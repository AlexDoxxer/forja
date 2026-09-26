"""Auth (ADR 0003): registro, login, logout, sesiones, CSRF, contraseñas y ``/auth/check``."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.security.ratelimit import RateLimiter
from app.security.tokens import CSRF_COOKIE, SESSION_COOKIE
from tests.integration.conftest import PASSWORD, register_user

pytestmark = pytest.mark.integration


async def test_register_first_user_is_admin_and_sets_cookies(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "Lucia@Example.org", "password": PASSWORD, "display_name": "Lucía"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "admin"
    assert body["email"].lower() == "lucia@example.org"
    assert body["onboarding_completed"] is False
    assert body["diet_available"] is False
    set_cookie = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in set_cookie if c.startswith(SESSION_COOKIE))
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert flag.lower() in session_cookie.lower()
    assert "domain" not in session_cookie.lower()
    csrf_cookie = next(c for c in set_cookie if c.startswith(CSRF_COOKIE))
    assert "httponly" not in csrf_cookie.lower()


async def test_second_user_is_regular_and_duplicate_email_conflicts(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    me = await other_client.get("/auth/me")
    assert me.json()["role"] == "user"
    dup = await client.post(
        "/auth/register",
        json={"email": "MARIO@example.org", "password": PASSWORD, "display_name": "x"},
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "email_taken"


async def test_register_validation_weak_password_and_closed(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    short = await client.post(
        "/auth/register", json={"email": "a@b.co", "password": "corta", "display_name": "x"}
    )
    assert short.status_code == 422
    assert short.headers["content-type"].startswith("application/problem+json")
    assert short.json()["code"] == "validation_error"
    assert short.json()["errors"][0]["loc"][:2] == ["body", "password"]
    common = await client.post(
        "/auth/register", json={"email": "a@b.co", "password": "password123", "display_name": "x"}
    )
    assert common.status_code == 422
    app.state.settings = app.state.settings.model_copy(update={"registration_open": False})
    try:
        closed = await client.post(
            "/auth/register", json={"email": "a@b.co", "password": PASSWORD, "display_name": "x"}
        )
        assert closed.status_code == 403
        assert closed.json()["code"] == "registration_closed"
    finally:
        app.state.settings = app.state.settings.model_copy(update={"registration_open": True})


async def test_login_logout_and_me(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    assert (await client.get("/auth/me")).status_code == 200
    logout = await client.post("/auth/logout")
    assert logout.status_code == 204
    client.cookies.delete(SESSION_COOKIE)  # el navegador ya la habría borrado
    assert (await client.get("/auth/me")).status_code == 401
    bad = await client.post("/auth/login", json={"email": user["email"], "password": "x" * 12})
    assert bad.status_code == 401
    assert bad.json()["code"] == "invalid_credentials"
    unknown = await client.post("/auth/login", json={"email": "no@existe.co", "password": PASSWORD})
    assert unknown.status_code == 401
    assert unknown.json() == {**bad.json(), "request_id": unknown.json()["request_id"], "instance": bad.json()["instance"]}
    ok = await client.post("/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["last_login_at"] is not None


async def test_revoked_token_is_rejected_server_side(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    token = client.cookies.get(SESSION_COOKIE)
    assert (await client.post("/auth/logout")).status_code == 204
    client.cookies.set(SESSION_COOKIE, token or "", domain="forja.test", path="/")
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/check")).status_code == 401


async def test_login_rotates_session_and_csrf_tokens(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    old_session, old_csrf = client.cookies.get(SESSION_COOKIE), client.cookies.get(CSRF_COOKIE)
    ok = await client.post("/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert ok.status_code == 200
    assert client.cookies.get(SESSION_COOKIE) != old_session
    assert client.cookies.get(CSRF_COOKIE) != old_csrf


async def test_csrf_required_on_every_unsafe_method(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    for method, path in (
        ("POST", "/auth/logout"),
        ("PUT", "/profile"),
        ("PATCH", "/programs/00000000-0000-0000-0000-000000000000"),
        ("DELETE", "/me"),
        ("POST", "/auth/login"),
    ):
        client.headers.pop("X-CSRF-Token", None)
        response = await client.request(method, path, json={})
        assert response.status_code == 403, (method, path)
        assert response.json()["code"] == "csrf_failed"
    wrong = await client.post("/auth/logout", headers={"X-CSRF-Token": "otro"})
    assert wrong.status_code == 403
    assert (await client.get("/auth/me")).status_code == 200


async def test_auth_check_is_bodyless(client: httpx.AsyncClient) -> None:
    anon = await client.get("/auth/check")
    assert anon.status_code == 401
    assert anon.content == b""
    await register_user(client)
    ok = await client.get("/auth/check")
    assert ok.status_code == 204
    assert ok.content == b""


async def test_sliding_expiration_and_expired_session(
    client: httpx.AsyncClient, user: dict[str, Any], engine: AsyncEngine
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE session SET last_seen_at = :ts, expires_at = :exp"),
            {
                "ts": datetime.now(UTC) - timedelta(minutes=5),
                "exp": datetime.now(UTC) + timedelta(days=1),
            },
        )
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert SESSION_COOKIE in response.headers.get("set-cookie", "")
    async with engine.connect() as conn:
        expires = (await conn.execute(text("SELECT expires_at FROM session"))).scalar_one()
    assert expires > datetime.now(UTC) + timedelta(days=29)
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE session SET expires_at = now() - interval '1 second'"))
    assert (await client.get("/auth/me")).status_code == 401


async def test_password_change_revokes_other_sessions(
    client: httpx.AsyncClient, user: dict[str, Any], app: FastAPI
) -> None:
    second = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://forja.test/api/v1")
    async with second:
        await second.get("/auth/csrf")
        token = second.cookies.get(CSRF_COOKIE) or ""
        login = await second.post(
            "/auth/login",
            headers={"X-CSRF-Token": token},
            json={"email": user["email"], "password": PASSWORD},
        )
        assert login.status_code == 200
        sessions = (await client.get("/auth/sessions")).json()["items"]
        assert len(sessions) == 2
        assert sum(1 for s in sessions if s["current"]) == 1
        wrong = await client.post(
            "/auth/password", json={"current_password": "nope-nope-nope", "new_password": "otra-clave-larga-1"}
        )
        assert wrong.status_code == 422
        weak = await client.post(
            "/auth/password", json={"current_password": PASSWORD, "new_password": "1234567890"}
        )
        assert weak.status_code == 422
        changed = await client.post(
            "/auth/password", json={"current_password": PASSWORD, "new_password": "otra-clave-larga-1"}
        )
        assert changed.status_code == 204
        assert (await second.get("/auth/me")).status_code == 401
        assert (await client.get("/auth/me")).status_code == 200
        relogin = await client.post(
            "/auth/login", json={"email": user["email"], "password": "otra-clave-larga-1"}
        )
        assert relogin.status_code == 200


async def test_revoke_own_session_and_cross_user_is_404(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    mine = (await client.get("/auth/sessions")).json()["items"][0]["id"]
    theirs = (await other_client.get("/auth/sessions")).json()["items"][0]["id"]
    assert (await client.delete(f"/auth/sessions/{theirs}")).status_code == 404
    assert (await client.delete(f"/auth/sessions/{mine}")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401
    assert (await other_client.get("/auth/me")).status_code == 200


async def test_deactivated_user_cannot_use_session(
    client: httpx.AsyncClient, user: dict[str, Any], engine: AsyncEngine
) -> None:
    async with engine.begin() as conn:
        await conn.execute(text('UPDATE "user" SET is_active = false'))
    assert (await client.get("/auth/me")).status_code == 401
    login = await client.post("/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert login.status_code == 401


async def test_rate_limit_returns_429_with_retry_after(app: FastAPI, client: httpx.AsyncClient) -> None:
    original = app.state.rate_limiter
    app.state.rate_limiter = RateLimiter(scale=1)
    try:
        statuses = []
        for _ in range(12):
            response = await client.post(
                "/auth/login", json={"email": "x@x.co", "password": PASSWORD}
            )
            statuses.append(response.status_code)
        assert statuses[:10] == [401] * 10
        assert 429 in statuses
        limited = next(s for s in statuses if s == 429)
        assert limited == 429
        assert int(response.headers["retry-after"]) >= 1
        assert response.json()["code"] == "rate_limited"
    finally:
        app.state.rate_limiter = original


async def test_security_headers_request_id_and_problem_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/nope", headers={"X-Request-ID": "abcdef123456"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["x-request-id"] == "abcdef123456"
    assert response.json()["request_id"] == "abcdef123456"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "max-age" in response.headers["strict-transport-security"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "same-origin"
    assert "permissions-policy" in response.headers
    generated = await client.get("/health")
    assert len(generated.headers["x-request-id"]) >= 8


async def test_payload_too_large_is_413(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    response = await client.post("/auth/password", content=b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


async def test_health_ready_and_about(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}
    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"database": True, "media": True}
    about = (await client.get("/about")).json()
    assert about["dataset"]["exercise_count"] == 1324
    assert about["media_attribution"] == {"text": "© Gym visual", "url": "https://gymvisual.com/"}
    assert about["engine_version"]

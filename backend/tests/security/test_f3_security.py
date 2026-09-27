"""Revisión de seguridad de la Fase 3 (revisor-seguridad).

Los tests marcados ``KNOWN_ISSUE`` (xfail estricto) demuestran un hallazgo real de
``docs/reviews/f3-security.md``: pasarán a XPASS (y fallarán el build, avisando de quitar la
marca) cuando el propietario aplique la corrección.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.main import create_app
from app.security.tokens import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, hash_token
from tests.integration.conftest import PASSWORD
from tests.integration.test_nutrition_account_admin import enable_diet, next_monday
from tests.integration.test_programs import create, preview
from tests.integration.test_training import log, start

pytestmark = pytest.mark.integration
KNOWN_ISSUE = pytest.mark.xfail(strict=True, reason="hallazgo abierto de f3-security.md")
GHOST = "00000000-0000-4000-8000-000000000001"
PUBLIC = {
    "/health",
    "/ready",
    "/about",
    "/auth/csrf",
    "/auth/register",
    "/auth/login",
    "/auth/check",
}
NOW = "2030-01-01T00:00:00Z"


def _operations() -> list[tuple[str, str]]:
    spec = yaml.safe_load((Path(__file__).parents[3] / "contracts/openapi.yaml").read_text())
    return [
        (m.upper(), p)
        for p, item in spec["paths"].items()
        for m in item
        if m in {"get", "post", "put", "patch", "delete"}
    ]


OPS = _operations()


def concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", GHOST, path)


# ------------------------------------------------------------ autenticación y CSRF
@pytest.mark.parametrize(("method", "path"), [o for o in OPS if o[1] not in PUBLIC])
async def test_every_private_route_requires_session(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, concrete(path), json={} if method != "GET" else None)
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


@pytest.mark.parametrize(
    ("method", "path"), [o for o in OPS if o[0] in {"POST", "PUT", "PATCH", "DELETE"}]
)
async def test_every_unsafe_route_enforces_csrf(
    client: httpx.AsyncClient, user: dict[str, Any], method: str, path: str
) -> None:
    missing = await client.request(method, concrete(path), json={}, headers={CSRF_HEADER: ""})
    assert missing.status_code == 403, f"{method} {path} -> {missing.status_code}"
    assert missing.json()["code"] == "csrf_failed"
    forged = await client.request(method, concrete(path), json={}, headers={CSRF_HEADER: "x" * 43})
    assert forged.status_code == 403


async def test_cookies_hardened_and_token_hashed_at_rest(
    client: httpx.AsyncClient, engine: AsyncEngine
) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "cookie@example.org", "password": PASSWORD, "display_name": "C"},
    )
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("__Host-forja_session="))
    lowered = session_cookie.lower()
    assert "httponly" in lowered
    assert "secure" in lowered
    assert "samesite=lax" in lowered
    assert "domain=" not in "\n".join(cookies).lower()
    token = client.cookies.get(SESSION_COOKIE)
    assert token
    async with engine.connect() as conn:
        hashes = (await conn.execute(text("SELECT token_hash FROM session"))).scalars().all()
    assert hash_token(token) in hashes
    assert token not in hashes


async def test_login_rotates_session_and_ignores_preset_cookie(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    fixed = "attacker-chosen-session-token"
    client.cookies.set(SESSION_COOKIE, fixed, domain="forja.test")
    login = await client.post(
        "/auth/login", json={"email": "lucia@example.org", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert client.cookies.get(SESSION_COOKIE) != fixed


async def test_password_change_revokes_old_sessions(
    client: httpx.AsyncClient, user: dict[str, Any], app: FastAPI
) -> None:
    old = client.cookies.get(SESSION_COOKIE)
    change = await client.post(
        "/auth/password", json={"current_password": PASSWORD, "new_password": PASSWORD + "-nueva"}
    )
    assert change.status_code == 204
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://forja.test/api/v1") as re_:
        re_.cookies.set(SESSION_COOKIE, old or "", domain="forja.test")
        assert (await re_.get("/auth/me")).status_code == 401


async def test_login_errors_are_indistinguishable(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    ghost = await client.post("/auth/login", json={"email": "no@example.org", "password": "x" * 12})
    wrong = await client.post(
        "/auth/login", json={"email": "lucia@example.org", "password": "x" * 12}
    )
    assert ghost.status_code == wrong.status_code == 401
    drop = {"request_id"}
    assert {k: v for k, v in ghost.json().items() if k not in drop} == {
        k: v for k, v in wrong.json().items() if k not in drop
    }


# ------------------------------------------------------- autorización entre usuarios
async def _victim_resources(client: httpx.AsyncClient) -> dict[str, Any]:
    program = await create(client, (await preview(client))["plan"], activate=True)
    day = program["weeks"][0]["days"][0]
    session = await start(client)
    set_response = await log(client, session["id"])
    assert set_response.status_code == 201, set_response.text
    metric = await client.post("/body-metrics", json={"date": "2026-01-02", "weight_kg": 70})
    await enable_diet(client)
    plan = await client.post("/nutrition/plans", json={"week_start": next_monday(), "seed": 3})
    assert plan.status_code == 201, plan.text
    sessions = (await client.get("/auth/sessions")).json()["items"]
    return {
        "program": program,
        "day": day,
        "session": session,
        "set": set_response.json(),
        "metric": metric.json(),
        "plan": plan.json(),
        "auth_session": sessions[0]["id"],
    }


async def test_cross_user_access_is_404_on_every_resource(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    v = await _victim_resources(client)
    await enable_diet(
        other_client
    )  # sin dieta activa la ruta respondería 403 antes de mirar la propiedad
    pid, day_id = v["program"]["id"], v["day"]["id"]
    sid, set_id = v["session"]["id"], v["set"]["id"]
    plan_id = v["plan"]["id"]
    cases: list[tuple[str, str, Any]] = [
        ("GET", f"/programs/{pid}", None),
        ("PATCH", f"/programs/{pid}", {"name": "pwn"}),
        ("DELETE", f"/programs/{pid}", None),
        ("POST", f"/programs/{pid}/activate", None),
        ("POST", f"/programs/{pid}/duplicate", {}),
        ("POST", f"/programs/{pid}/regenerate-day", {"day_id": day_id, "week_index": 0}),
        ("POST", f"/programs/{pid}/swap", {"day_id": day_id}),
        ("PUT", f"/programs/{pid}/days/{day_id}", {}),
        ("GET", f"/programs/{pid}/export.pdf", None),
        ("GET", f"/programs/{pid}/calendar.ics", None),
        ("GET", f"/sessions/{sid}", None),
        ("PATCH", f"/sessions/{sid}", {"name": "pwn"}),
        ("POST", f"/sessions/{sid}/finish", {}),
        ("POST", f"/sessions/{sid}/sets", {}),
        ("PATCH", f"/sessions/{sid}/sets/{set_id}", {"reps": 1}),
        ("DELETE", f"/sessions/{sid}/sets/{set_id}", None),
        ("DELETE", f"/body-metrics/{v['metric']['id']}", None),
        ("GET", f"/nutrition/plans/{plan_id}", None),
        ("POST", f"/nutrition/plans/{plan_id}/swap", {}),
        ("GET", f"/nutrition/plans/{plan_id}/shopping-list", None),
        ("DELETE", f"/auth/sessions/{v['auth_session']}", None),
    ]
    for method, path, body in cases:
        response = await other_client.request(
            method, path, json=body, headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        assert response.status_code in {404, 422}, f"{method} {path} -> {response.status_code}"
    for path in ("/programs", "/sessions", "/nutrition/plans", "/records"):
        assert (await other_client.get(path)).json()["items"] == [], path
    assert (await client.get(f"/programs/{pid}")).status_code == 200
    assert (await client.get(f"/sessions/{sid}")).status_code == 200
    stolen = await other_client.post(
        "/sessions",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "client_uuid": str(uuid.uuid4()),
            "program_day_id": day_id,
            "started_at": "2026-01-01T10:00:00Z",
        },
    )
    assert stolen.status_code in {404, 422}


async def test_admin_routes_forbidden_for_regular_user(
    other_client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    for method, path, body in (
        ("GET", "/admin/settings", None),
        ("PUT", "/admin/settings", {"registration_open": True, "diet_feature_enabled": True}),
        ("GET", "/admin/users", None),
        ("PATCH", f"/admin/users/{user['id']}", {"role": "user"}),
        ("POST", "/admin/ingest", {"dry_run": True}),
        ("GET", "/admin/ingest/runs", None),
    ):
        response = await other_client.request(method, path, json=body)
        assert response.status_code == 403, f"{method} {path}"


def _session_op(client_uuid: str, name: str) -> dict[str, Any]:
    return {
        "op": "session_upsert",
        "client_uuid": client_uuid,
        "started_at": NOW,
        "finished_at": None,
        "status": "in_progress",
        "name": name,
        "updated_at": NOW,
        "program_day_id": None,
        "perceived_effort": None,
        "notes": None,
    }


def _set_op(session_uuid: str, set_uuid: str) -> dict[str, Any]:
    return {
        "op": "set_upsert",
        "session_client_uuid": session_uuid,
        "updated_at": NOW,
        "set": {
            "client_uuid": set_uuid,
            "exercise_id": "0043",
            "program_exercise_id": None,
            "set_index": 1,
            "weight_kg": 1,
            "reps": 1,
            "rir": None,
            "duration_s": None,
            "is_warmup": False,
            "completed_at": NOW,
        },
    }


async def test_sync_cannot_touch_foreign_sessions_or_sets(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    session = await start(client)
    victim_set = (await log(client, session["id"])).json()["client_uuid"]
    ops = [
        {"op": "set_delete", "client_uuid": victim_set, "deleted_at": NOW},
        _session_op(session["client_uuid"], "pwn"),
    ]
    response = await other_client.post("/sync", json={"operations": ops})
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["server_id"] is None
    mine = (await other_client.get("/sessions")).json()["items"]
    assert [s["name"] for s in mine] == ["pwn"]  # se creó una sesión PROPIA, no se tocó la ajena
    victim = (await client.get(f"/sessions/{session['id']}")).json()
    assert victim["name"] != "pwn"
    assert len(victim["sets"]) == 1


@KNOWN_ISSUE
async def test_sync_set_conflict_does_not_reveal_foreign_client_uuid(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    """S-05: el 409 «pertenece a otra sesión» confirma que un client_uuid existe en otra cuenta."""
    session = await start(client)
    victim_set = (await log(client, session["id"])).json()["client_uuid"]
    mine = str(uuid.uuid4())
    ops = [_session_op(mine, "m"), _set_op(mine, victim_set)]
    results = (await other_client.post("/sync", json={"operations": ops})).json()["results"]
    assert "otra sesión" not in json.dumps(results, ensure_ascii=False)


async def test_import_never_overwrites_foreign_data(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    v = await _victim_resources(client)
    export = (await client.get("/me/export")).json()
    assert "password" not in json.dumps(export).lower()
    export["programs"][0]["name"] = "HIJACK"
    assert (await other_client.post("/me/import", json=export)).status_code == 200
    assert (await client.get(f"/programs/{v['program']['id']}")).json()["name"] != "HIJACK"


# ----------------------------------------------------------------------- privacidad
async def test_account_deletion_removes_every_user_row(
    other_client: httpx.AsyncClient, user: dict[str, Any], engine: AsyncEngine
) -> None:
    client = other_client
    user = (await client.get("/auth/me")).json()
    await _victim_resources(client)
    assert (await client.request("DELETE", "/me", json={"password": PASSWORD})).status_code == 204
    async with engine.connect() as conn:
        tables = (
            (
                await conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.columns WHERE "
                        "table_schema='public' AND column_name IN ('user_id','actor_id')"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert tables
        leftovers = {}
        for table in set(tables):
            col = "actor_id" if table == "audit_log" else "user_id"
            count = (
                await conn.execute(
                    text(f'SELECT count(*) FROM "{table}" WHERE {col} = :u'),
                    {"u": uuid.UUID(user["id"])},
                )
            ).scalar_one()
            if count:
                leftovers[table] = count
        assert not leftovers, leftovers
        details = (await conn.execute(text("SELECT details::text FROM audit_log"))).scalars().all()
        assert not any("lucia@example.org" in (d or "") for d in details)


async def test_health_data_never_logged(
    client: httpx.AsyncClient, user: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    secret = "SECRETNOTE-lumbar-8f3a"  # noqa: S105
    session = await start(client, notes=secret)
    await client.patch(f"/sessions/{session['id']}", json={"notes": secret})
    await client.post("/body-metrics", json={"date": "2026-02-02", "weight_kg": 123.456})
    await client.post(
        "/auth/login", json={"email": "lucia@example.org", "password": "WRONGPASS-xyz1"}
    )
    await client.post("/sessions", json={"bad": secret})
    blob = "\n".join(r.getMessage() + json.dumps(r.__dict__, default=str) for r in caplog.records)
    for needle in (secret, "123.456", "WRONGPASS-xyz1", "lucia@example.org", PASSWORD):
        assert needle not in blob, needle


# ------------------------------------------------------------------ entrada y límites
async def test_oversized_declared_body_is_413(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    response = await client.post(
        "/programs",
        content=b"{" + b" " * (1024 * 1024 + 10) + b"}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


@KNOWN_ISSUE
async def test_chunked_body_over_limit_is_413(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    """S-03: el límite solo mira Content-Length; con Transfer-Encoding: chunked no se aplica."""

    async def gen() -> Any:
        for _ in range(3):
            yield b" " * (1024 * 1024)
        yield b"{}"

    response = await client.post(
        "/programs", content=gen(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


async def test_json_nesting_bomb_is_client_error(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    body = b"[" * 200_000 + b"]" * 200_000
    response = await client.post(
        "/me/import", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code in {400, 413, 422}, response.status_code


@pytest.mark.parametrize("path", ["/profile", "/body-metrics", "/sessions"])
async def test_nul_byte_strings_do_not_cause_500(
    client: httpx.AsyncClient, user: dict[str, Any], path: str
) -> None:
    """U+0000 en un texto libre no debe llegar a PostgreSQL (500)."""
    payload: dict[str, Any] = {
        "/profile": {"display_name": "a\u0000b"},
        "/body-metrics": {"date": "2026-03-03", "weight_kg": 70, "notes": "a\u0000b"},
        "/sessions": {
            "client_uuid": str(uuid.uuid4()),
            "started_at": "2026-01-01T00:00:00Z",
            "name": "a\u0000b",
        },
    }[path]
    method = "PUT" if path == "/profile" else "POST"
    response = await client.request(
        method, path, json=payload, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert response.status_code != 500, f"{method} {path}"


async def test_sql_injection_payloads_are_inert(
    client: httpx.AsyncClient, user: dict[str, Any], engine: AsyncEngine
) -> None:
    for q in ("' OR 1=1 --", '\'; DROP TABLE "user"; --', "%' UNION SELECT 1 --"):
        assert (await client.get("/exercises", params={"q": q})).status_code in {200, 422}
        assert (await client.get("/admin/users", params={"q": q})).status_code == 200
        assert (await client.get("/foods", params={"q": q})).status_code in {200, 403, 422}
    async with engine.connect() as conn:
        assert (await conn.execute(text('SELECT count(*) FROM "user"'))).scalar_one() == 1


@KNOWN_ISSUE
async def test_ics_text_fields_cannot_inject_lines(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    """S-08: `_escape` no neutraliza un CR suelto ⇒ inyección de líneas en el .ics."""
    evil = "x\rBEGIN:VEVENT\rSUMMARY:pwn"
    program = await create(client, (await preview(client))["plan"], name=evil)
    ics = (await client.get(f"/programs/{program['id']}/calendar.ics")).text
    assert "\rBEGIN:VEVENT\rSUMMARY:pwn" not in ics


async def test_pdf_export_escapes_html_and_makes_no_remote_fetch(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    evil = 'x</style><img src="http://127.0.0.1:9/ssrf">'
    program = await create(client, (await preview(client))["plan"], name=evil)
    pdf = await client.get(f"/programs/{program['id']}/export.pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


# ------------------------------------------------------------------ rate limiting
@pytest.fixture
async def strict_app(settings: Any, app: FastAPI) -> Any:
    application = create_app(settings, rate_limit_scale=1)
    async with application.router.lifespan_context(application):
        yield application


async def _strict_client(app: FastAPI) -> httpx.AsyncClient:
    http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://forja.test/api/v1"
    )
    await http.get("/auth/csrf")
    http.headers[CSRF_HEADER] = http.cookies.get(CSRF_COOKIE) or ""
    return http


async def test_login_rate_limit_per_email(strict_app: FastAPI, user: dict[str, Any]) -> None:
    http = await _strict_client(strict_app)
    try:
        codes = [
            (
                await http.post(
                    "/auth/login",
                    json={"email": "lucia@example.org", "password": f"bad-password-{i}"},
                )
            ).status_code
            for i in range(12)
        ]
    finally:
        await http.aclose()
    assert codes[:10] == [401] * 10
    assert 429 in codes[10:]


@KNOWN_ISSUE
async def test_rate_limit_not_bypassable_with_spoofed_forwarded_for(
    strict_app: FastAPI, user: dict[str, Any]
) -> None:
    """S-02: ``client_ip`` confía en el primer valor de X-Forwarded-For (lo fija el cliente)."""
    http = await _strict_client(strict_app)
    try:
        codes = [
            (
                await http.post(
                    "/auth/login",
                    json={"email": f"spray{i}@example.org", "password": "bad-password-1"},
                    headers={"X-Forwarded-For": f"10.9.{i // 250}.{i % 250}"},
                )
            ).status_code
            for i in range(30)
        ]
    finally:
        await http.aclose()
    assert 429 in codes, "30 intentos de una sola conexión sin ningún 429"

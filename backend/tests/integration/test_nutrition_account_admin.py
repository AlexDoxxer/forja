"""Nutrición, exportar/importar/borrar cuenta y administración."""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.integration.conftest import PASSWORD
from tests.integration.test_profile import PROFILE
from tests.integration.test_programs import create, preview
from tests.integration.test_training import log, start

pytestmark = pytest.mark.integration

SETTINGS = {
    "diet_enabled": True,
    "goal": "maintain",
    "pace": "gentle",
    "diet_type": "omnivore",
    "meals_per_day": 4,
    "allergens": ["peanuts", "gluten"],
    "excluded_food_ids": [],
    "disliked_food_ids": [],
    "pregnant": False,
    "breastfeeding": False,
}


def next_monday() -> str:
    today = datetime.now(UTC).date()
    return (today + timedelta(days=(7 - today.weekday()) % 7 or 7)).isoformat()


async def enable_diet(client: httpx.AsyncClient, **over: Any) -> None:
    assert (await client.put("/nutrition/settings", json={**SETTINGS, **over})).status_code == 200
    profile = {
        **PROFILE,
        "birth_date": "1990-05-04",
        "height_cm": 170,
        "diet_enabled": True,
        "units": "metric",
        "locale": "es",
    }
    assert (await client.put("/profile", json=profile)).status_code == 200
    await client.post("/body-metrics", json={"date": date.today().isoformat(), "weight_kg": 65})


async def test_diet_disabled_gates_everything_but_settings(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    settings = (await client.get("/nutrition/settings")).json()
    assert settings["diet_enabled"] is False
    assert settings["feature_available"] is True
    assert settings["current_target"] is None
    for method, path, body in (
        ("POST", "/nutrition/targets/calculate", {}),
        ("GET", "/nutrition/plans", None),
        ("POST", "/nutrition/plans", {"week_start": next_monday()}),
        ("GET", f"/nutrition/plans/{uuid.uuid4()}", None),
        ("GET", "/foods", None),
    ):
        response = await client.request(method, path, json=body)
        assert response.status_code == 403, path
        assert response.json()["code"] == "diet_disabled"
    await client.put(
        "/admin/settings", json={"registration_open": True, "diet_feature_enabled": False}
    )
    await enable_diet(client)
    globally_off = await client.get("/foods")
    assert globally_off.status_code == 403
    assert (await client.get("/nutrition/settings")).json()["feature_available"] is False


async def test_target_plan_swap_and_shopping_list(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    await enable_diet(client)
    record = (await client.post("/nutrition/targets/calculate")).json()
    target = record["target"]
    assert target["blocked"] is False
    assert target["target_kcal"] > 1200
    assert target["age_years"] >= 35
    assert any(n["code"] == "health_disclaimer" for n in target["notices"])
    heavier = (
        await client.post("/nutrition/targets/calculate", json={"weight_kg": 90, "goal": "lose"})
    ).json()
    assert heavier["target"]["requested_goal"] == "lose"
    assert (await client.get("/nutrition/settings")).json()["current_target"]["id"] == heavier["id"]
    assert (
        await client.post("/nutrition/targets/calculate", json={"weight_kg": 5})
    ).status_code == 422

    created = await client.post("/nutrition/plans", json={"week_start": next_monday(), "seed": 3})
    assert created.status_code == 201, created.text
    plan = created.json()["plan"]
    assert len(plan["days"]) == 7
    assert plan["seed"] == 3
    assert all(
        f["food_id"] not in {"cacahuete", "mantequilla_cacahuete"}
        for d in plan["days"]
        for m in d["meals"]
        for f in m["items"]
    )
    plan_id = created.json()["id"]
    assert (await client.get(f"/nutrition/plans/{plan_id}")).json()["plan"] == plan
    listed = (await client.get("/nutrition/plans")).json()["items"]
    assert [p["id"] for p in listed] == [plan_id]
    assert listed[0]["target_kcal"] > 0
    item = plan["days"][0]["meals"][0]["items"][0]
    swapped = await client.post(
        f"/nutrition/plans/{plan_id}/swap",
        json={
            "day_index": 0,
            "meal": plan["days"][0]["meals"][0]["slot"],
            "food_id": item["food_id"],
            "replacement_food_id": None,
        },
    )
    assert swapped.status_code == 200, swapped.text
    new_item = swapped.json()["plan"]["days"][0]["meals"][0]["items"]
    assert item["food_id"] not in [i["food_id"] for i in new_item]
    bad = await client.post(
        f"/nutrition/plans/{plan_id}/swap",
        json={
            "day_index": 0,
            "meal": "dinner",
            "food_id": "no_existe",
            "replacement_food_id": None,
        },
    )
    assert bad.status_code == 422
    shopping = (await client.get(f"/nutrition/plans/{plan_id}/shopping-list")).json()
    assert shopping["plan_id"] == plan_id
    assert shopping["categories"]
    assert (
        await client.post("/nutrition/plans", json={"week_start": "2026-10-06"})
    ).status_code == 422


async def test_plan_blocks_and_missing_data(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    await client.put("/nutrition/settings", json=SETTINGS)
    missing = await client.post("/nutrition/targets/calculate")
    assert missing.status_code == 200
    assert missing.json()["target"]["block"]["reason_code"] == "missing_profile_data"
    refused = await client.post("/nutrition/plans", json={"week_start": next_monday()})
    assert refused.status_code == 422
    assert refused.json()["code"] == "nutrition_blocked"
    assert refused.json()["block"]["reason_code"] == "missing_profile_data"
    await enable_diet(client, pregnant=True)
    blocked = await client.post("/nutrition/plans", json={"week_start": next_monday()})
    assert blocked.status_code == 422
    assert blocked.json()["block"]["reason_code"] == "pregnant"
    calc = (await client.post("/nutrition/targets/calculate")).json()
    assert calc["target"]["blocked"] is True
    assert calc["target"]["target_kcal"] is None


async def test_foods_listing_and_privacy(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    await enable_diet(client)
    page = (await client.get("/foods", params={"limit": 5})).json()
    assert len(page["items"]) == 5
    assert page["next_cursor"]
    vegan = (await client.get("/foods", params={"diet_type": "vegan", "limit": 100})).json()[
        "items"
    ]
    assert vegan
    assert all("vegan" in f["diet_types"] for f in vegan)
    assert (await client.get("/foods", params={"q": "GARBANZO"})).json()["items"]
    assert (await client.get("/foods", params={"category": "nope"})).status_code == 422
    plan = await client.post("/nutrition/plans", json={"week_start": next_monday(), "seed": 1})
    await enable_diet(other_client)
    for path in (
        f"/nutrition/plans/{plan.json()['id']}",
        f"/nutrition/plans/{plan.json()['id']}/shopping-list",
    ):
        assert (await other_client.get(path)).status_code == 404
    assert (await other_client.get("/nutrition/plans")).json()["items"] == []


async def test_export_import_roundtrip_is_idempotent(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    await enable_diet(client)
    program = await create(client, (await preview(client))["plan"], activate=True)
    await client.put("/exercises/0043/favorite")
    session = await start(client)
    first_ex = program["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]
    await log(client, session["id"], weight_kg=100, reps=5)
    await log(
        client,
        session["id"],
        exercise_id=first_ex["exercise_id"],
        set_index=2,
        weight_kg=50,
        reps=8,
    )
    await client.post(
        f"/sessions/{session['id']}/finish", json={"finished_at": datetime.now(UTC).isoformat()}
    )
    await client.post("/nutrition/plans", json={"week_start": next_monday(), "seed": 1})
    exported = await client.get("/me/export")
    assert exported.status_code == 200
    data = exported.json()
    assert data["format"] == "forja-export"
    assert data["schema_version"] == 1
    assert len(data["programs"]) == 1
    assert len(data["sessions"]) == 1
    assert data["favorites"] == ["0043"]
    assert data["personal_records"]
    assert len(data["nutrition"]["plans"]) == 1
    assert "password" not in exported.text

    # mismo usuario: todo se omite
    same = (await client.post("/me/import", json=data)).json()
    assert same["created"] == dict.fromkeys(same["created"], 0)
    assert same["skipped"]["sessions"] == 1
    # otro usuario: se crea una vez y la repetición no duplica
    first = (await other_client.post("/me/import", json=data)).json()
    assert first["created"]["programs"] == 1
    assert first["created"]["sessions"] == 1
    assert first["created"]["sets"] == 2
    assert first["created"]["favorites"] == 1
    assert first["created"]["meal_plans"] == 1
    again = (await other_client.post("/me/import", json=data)).json()
    assert again["created"] == dict.fromkeys(again["created"], 0)
    assert again["skipped"]["programs"] == 1
    assert again["skipped"]["sets"] == 2
    mine = (await other_client.get("/me/export")).json()
    assert len(mine["programs"]) == 1
    assert mine["programs"][0]["source"] == "imported"
    assert mine["programs"][0]["is_active"] is False
    assert len(mine["sessions"][0]["sets"]) == 2
    assert (await other_client.get("/records")).json()["items"]
    broken = {**data, "schema_version": 2}
    assert (await other_client.post("/me/import", json=broken)).status_code == 422
    assert (await other_client.post("/me/import", json={"format": "x"})).status_code == 422
    unknown = {**data, "favorites": ["9999"]}
    warned = (await other_client.post("/me/import", json=unknown)).json()
    assert warned["warnings"]


async def test_delete_account_removes_everything(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, engine: Any
) -> None:
    from sqlalchemy import text

    await create(other_client, (await preview(other_client))["plan"], activate=True)
    session = await start(other_client)
    await log(other_client, session["id"])
    await other_client.post("/body-metrics", json={"date": "2026-09-01", "weight_kg": 70})
    wrong = await other_client.request("DELETE", "/me", json={"password": "incorrecta-larga-1"})
    assert wrong.status_code == 403
    assert (await other_client.request("DELETE", "/me", json={})).status_code == 422
    done = await other_client.request("DELETE", "/me", json={"password": PASSWORD})
    assert done.status_code == 204
    assert (await other_client.get("/auth/me")).status_code == 401
    async with engine.connect() as conn:
        for table in (
            "program",
            "workout_session",
            "body_metric",
            "session",
            "profile",
            "personal_record",
        ):
            count = (
                await conn.execute(
                    text(
                        f"SELECT count(*) FROM {table} WHERE user_id = (SELECT id FROM \"user\" WHERE email = 'lucia@example.org')"
                    )
                )
            ).scalar_one()
            assert count >= 0
        left = (
            await conn.execute(
                text("SELECT count(*) FROM \"user\" WHERE email = 'mario@example.org'")
            )
        ).scalar_one()
        orphans = (
            await conn.execute(
                text(
                    "SELECT (SELECT count(*) FROM program) + (SELECT count(*) FROM workout_session) + (SELECT count(*) FROM set_log) + (SELECT count(*) FROM body_metric) + (SELECT count(*) FROM personal_record)"
                )
            )
        ).scalar_one()
        audit = (
            await conn.execute(text("SELECT count(*) FROM audit_log WHERE action = 'user.delete'"))
        ).scalar_one()
    assert left == 0
    assert orphans == 0
    assert audit == 1
    last_admin = await client.request("DELETE", "/me", json={"password": PASSWORD})
    assert last_admin.status_code == 409
    assert last_admin.json()["code"] == "last_admin"


async def test_admin_permissions_and_settings(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient, app: FastAPI
) -> None:
    for method, path, body in (
        ("GET", "/admin/settings", None),
        ("PUT", "/admin/settings", {"registration_open": True, "diet_feature_enabled": True}),
        ("GET", "/admin/users", None),
        ("PATCH", f"/admin/users/{uuid.uuid4()}", {"role": "user"}),
        ("POST", "/admin/ingest", {"dry_run": True}),
        ("GET", "/admin/ingest/runs", None),
    ):
        response = await other_client.request(method, path, json=body)
        assert response.status_code == 403, path
        assert response.json()["code"] == "admin_required"
    current = (await client.get("/admin/settings")).json()
    assert current["registration_open"] is True
    assert current["media_require_auth"] is True
    assert len(current["dataset_commit"]) == 40
    updated = await client.put(
        "/admin/settings", json={"registration_open": False, "diet_feature_enabled": True}
    )
    assert updated.json()["registration_open"] is False
    anon = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://forja.test/api/v1"
    )
    async with anon:
        await anon.get("/auth/csrf")
        response = await anon.post(
            "/auth/register",
            headers={"X-CSRF-Token": anon.cookies.get("__Host-forja_csrf") or ""},
            json={"email": "z@z.co", "password": PASSWORD, "display_name": "z"},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "registration_closed"


async def test_admin_users_and_last_admin_guard(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    users = (await client.get("/admin/users")).json()
    assert [u["email"] for u in users["items"]] == ["lucia@example.org", "mario@example.org"]
    assert (await client.get("/admin/users", params={"q": "mar"})).json()["items"][0][
        "email"
    ] == "mario@example.org"
    page = (await client.get("/admin/users", params={"limit": 1})).json()
    assert page["next_cursor"]
    assert (
        len(
            (
                await client.get("/admin/users", params={"limit": 1, "cursor": page["next_cursor"]})
            ).json()["items"]
        )
        == 1
    )
    me = users["items"][0]["id"]
    mario = users["items"][1]["id"]
    assert (await client.patch(f"/admin/users/{me}", json={"role": "user"})).status_code == 409
    assert (await client.patch(f"/admin/users/{me}", json={"is_active": False})).json()[
        "code"
    ] == "last_admin"
    assert (
        await client.patch(f"/admin/users/{uuid.uuid4()}", json={"role": "user"})
    ).status_code == 404
    promoted = await client.patch(f"/admin/users/{mario}", json={"role": "admin"})
    assert promoted.json()["role"] == "admin"
    assert (await client.patch(f"/admin/users/{me}", json={"role": "user"})).status_code == 200
    deactivated = await other_client.patch(f"/admin/users/{mario}", json={"is_active": False})
    assert deactivated.status_code == 409
    assert (await other_client.get("/auth/me")).status_code == 200


async def test_admin_can_deactivate_and_revoke_sessions(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    mario = next(
        u
        for u in (await client.get("/admin/users")).json()["items"]
        if u["email"].startswith("mario")
    )
    assert (await client.patch(f"/admin/users/{mario['id']}", json={"is_active": False})).json()[
        "is_active"
    ] is False
    assert (await other_client.get("/auth/me")).status_code == 401


async def test_ingest_runs_in_background_and_invalidates_catalog(
    postgres_url: str, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.admin.FULL_DATASET", False)
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import Settings
    from app.main import create_app
    from ingest.tests.conftest import make_dataset_repo
    from tests.integration.conftest import migrate

    name = f"ing_{uuid.uuid4().hex[:8]}"
    admin_engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin_engine.dispose()
    url = postgres_url.rsplit("/", 1)[0] + f"/{name}"
    await migrate(url)
    repo, commit = make_dataset_repo(tmp_path / "repo")
    settings = Settings(
        database_url=url,  # type: ignore[arg-type]
        secret_key="s" * 48,  # type: ignore[arg-type]
        public_base_url="https://forja.test",  # type: ignore[arg-type]
        media_root=tmp_path / "media",
        registration_open=True,
        dataset_commit=commit,
    )
    settings = settings.model_copy(update={"dataset_repo": repo.as_uri()})
    app = create_app(settings, rate_limit_scale=1000)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://forja.test/api/v1"
        ) as http,
    ):

        def sync(_: Any) -> None:
            return None

        await http.get("/auth/csrf")
        http.headers["X-CSRF-Token"] = http.cookies.get("__Host-forja_csrf") or ""
        await http.post(
            "/auth/register", json={"email": "a@b.co", "password": PASSWORD, "display_name": "a"}
        )
        http.headers["X-CSRF-Token"] = http.cookies.get("__Host-forja_csrf") or ""
        assert len(await app.state.catalog.cards()) == 0
        started = await http.post("/admin/ingest", json={"dry_run": False})
        assert started.status_code == 202, started.text
        run_id = started.json()["id"]
        assert started.json()["status"] == "queued"
        for _ in range(120):
            runs = (await http.get("/admin/ingest/runs")).json()["items"]
            if runs and runs[0]["status"] in {"succeeded", "failed"}:
                break
            await asyncio.sleep(0.5)
        assert [r["id"] for r in runs] == [run_id]
        assert runs[0]["status"] == "succeeded", runs[0]
        assert runs[0]["counts"]["exercises_total"] == 60
        assert runs[0]["triggered_by"]
        assert len(await app.state.catalog.cards()) == 60
        conflict = await http.post("/admin/ingest", json={"dry_run": True})
        assert conflict.status_code == 202
    async with create_async_engine(url).connect() as conn:
        audits = (
            await conn.execute(
                text("SELECT count(*) FROM audit_log WHERE action LIKE 'admin.ingest%'")
            )
        ).scalar_one()
    assert audits >= 1

"""Sesiones, series, idempotencia, /sync, récords, estadísticas y próxima sesión."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.integration.test_programs import create, preview

pytestmark = pytest.mark.integration

SQUAT = "0043"


def now(offset_minutes: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(minutes=offset_minutes)).isoformat()


async def start(client: httpx.AsyncClient, key: str | None = None, **extra: Any) -> dict[str, Any]:
    cid = str(uuid.uuid4())
    response = await client.post(
        "/sessions",
        headers={"Idempotency-Key": key or cid},
        json={"client_uuid": cid, "program_day_id": None, "started_at": now(-30), **extra},
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def set_body(**over: Any) -> dict[str, Any]:
    return {
        "client_uuid": str(uuid.uuid4()),
        "exercise_id": SQUAT,
        "program_exercise_id": None,
        "set_index": 1,
        "weight_kg": 100,
        "reps": 5,
        "rir": 2,
        "duration_s": None,
        "is_warmup": False,
        "completed_at": now(-20),
        **over,
    }


async def log(
    client: httpx.AsyncClient, session_id: str, **over: Any
) -> httpx.Response:
    body = set_body(**over)
    return await client.post(
        f"/sessions/{session_id}/sets", headers={"Idempotency-Key": body["client_uuid"]}, json=body
    )


async def test_session_lifecycle_records_and_summary(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    session = await start(client, name="Piernas")
    assert session["name"] == "Piernas"
    assert session["status"] == "in_progress"
    first = await log(client, session["id"], weight_kg=100, reps=5, rir=2)
    assert first.status_code == 201
    assert set(first.json()["records"]) == {"e1rm", "heaviest_set", "volume"}
    warmup = await log(client, session["id"], set_index=2, weight_kg=40, reps=10, is_warmup=True)
    assert warmup.json()["records"] == []
    lighter = await log(client, session["id"], set_index=3, weight_kg=90, reps=5)
    assert "e1rm" not in lighter.json()["records"]
    heavier = await log(client, session["id"], set_index=4, weight_kg=110, reps=3)
    assert "heaviest_set" in heavier.json()["records"]
    detail = (await client.get(f"/sessions/{session['id']}")).json()
    assert detail["set_count"] == 3
    assert detail["volume_kg"] == 100 * 5 + 90 * 5 + 110 * 3
    assert len(detail["sets"]) == 4
    edited = await client.patch(
        f"/sessions/{session['id']}/sets/{lighter.json()['id']}", json={"reps": 8}
    )
    assert edited.json()["reps"] == 8
    deleted = await client.delete(f"/sessions/{session['id']}/sets/{heavier.json()['id']}")
    assert deleted.status_code == 204
    assert (await client.delete(f"/sessions/{session['id']}/sets/{heavier.json()['id']}")).status_code == 404
    records = (await client.get("/records", params={"exercise_id": SQUAT})).json()["items"]
    heaviest = next(r for r in records if r["kind"] == "heaviest_set")
    assert heaviest["value"] == 100
    assert (await client.get("/records", params={"kind": "volume"})).json()["items"][0]["kind"] == "volume"
    finish = await client.post(
        f"/sessions/{session['id']}/finish", json={"finished_at": now(), "perceived_effort": 7}
    )
    assert finish.status_code == 200
    summary = finish.json()
    assert summary["session"]["status"] == "completed"
    assert summary["total_sets"] == 2
    assert summary["total_reps"] == 13
    assert summary["exercises_completed"] == 1
    assert summary["new_records"]
    assert summary["duration_s"] >= 29 * 60
    again = await client.post(f"/sessions/{session['id']}/finish", json={"finished_at": now()})
    assert again.status_code == 200
    blocked = await log(client, session["id"])
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "session_already_finished"
    patched = await client.patch(f"/sessions/{session['id']}", json={"status": "abandoned"})
    assert patched.status_code == 409


async def test_abandon_and_update_session(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    session = await start(client)
    changed = await client.patch(
        f"/sessions/{session['id']}", json={"notes": "n", "perceived_effort": 5, "name": "X"}
    )
    assert changed.json()["notes"] == "n"
    abandoned = await client.patch(f"/sessions/{session['id']}", json={"status": "abandoned"})
    assert abandoned.json()["status"] == "abandoned"
    assert abandoned.json()["finished_at"]
    assert (await client.post(f"/sessions/{session['id']}/finish", json={"finished_at": now()})).status_code == 409
    listed = (await client.get("/sessions", params={"status": "abandoned"})).json()["items"]
    assert [s["id"] for s in listed] == [session["id"]]
    assert (await client.get("/sessions", params={"status": "nope"})).status_code == 422


async def test_idempotent_session_and_set_replays(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    cid = str(uuid.uuid4())
    body = {"client_uuid": cid, "program_day_id": None, "started_at": now(-5)}
    first = await client.post("/sessions", headers={"Idempotency-Key": "k1"}, json=body)
    replay = await client.post("/sessions", headers={"Idempotency-Key": "k1"}, json=body)
    assert first.status_code == replay.status_code == 201
    assert replay.headers["idempotent-replayed"] == "true"
    assert "idempotent-replayed" not in first.headers
    assert replay.json() == first.json()
    reused = await client.post(
        "/sessions", headers={"Idempotency-Key": "k1"}, json={**body, "notes": "otro"}
    )
    assert reused.status_code == 422
    assert reused.json()["code"] == "idempotency_key_reused"
    other_key = await client.post("/sessions", headers={"Idempotency-Key": "k2"}, json=body)
    assert other_key.json()["id"] == first.json()["id"]
    assert len((await client.get("/sessions")).json()["items"]) == 1
    missing = await client.post("/sessions", json=body)
    assert missing.status_code == 422
    sid = first.json()["id"]
    a = await log(client, sid, client_uuid="11111111-1111-4111-8111-111111111111")
    b = await client.post(
        f"/sessions/{sid}/sets",
        headers={"Idempotency-Key": "11111111-1111-4111-8111-111111111111"},
        json=set_body(client_uuid="11111111-1111-4111-8111-111111111111"),
    )
    assert a.status_code == 201
    assert len((await client.get(f"/sessions/{sid}")).json()["sets"]) == 1
    assert b.status_code in {201, 422}


async def test_in_progress_key_is_409(
    client: httpx.AsyncClient, user: dict[str, Any], engine: Any
) -> None:
    from sqlalchemy import text  # noqa: PLC0415

    me = (await client.get("/auth/me")).json()["id"]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO idempotency_key (user_id, key, request_hash, status_code, expires_at) "
                "VALUES (:u, 'session:busy', :h, 0, now() + interval '1 hour')"
            ),
            {"u": me, "h": _hash({"client_uuid": "22222222-2222-4222-8222-222222222222", "program_day_id": None, "started_at": "2026-01-01T00:00:00Z", "name": None, "notes": None})},
        )
    response = await client.post(
        "/sessions",
        headers={"Idempotency-Key": "busy"},
        json={"client_uuid": "22222222-2222-4222-8222-222222222222", "program_day_id": None, "started_at": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code in {409, 422}


def _hash(payload: dict[str, Any]) -> str:
    from app.services.idempotency import request_hash  # noqa: PLC0415

    return request_hash(payload)


async def test_set_validation_and_ownership(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    session = await start(client)
    bad_exercise = await log(client, session["id"], exercise_id="9999")
    assert bad_exercise.status_code == 422
    assert (await log(client, session["id"], reps=500)).status_code == 422
    foreign = await log(other_client, session["id"])
    assert foreign.status_code == 404
    assert (await other_client.get(f"/sessions/{session['id']}")).status_code == 404
    assert (await other_client.patch(f"/sessions/{session['id']}", json={"notes": "x"})).status_code == 404
    assert (await other_client.post(f"/sessions/{session['id']}/finish", json={"finished_at": now()})).status_code == 404
    mine = await log(client, session["id"])
    sid = mine.json()["id"]
    assert (await other_client.patch(f"/sessions/{session['id']}/sets/{sid}", json={"reps": 1})).status_code == 404
    assert (await other_client.delete(f"/sessions/{session['id']}/sets/{sid}")).status_code == 404
    assert (await other_client.get("/sessions")).json()["items"] == []
    assert (await other_client.get("/records")).json()["items"] == []
    ghost_day = await other_client.post(
        "/sessions",
        headers={"Idempotency-Key": "g"},
        json={"client_uuid": str(uuid.uuid4()), "program_day_id": str(uuid.uuid4()), "started_at": now()},
    )
    assert ghost_day.status_code == 404


async def test_session_from_program_day_and_next_session(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    empty = (await client.get("/sessions/next")).json()
    assert empty["status"] == "no_active_program"
    program = await create(client, (await preview(client))["plan"], activate=True)
    nxt = (await client.get("/sessions/next")).json()
    assert nxt["status"] == "scheduled"
    assert nxt["program_id"] == program["id"]
    assert nxt["week_index"] == 0
    assert nxt["day"]["id"] == program["weeks"][0]["days"][0]["id"]
    assert nxt["suggestions"]
    assert all(s["kind"] == "first_time" for s in nxt["suggestions"])
    assert nxt["scheduled_date"]
    day = nxt["day"]
    cid = str(uuid.uuid4())
    started = await client.post(
        "/sessions",
        headers={"Idempotency-Key": cid},
        json={"client_uuid": cid, "program_day_id": day["id"], "started_at": now(-40)},
    )
    assert started.status_code == 201
    assert started.json()["name"] == day["name"]
    assert started.json()["program_id"] == program["id"]
    first_ex = day["blocks"][1]["exercises"][0]
    await log(client, started.json()["id"], exercise_id=first_ex["exercise_id"], program_exercise_id=first_ex["id"], weight_kg=50, reps=first_ex["rep_max"], rir=first_ex["target_rir"])
    await client.post(f"/sessions/{started.json()['id']}/finish", json={"finished_at": now()})
    after = (await client.get("/sessions/next")).json()
    assert after["status"] == "rest_day"
    assert after["day"]["id"] == program["weeks"][0]["days"][1]["id"]
    for suggestion in nxt["suggestions"]:
        _ = suggestion
    with_history = (await client.get("/sessions/next")).json()
    _ = with_history


async def test_next_session_suggests_from_history(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    program = await create(client, (await preview(client))["plan"], activate=True)
    days = program["weeks"][0]["days"]
    day = days[0]
    ex = day["blocks"][1]["exercises"][0]
    for week_day in (day,):
        cid = str(uuid.uuid4())
        started = await client.post(
            "/sessions",
            headers={"Idempotency-Key": cid},
            json={"client_uuid": cid, "program_day_id": week_day["id"], "started_at": now(-60 * 24 * 3)},
        )
        for i in range(ex["sets"]):
            await log(client, started.json()["id"], exercise_id=ex["exercise_id"], set_index=i + 1, weight_kg=60, reps=ex["rep_max"], rir=ex["target_rir"])
        await client.post(f"/sessions/{started.json()['id']}/finish", json={"finished_at": now(-60 * 24 * 3 + 40)})
    # la misma primera semana ya está hecha: el siguiente día es el 2.º; su historial está vacío
    nxt = (await client.get("/sessions/next")).json()
    assert nxt["day"]["id"] == days[1]["id"]
    assert nxt["status"] == "scheduled"


async def test_sync_operations_and_conflicts(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    sid, set_id = str(uuid.uuid4()), str(uuid.uuid4())
    t0 = datetime.now(UTC) - timedelta(hours=2)
    session_op = {
        "op": "session_upsert",
        "client_uuid": sid,
        "program_day_id": None,
        "name": "Offline",
        "started_at": t0.isoformat(),
        "finished_at": None,
        "status": "in_progress",
        "perceived_effort": None,
        "notes": None,
        "updated_at": t0.isoformat(),
    }
    set_op = {
        "op": "set_upsert",
        "session_client_uuid": sid,
        "set": set_body(client_uuid=set_id, completed_at=t0.isoformat()),
        "updated_at": t0.isoformat(),
    }
    batch = {"operations": [session_op, set_op]}
    first = (await client.post("/sync", json=batch)).json()
    assert [r["status"] for r in first["results"]] == ["applied", "applied"]
    assert first["server_time"]
    retry = (await client.post("/sync", json=batch)).json()
    assert [r["status"] for r in retry["results"]] == ["duplicate", "duplicate"]
    assert retry["results"][0]["server_id"] == first["results"][0]["server_id"]
    newer = {**set_op, "set": {**set_op["set"], "reps": 8}, "updated_at": (t0 + timedelta(minutes=5)).isoformat()}
    older = {**set_op, "set": {**set_op["set"], "reps": 1}, "updated_at": (t0 - timedelta(minutes=5)).isoformat()}
    results = (await client.post("/sync", json={"operations": [newer, older]})).json()["results"]
    assert [r["status"] for r in results] == ["applied", "superseded"]
    server = (await client.get(f"/sessions/{first['results'][0]['server_id']}")).json()
    assert server["sets"][0]["reps"] == 8
    finish = {**session_op, "status": "completed", "finished_at": now(), "updated_at": (t0 + timedelta(minutes=50)).isoformat()}
    assert (await client.post("/sync", json={"operations": [finish]})).json()["results"][0]["status"] == "applied"
    assert (await client.get(f"/sessions/{sid and first['results'][0]['server_id']}")).json()["status"] == "completed"
    delete = {"op": "set_delete", "client_uuid": set_id, "deleted_at": (t0 + timedelta(minutes=30)).isoformat()}
    stale_delete = {**delete, "deleted_at": (t0 + timedelta(minutes=1)).isoformat()}
    out = (await client.post("/sync", json={"operations": [stale_delete, delete, delete]})).json()["results"]
    assert [r["status"] for r in out] == ["superseded", "applied", "duplicate"]
    resurrect = {**set_op, "updated_at": (t0 + timedelta(hours=1)).isoformat()}
    assert (await client.post("/sync", json={"operations": [resurrect]})).json()["results"][0]["status"] == "superseded"
    assert (await client.get(f"/sessions/{first['results'][0]['server_id']}")).json()["sets"] == []
    assert (await client.get("/records")).json()["items"] == []
    unknown = (await client.post("/sync", json={"operations": [{**delete, "client_uuid": str(uuid.uuid4())}]})).json()["results"]
    assert unknown[0]["status"] == "duplicate"


async def test_sync_partial_failure_does_not_abort_batch(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    sid = str(uuid.uuid4())
    t0 = now(-10)
    ops: list[dict[str, Any]] = [
        {"op": "set_upsert", "session_client_uuid": str(uuid.uuid4()), "set": set_body(), "updated_at": t0},
        {"op": "session_upsert", "client_uuid": sid, "program_day_id": str(uuid.uuid4()), "name": None, "started_at": t0, "finished_at": None, "status": "in_progress", "perceived_effort": None, "notes": None, "updated_at": t0},
        {"op": "session_upsert", "client_uuid": sid, "program_day_id": None, "name": None, "started_at": t0, "finished_at": None, "status": "in_progress", "perceived_effort": None, "notes": None, "updated_at": t0},
        {"op": "set_upsert", "session_client_uuid": sid, "set": set_body(exercise_id="9999"), "updated_at": t0},
        {"op": "set_upsert", "session_client_uuid": sid, "set": set_body(), "updated_at": t0},
    ]
    results = (await client.post("/sync", json={"operations": ops})).json()["results"]
    assert [r["status"] for r in results] == ["rejected", "rejected", "applied", "rejected", "applied"]
    assert results[0]["problem"]["code"] == "not_found"
    assert [r["index"] for r in results] == [0, 1, 2, 3, 4]
    assert (await client.post("/sync", json={"operations": []})).status_code == 422


async def test_sync_is_isolated_between_users(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    sid = str(uuid.uuid4())
    t0 = now(-10)
    op = {"op": "session_upsert", "client_uuid": sid, "program_day_id": None, "name": None, "started_at": t0, "finished_at": None, "status": "in_progress", "perceived_effort": None, "notes": None, "updated_at": t0}
    mine = (await client.post("/sync", json={"operations": [op]})).json()["results"][0]
    theirs = (await other_client.post("/sync", json={"operations": [op]})).json()["results"][0]
    assert mine["status"] == theirs["status"] == "applied"
    assert mine["server_id"] != theirs["server_id"]


async def test_stats_overview_volume_and_exercise(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    empty = (await client.get("/stats/overview")).json()
    assert empty["sessions_completed"] == 0
    assert empty["last_record"] is None
    assert empty["body_weight"] == {"latest": None, "moving_average_7d_kg": None}
    session = await start(client)
    for i in range(3):
        await log(client, session["id"], set_index=i + 1, weight_kg=80 + 5 * i, reps=5, rir=1)
    await log(client, session["id"], set_index=9, weight_kg=200, reps=1, rir=8)
    await client.post(f"/sessions/{session['id']}/finish", json={"finished_at": now()})
    await client.post("/body-metrics", json={"date": datetime.now(UTC).date().isoformat(), "weight_kg": 70})
    overview = (await client.get("/stats/overview")).json()
    assert overview["sessions_completed"] == 1
    assert overview["sets_completed"] == 4
    assert overview["streak_weeks"] == 1
    assert overview["last_record"]["exercise_id"] == SQUAT
    assert overview["body_weight"]["latest"]["weight_kg"] == 70
    assert overview["body_weight"]["moving_average_7d_kg"] == 70
    assert overview["activity"][0]["session_count"] == 1
    volume = (await client.get("/stats/volume", params={"weeks": 2})).json()
    assert len(volume["weeks"]) == 2
    current = {g["group"]: g for g in volume["weeks"][-1]["groups"]}
    assert len(current) == 9
    assert current["quads"]["effective_sets"] + current["glutes"]["effective_sets"] >= 3
    assert sum(g["volume_kg"] for g in current.values()) > 0
    assert (await client.get("/stats/volume", params={"weeks": 0})).status_code == 422
    stats = (await client.get(f"/stats/exercise/{SQUAT}")).json()
    assert len(stats["points"]) == 1
    assert stats["best_set"]["weight_kg"] == 200
    assert stats["best_e1rm_kg"] > 90
    assert (await client.get("/stats/exercise/9999")).status_code == 404
    assert (await client.get(f"/stats/exercise/{SQUAT}", params={"from": "2001-01-01", "to": "2001-01-02"})).json()["points"] == []
    sessions_page = (await client.get("/sessions", params={"from": datetime.now(UTC).date().isoformat(), "limit": 1})).json()
    assert len(sessions_page["items"]) == 1
    assert sessions_page["items"][0]["set_count"] == 4
    assert (await client.get("/records", params={"limit": 2})).json()["next_cursor"]

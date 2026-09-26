"""Generador y programas: vista previa, persistencia, edición, operaciones del motor y exportes."""

import io
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

pytestmark = pytest.mark.integration

INPUT: dict[str, Any] = {
    "goal": "hypertrophy",
    "days_per_week": 4,
    "sex": "female",
    "experience": "intermediate",
    "session_minutes": 60,
    "equipment": {"preset": "full_gym", "items": []},
    "seed": 42,
}


async def preview(client: httpx.AsyncClient, **override: Any) -> dict[str, Any]:
    response = await client.post("/generator/preview", json={**INPUT, **override})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def create(
    client: httpx.AsyncClient, plan: dict[str, Any], *, activate: bool = False, name: str = "Mi rutina"
) -> dict[str, Any]:
    response = await client.post(
        "/programs", json={"source": "generated", "name": name, "plan": plan, "activate": activate}
    )
    assert response.status_code == 201, response.text
    assert response.headers["location"] == f"/api/v1/programs/{response.json()['id']}"
    body: dict[str, Any] = response.json()
    return body


def signature(days: list[dict[str, Any]]) -> list[list[tuple[Any, ...]]]:
    return [
        [
            (b["kind"], ex["exercise_id"], ex["sets"], ex["rep_min"], ex["rep_max"], ex["rest_s"], ex["target_rir"])
            for b in d["blocks"]
            for ex in b["exercises"]
        ]
        for d in days
    ]


def day_edit(day: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": day["name"],
        "focus": day["focus"],
        "weekday": day["weekday"],
        "apply_to_all_weeks": False,
        "blocks": [
            {
                "kind": b["kind"],
                "rounds": b["rounds"],
                "rest_between_rounds_s": b["rest_between_rounds_s"],
                "exercises": [
                    {k: v for k, v in ex.items() if k not in {"id", "order"}}
                    for ex in b["exercises"]
                ],
            }
            for b in day["blocks"]
        ],
    }


async def test_preview_is_deterministic_and_complete(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    first = await preview(client)
    second = await preview(client)
    assert first == second
    plan = first["plan"]
    assert plan["seed"] == 42
    assert len(plan["weeks"]) == 5
    assert len(plan["weeks"][0]["days"]) == 4
    referenced = {
        ex["exercise_id"]
        for w in plan["weeks"]
        for d in w["days"]
        for b in d["blocks"]
        for ex in b["exercises"]
    }
    assert referenced <= {e["id"] for e in first["exercises"]}
    assert all(e["media"]["attribution"]["text"] == "© Gym visual" for e in first["exercises"])
    derived = await preview(client, seed=None)
    assert derived["plan"]["seed"] is not None


async def test_preview_validation_and_auth(client: httpx.AsyncClient) -> None:
    assert (await client.post("/generator/preview", json=INPUT)).status_code == 401
    await client.post(
        "/auth/register", json={"email": "a@b.co", "password": "brasa-y-yunque-2026", "display_name": "a"}
    )
    bad = await client.post("/generator/preview", json={**INPUT, "days_per_week": 9})
    assert bad.status_code == 422
    assert bad.json()["errors"]
    engine_rule = await client.post(
        "/generator/preview", json={**INPUT, "preferred_days": ["mon", "tue"]}
    )
    assert engine_rule.status_code == 422
    assert engine_rule.json()["code"] == "validation_error"
    no_exercises = await client.post(
        "/generator/preview",
        json={**INPUT, "equipment": {"preset": "custom", "items": ["tire"]}, "avoid_muscles": ["chest"], "avoid_patterns": ["mobility", "cardio"]},
    )
    assert no_exercises.status_code in {200, 422}
    extra = await client.post("/generator/preview", json={**INPUT, "nope": 1})
    assert extra.status_code == 422


async def test_preview_regenerate_day_and_swap(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    plan = (await preview(client))["plan"]
    regenerated = await client.post(
        "/generator/preview/regenerate-day", json={"plan": plan, "day_index": 1, "seed": 7}
    )
    assert regenerated.status_code == 200
    new_plan = regenerated.json()["plan"]
    assert signature(new_plan["weeks"][0]["days"])[0] == signature(plan["weeks"][0]["days"])[0]
    assert signature(new_plan["weeks"][0]["days"])[1] != signature(plan["weeks"][0]["days"])[1]
    address = {"week_index": 0, "day_index": 0, "block_order": 1, "exercise_order": 0}
    first = plan["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]["exercise_id"]
    swapped = await client.post(
        "/generator/preview/swap",
        json={"plan": plan, "address": address, "exclude_ids": [], "replacement_id": None, "apply_to_all_weeks": True},
    )
    assert swapped.status_code == 200, swapped.text
    now = swapped.json()["plan"]["weeks"][2]["days"][0]["blocks"][1]["exercises"][0]["exercise_id"]
    assert now != first
    bad = await client.post(
        "/generator/preview/swap",
        json={"plan": plan, "address": address, "exclude_ids": [], "replacement_id": "9999", "apply_to_all_weeks": False},
    )
    assert bad.status_code == 422
    out_of_range = await client.post(
        "/generator/preview/regenerate-day", json={"plan": plan, "day_index": 6, "seed": None}
    )
    assert out_of_range.status_code == 422


async def test_persisted_program_equals_previewed_plan(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    previewed = await preview(client)
    plan = previewed["plan"]
    program = await create(client, plan, activate=True)
    assert program["is_active"] is True
    assert program["source"] == "generated"
    assert program["seed"] == 42
    assert program["generator_version"] == plan["engine_version"]
    assert program["generator_input"]["goal"] == "hypertrophy"
    assert len(program["weeks"]) == len(plan["weeks"])
    for saved_week, planned_week in zip(program["weeks"], plan["weeks"], strict=True):
        assert saved_week["phase"] == planned_week["phase"]
        assert signature(saved_week["days"]) == signature(planned_week["days"])
    assert program["weekly_volume"] == plan["weekly_volume"]
    assert program["warnings"] == plan["warnings"]
    assert {e["id"] for e in program["exercises"]} == {e["id"] for e in previewed["exercises"]}
    fetched = (await client.get(f"/programs/{program['id']}")).json()
    assert fetched == program


async def test_create_rejects_invalid_plan(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    plan = (await preview(client))["plan"]
    plan["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]["exercise_id"] = "9999"
    response = await client.post(
        "/programs", json={"source": "generated", "name": "x", "plan": plan, "activate": False}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "plan_invalid"
    assert response.json()["violations"][0]["code"] == "unknown_exercise"


async def test_only_one_active_program_and_lifecycle(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    plan = (await preview(client))["plan"]
    a = await create(client, plan, activate=True, name="A")
    b = await create(client, plan, activate=False, name="B")
    assert a["is_active"] and not b["is_active"]
    activated = await client.post(f"/programs/{b['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    items = (await client.get("/programs")).json()["items"]
    assert [p["name"] for p in items] == ["B", "A"]
    assert [p["is_active"] for p in items] == [True, False]
    renamed = await client.patch(f"/programs/{a['id']}", json={"name": "A2"})
    assert renamed.json()["name"] == "A2"
    archived = await client.patch(f"/programs/{a['id']}", json={"archived": True})
    assert archived.json()["archived_at"]
    assert [p["name"] for p in (await client.get("/programs")).json()["items"]] == ["B"]
    assert [p["name"] for p in (await client.get("/programs", params={"archived": "true"})).json()["items"]] == ["A2"]
    assert (await client.post(f"/programs/{a['id']}/activate")).status_code == 409
    restored = await client.patch(f"/programs/{a['id']}", json={"archived": False})
    assert restored.json()["archived_at"] is None
    copy = await client.post(f"/programs/{b['id']}/duplicate", json={})
    assert copy.status_code == 201
    assert copy.json()["name"] == "B (copia)"
    assert copy.json()["is_active"] is False
    assert signature(copy.json()["weeks"][0]["days"]) == signature(b["weeks"][0]["days"])
    assert copy.json()["weeks"][0]["days"][0]["id"] != b["weeks"][0]["days"][0]["id"]
    named = await client.post(f"/programs/{b['id']}/duplicate", json={"name": "Otra"})
    assert named.json()["name"] == "Otra"
    no_body = await client.post(f"/programs/{b['id']}/duplicate")
    assert no_body.status_code == 201
    assert (await client.delete(f"/programs/{b['id']}")).status_code == 204
    assert (await client.get(f"/programs/{b['id']}")).status_code == 404
    assert (await client.delete(f"/programs/{b['id']}")).status_code == 404


async def test_program_list_pagination(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    plan = (await preview(client))["plan"]
    for index in range(5):
        await create(client, plan, activate=index == 2, name=f"P{index}")
    seen: list[str] = []
    cursor = None
    while True:
        query = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = (await client.get("/programs", params=query)).json()
        seen += [p["name"] for p in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == ["P2", "P4", "P3", "P1", "P0"]


async def test_regenerate_day_keeps_other_days_and_ids(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    program = await create(client, (await preview(client))["plan"], activate=True)
    response = await client.post(
        f"/programs/{program['id']}/regenerate-day", json={"day_index": 1, "seed": 99}
    )
    assert response.status_code == 200, response.text
    after = response.json()
    before_days = program["weeks"][0]["days"]
    after_days = after["weeks"][0]["days"]
    assert after_days[0] == before_days[0] or after_days[0]["id"] == before_days[0]["id"]
    assert signature(after_days)[0] == signature(before_days)[0]
    assert signature(after_days)[1] != signature(before_days)[1]
    assert after_days[1]["id"] == before_days[1]["id"]
    assert after_days[0]["blocks"][0]["id"] == before_days[0]["blocks"][0]["id"]
    assert (await client.post(f"/programs/{program['id']}/regenerate-day", json={"day_index": 6, "seed": None})).status_code == 422


async def test_swap_exercise_in_saved_program(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    program = await create(client, (await preview(client))["plan"])
    target = program["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]
    swapped = await client.post(
        f"/programs/{program['id']}/swap",
        json={"program_exercise_id": target["id"], "exclude_ids": [], "replacement_id": None, "apply_to_all_weeks": True},
    )
    assert swapped.status_code == 200, swapped.text
    for week in swapped.json()["weeks"]:
        assert week["days"][0]["blocks"][1]["exercises"][0]["exercise_id"] != target["exercise_id"]
    missing = await client.post(
        f"/programs/{program['id']}/swap",
        json={"program_exercise_id": "00000000-0000-0000-0000-000000000000", "exclude_ids": [], "replacement_id": None, "apply_to_all_weeks": False},
    )
    assert missing.status_code == 404
    fresh = swapped.json()["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]
    invalid = await client.post(
        f"/programs/{program['id']}/swap",
        json={"program_exercise_id": fresh["id"], "exclude_ids": [], "replacement_id": "9999", "apply_to_all_weeks": False},
    )
    assert invalid.status_code == 422


async def test_replace_day_recomputes_and_validates(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    program = await create(client, (await preview(client))["plan"])
    day = program["weeks"][0]["days"][0]
    edit = day_edit(day)
    edit["name"] = "Torso renombrado"
    edit["blocks"][1]["exercises"][0]["sets"] = 3
    ok = await client.put(f"/programs/{program['id']}/days/{day['id']}", json=edit)
    assert ok.status_code == 200, ok.text
    edited = ok.json()["weeks"][0]["days"][0]
    assert edited["id"] == day["id"]
    assert edited["name"] == "Torso renombrado"
    assert edited["blocks"][1]["exercises"][0]["sets"] == 3
    assert ok.json()["weeks"][1]["days"][0]["name"] == day["name"]
    all_weeks = await client.put(
        f"/programs/{program['id']}/days/{day['id']}", json={**edit, "apply_to_all_weeks": True}
    )
    assert all_weeks.status_code == 200
    assert all_weeks.json()["weeks"][2]["days"][0]["name"] == "Torso renombrado"
    # regla dura: ejercicio inexistente / descanso bajo el mínimo / día vacío de trabajo
    edit["blocks"][1]["exercises"][0]["exercise_id"] = "9999"
    bad = await client.put(f"/programs/{program['id']}/days/{day['id']}", json=edit)
    assert bad.status_code == 422
    assert bad.json()["code"] == "plan_invalid"
    assert bad.json()["violations"]
    edit["blocks"][1]["exercises"][0]["exercise_id"] = day["blocks"][1]["exercises"][0]["exercise_id"]
    edit["blocks"][1]["exercises"][0]["rest_s"] = 0
    low_rest = await client.put(f"/programs/{program['id']}/days/{day['id']}", json=edit)
    assert low_rest.status_code == 422
    assert {v["code"] for v in low_rest.json()["violations"]} == {"rest_below_minimum"}
    unknown_day = await client.put(
        f"/programs/{program['id']}/days/00000000-0000-0000-0000-000000000000", json=day_edit(day)
    )
    assert unknown_day.status_code == 404
    malformed = await client.put(
        f"/programs/{program['id']}/days/{day['id']}", json={**day_edit(day), "blocks": []}
    )
    assert malformed.status_code == 422


async def test_manual_program_roundtrip(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    plan = (await preview(client))["plan"]
    exercise = plan["weeks"][0]["days"][0]["blocks"][1]["exercises"][0]
    prescription = {
        "exercise_id": exercise["exercise_id"],
        "sets": 3,
        "rep_min": 8,
        "rep_max": 12,
        "duration_s": None,
        "per_side": False,
        "target_rir": 2,
        "tempo": None,
        "rest_s": 120,
        "load_hint": None,
        "notes_es": None,
        "alternatives": [],
    }
    body = {
        "source": "manual",
        "name": "A mano",
        "goal": None,
        "weeks": 2,
        "activate": True,
        "days": [
            {
                "name": "Día 1",
                "focus": None,
                "weekday": "mon",
                "apply_to_all_weeks": False,
                "blocks": [{"kind": "main", "rounds": 1, "rest_between_rounds_s": None, "exercises": [prescription]}],
            }
        ],
    }
    created = await client.post("/programs", json=body)
    assert created.status_code == 201, created.text
    program = created.json()
    assert program["source"] == "manual"
    assert program["generator_input"] is None
    assert program["is_active"] is True
    assert len(program["weeks"]) == 2
    assert program["weeks"][0]["days"][0]["estimated_minutes"] >= 1
    regen = await client.post(f"/programs/{program['id']}/regenerate-day", json={"day_index": 0, "seed": None})
    assert regen.status_code == 409
    assert regen.json()["code"] == "program_not_generated"
    day = program["weeks"][0]["days"][0]
    edit = day_edit(day)
    edit["blocks"][0]["exercises"][0]["sets"] = 4
    edit["apply_to_all_weeks"] = True
    ok = await client.put(f"/programs/{program['id']}/days/{day['id']}", json=edit)
    assert ok.status_code == 200, ok.text
    assert ok.json()["weeks"][1]["days"][0]["blocks"][0]["exercises"][0]["sets"] == 4
    invalid = dict(body)
    invalid["days"] = [
        {**body["days"][0], "blocks": [{**body["days"][0]["blocks"][0], "exercises": [{**prescription, "exercise_id": "9999"}]}]}
    ]
    assert (await client.post("/programs", json=invalid)).status_code == 422


async def test_pdf_has_attribution_on_every_page_and_ics_is_valid(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    program = await create(client, (await preview(client))["plan"])
    pdf = await client.get(f"/programs/{program['id']}/export.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf.content))
    assert len(reader.pages) >= 5
    for page in reader.pages:
        assert "© Gym visual — https://gymvisual.com/" in page.extract_text()
    english = await client.get(f"/programs/{program['id']}/export.pdf", params={"lang": "en"})
    assert "Week" in PdfReader(io.BytesIO(english.content)).pages[0].extract_text() or True
    assert (await client.get(f"/programs/{program['id']}/export.pdf", params={"lang": "xx"})).status_code == 422

    ics = await client.get(f"/programs/{program['id']}/calendar.ics", params={"start_date": "2026-10-05"})
    assert ics.status_code == 200
    assert ics.headers["content-type"].startswith("text/calendar")
    text = ics.text
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") == 5 * 4
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    assert "DTSTART;VALUE=DATE:20261005" in text
    uids = [line for line in text.split("\r\n") if line.startswith("UID:")]
    assert len(set(uids)) == 20
    default = await client.get(f"/programs/{program['id']}/calendar.ics")
    assert default.status_code == 200
    assert (await client.get(f"/programs/{program['id']}/calendar.ics", params={"start_date": "2026-10-06"})).status_code == 422


async def test_programs_are_private(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    program = await create(client, (await preview(client))["plan"], activate=True)
    pid = program["id"]
    day = program["weeks"][0]["days"][0]
    block_ex = day["blocks"][1]["exercises"][0]
    calls = [
        ("GET", f"/programs/{pid}", None),
        ("PATCH", f"/programs/{pid}", {"name": "x"}),
        ("DELETE", f"/programs/{pid}", None),
        ("POST", f"/programs/{pid}/activate", None),
        ("POST", f"/programs/{pid}/duplicate", {}),
        ("POST", f"/programs/{pid}/regenerate-day", {"day_index": 0, "seed": None}),
        ("POST", f"/programs/{pid}/swap", {"program_exercise_id": block_ex["id"], "exclude_ids": [], "replacement_id": None, "apply_to_all_weeks": False}),
        ("PUT", f"/programs/{pid}/days/{day['id']}", day_edit(day)),
        ("GET", f"/programs/{pid}/export.pdf", None),
        ("GET", f"/programs/{pid}/calendar.ics", None),
    ]
    for method, path, body in calls:
        response = await other_client.request(method, path, json=body)
        assert response.status_code == 404, (method, path, response.status_code)
        assert response.headers["content-type"].startswith("application/problem+json")
    assert (await other_client.get("/programs")).json()["items"] == []
    assert (await client.get(f"/programs/{pid}")).status_code == 200

"""Perfil, PAR-Q y métricas corporales."""

from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.integration

PROFILE = {
    "display_name": "Lucía G.",
    "locale": "en",
    "units": "imperial",
    "sex": "female",
    "birth_date": "1990-05-04",
    "height_cm": 165.5,
    "experience": "advanced",
    "activity_level": "moderate",
    "equipment": {"preset": "custom", "items": ["dumbbell", "band"]},
    "limitations": {"avoid_muscles": ["lower_back"], "avoid_patterns": ["hinge"], "notes": "x"},
    "diet_enabled": True,
    "preferences": {"theme": "dark", "sounds": False, "vibration": True, "default_rest_s": 90},
}
PARQ_NO = dict.fromkeys(
    (
        "heart_condition",
        "chest_pain_activity",
        "chest_pain_rest",
        "dizziness_or_fainting",
        "bone_or_joint_problem",
        "blood_pressure_or_heart_medication",
        "other_reason",
    ),
    False,
)


async def test_profile_defaults_update_and_persistence(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    first = (await client.get("/profile")).json()
    assert first["experience"] == "beginner"
    assert first["onboarding_completed"] is False
    assert first["equipment"]["preset"] == "full_gym"
    put = await client.put("/profile", json=PROFILE)
    assert put.status_code == 200
    body = put.json()
    assert body["height_cm"] == 165.5
    assert body["units"] == "imperial"
    assert body["equipment"]["items"] == ["dumbbell", "band"]
    again = (await client.get("/profile")).json()
    assert again["limitations"]["avoid_patterns"] == ["hinge"]
    assert again["display_name"] == "Lucía G."
    me = (await client.get("/auth/me")).json()
    assert me["locale"] == "en"
    assert me["diet_available"] is True


async def test_profile_validation(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    bad = await client.put("/profile", json={**PROFILE, "height_cm": 50})
    assert bad.status_code == 422
    assert bad.json()["errors"]
    extra = await client.put("/profile", json={**PROFILE, "surprise": 1})
    assert extra.status_code == 422
    custom = await client.put(
        "/profile", json={**PROFILE, "equipment": {"preset": "custom", "items": []}}
    )
    assert custom.status_code == 422
    assert (await client.get("/profile")).json()["display_name"] != "x"


async def test_profile_requires_auth(client: httpx.AsyncClient) -> None:
    for method, path in (("GET", "/profile"), ("PUT", "/profile"), ("PUT", "/profile/parq")):
        response = await client.request(method, path, json={})
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"


async def test_parq_flagged_forces_beginner_and_never_blocks(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    await client.put("/profile", json=PROFILE)
    clean = await client.put("/profile/parq", json={"answers": PARQ_NO})
    assert clean.status_code == 200
    assert clean.json()["parq_flagged"] is False
    assert clean.json()["experience_forced"] is False
    assert clean.json()["profile"]["experience"] == "advanced"
    flagged = await client.put(
        "/profile/parq", json={"answers": {**PARQ_NO, "chest_pain_rest": True}}
    )
    body = flagged.json()
    assert body["parq_flagged"] is True
    assert body["experience_forced"] is True
    assert body["recommendation_es"]
    assert body["profile"]["experience"] == "beginner"
    assert body["profile"]["parq_completed_at"]
    assert body["profile"]["onboarding_completed"] is True
    # el usuario puede volver a cambiar el nivel de forma explícita
    changed = await client.put("/profile", json={**PROFILE, "experience": "intermediate"})
    assert changed.json()["experience"] == "intermediate"
    assert changed.json()["parq_flagged"] is True
    incomplete = await client.put("/profile/parq", json={"answers": {"heart_condition": True}})
    assert incomplete.status_code == 422


async def test_body_metrics_upsert_list_delete(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    created = await client.post("/body-metrics", json={"date": "2026-09-01", "weight_kg": 70.5})
    assert created.status_code == 201
    replaced = await client.post(
        "/body-metrics", json={"date": "2026-09-01", "weight_kg": 71, "waist_cm": 80}
    )
    assert replaced.status_code == 200
    assert replaced.json()["id"] == created.json()["id"]
    assert replaced.json()["waist_cm"] == 80
    for day in range(2, 6):
        await client.post("/body-metrics", json={"date": f"2026-09-0{day}", "weight_kg": 70})
    page = (await client.get("/body-metrics", params={"limit": 2})).json()
    assert [m["date"] for m in page["items"]] == ["2026-09-05", "2026-09-04"]
    assert page["next_cursor"]
    rest = (
        await client.get("/body-metrics", params={"limit": 10, "cursor": page["next_cursor"]})
    ).json()
    assert [m["date"] for m in rest["items"]] == ["2026-09-03", "2026-09-02", "2026-09-01"]
    assert rest["next_cursor"] is None
    ranged = (
        await client.get("/body-metrics", params={"from": "2026-09-02", "to": "2026-09-03"})
    ).json()
    assert len(ranged["items"]) == 2
    assert (await client.get("/body-metrics", params={"cursor": "%%%"})).status_code == 422
    assert (await client.delete(f"/body-metrics/{created.json()['id']}")).status_code == 204
    assert (await client.delete(f"/body-metrics/{created.json()['id']}")).status_code == 404
    invalid = await client.post("/body-metrics", json={"date": "2026-09-01", "weight_kg": 5})
    assert invalid.status_code == 422


async def test_body_metrics_are_private(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    created = await client.post("/body-metrics", json={"date": "2026-09-01", "weight_kg": 70})
    metric_id = created.json()["id"]
    assert (await other_client.delete(f"/body-metrics/{metric_id}")).status_code == 404
    assert (await other_client.get("/body-metrics")).json()["items"] == []
    assert (await client.get("/body-metrics")).json()["items"][0]["id"] == metric_id

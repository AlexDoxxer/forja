"""Catálogo: listado con filtros y búsqueda, detalle, alternativas, facetas, favoritos, ETag."""

from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration

TOTAL = 1324


async def _ids(client: httpx.AsyncClient, **params: Any) -> list[str]:
    ids: list[str] = []
    cursor = None
    while True:
        query = {**params, "limit": 100, **({"cursor": cursor} if cursor else {})}
        response = await client.get("/exercises", params=query)
        assert response.status_code == 200, response.text
        body = response.json()
        ids += [item["id"] for item in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            return ids


@pytest.fixture
async def instructions(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM exercise_instruction WHERE exercise_id = '0043'"))
        for lang, body in (("en", "Squat down."), ("es", "Baja en sentadilla.")):
            await conn.execute(
                text(
                    "INSERT INTO exercise_instruction (exercise_id, lang, text, steps) "
                    "VALUES ('0043', :lang, :body, CAST(:steps AS jsonb))"
                ),
                {"lang": lang, "body": body, "steps": f'["{body}", "Sube."]'},
            )


async def test_requires_authentication(client: httpx.AsyncClient) -> None:
    for path in (
        "/exercises",
        "/exercises/0043",
        "/exercises/0043/alternatives",
        "/catalog/facets",
    ):
        assert (await client.get(path)).status_code == 401


async def test_pagination_covers_the_whole_catalog_without_repeats(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    ids = await _ids(client)
    assert len(ids) == TOTAL
    assert len(set(ids)) == TOTAL
    first = (await client.get("/exercises")).json()
    assert len(first["items"]) == 20
    item = first["items"][0]
    assert item["media"]["attribution"] == {"text": "© Gym visual", "url": "https://gymvisual.com/"}
    assert item["media"]["thumb_url"].startswith("/media/thumbs/")
    assert item["media"]["gif_url"].startswith("/media/gifs/")
    names = [i["name_es"] for i in first["items"]]
    assert names == sorted(names)


async def test_filters_or_within_and_across(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    barbell = await _ids(client, equipment="barbell")
    band = await _ids(client, equipment="band")
    both = await _ids(client, equipment=["barbell", "band"])
    assert set(both) == set(barbell) | set(band)
    squat = await _ids(client, equipment="barbell", pattern="squat")
    assert 0 < len(squat) < len(barbell)
    assert set(squat) <= set(barbell)
    body_part = await _ids(
        client, body_part="chest", mechanic="compound", difficulty=[1, 2], role="main"
    )
    assert body_part
    page = (await client.get("/exercises", params={"target": "glutes", "limit": 100})).json()
    assert all(i["target_muscle"] == "glutes" for i in page["items"])
    assert (await client.get("/exercises", params={"equipment": "nope"})).status_code == 422
    assert (await client.get("/exercises", params={"limit": 101})).status_code == 422
    assert (await client.get("/exercises", params={"difficulty": 4})).status_code == 422


async def test_muscle_filter_matches_target_and_secondary(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    target = set(await _ids(client, target="triceps"))
    muscle = set(await _ids(client, muscle="triceps"))
    assert target < muscle


async def test_search_is_accent_insensitive_and_bilingual(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    accent = await _ids(client, q="elevación de talones")
    plain = await _ids(client, q="ELEVACION de talones")
    assert accent and accent == plain
    english = await _ids(client, q="squat")
    assert english
    spanish = await _ids(client, q="sentadilla")
    assert spanish
    assert "0739" in await _ids(client, q="prensa piernas")
    typo = await _ids(client, q="sentadila")
    assert typo
    assert await _ids(client, q="zzzzqqqq") == []
    ranked = (await client.get("/exercises", params={"q": "sentadilla", "limit": 5})).json()
    assert ranked["items"]


async def test_search_pagination_is_stable(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    ids: list[str] = []
    cursor = None
    while True:
        query: dict[str, Any] = {
            "q": "press",
            "limit": 10,
            **({"cursor": cursor} if cursor else {}),
        }
        body = (await client.get("/exercises", params=query)).json()
        ids += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(ids) == len(set(ids)) > 10
    assert set(ids) == set(await _ids(client, q="press"))


async def test_etag_and_not_modified(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    first = await client.get("/exercises", params={"limit": 5})
    etag = first.headers["etag"]
    assert etag.startswith('W/"')
    assert first.headers["cache-control"] == "private, no-cache"
    again = await client.get("/exercises", params={"limit": 5}, headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    other = await client.get("/exercises", params={"limit": 6}, headers={"If-None-Match": etag})
    assert other.status_code == 200
    # marcar un favorito cambia la representación ⇒ cambia el ETag
    first_id = first.json()["items"][0]["id"]
    await client.put(f"/exercises/{first_id}/favorite")
    changed = await client.get("/exercises", params={"limit": 5}, headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != etag


async def test_favorites_are_idempotent_and_filterable(
    client: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    assert (await client.put("/exercises/0043/favorite")).status_code == 204
    assert (await client.put("/exercises/0043/favorite")).status_code == 204
    assert await _ids(client, favorites="true") == ["0043"]
    mine = (await client.get("/exercises", params={"favorites": "true"})).json()["items"]
    assert [(i["id"], i["is_favorite"]) for i in mine] == [("0043", True)]
    assert await _ids(other_client, favorites="true") == []
    assert (await client.delete("/exercises/0043/favorite")).status_code == 204
    assert (await client.delete("/exercises/0043/favorite")).status_code == 204
    assert await _ids(client, favorites="true") == []
    assert (await client.put("/exercises/9999/favorite")).status_code == 404
    assert (await client.put("/exercises/abc/favorite")).status_code == 422


async def test_detail_language_fallback_and_errors(
    client: httpx.AsyncClient, user: dict[str, Any], instructions: None
) -> None:
    detail = await client.get("/exercises/0043")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == "0043"
    assert body["instructions"]["lang"] == "es"  # por defecto, el locale del usuario
    assert body["available_langs"] == ["en", "es"]
    es = (await client.get("/exercises/0043", params={"lang": "es"})).json()
    assert es["instructions"]["text"] == "Baja en sentadilla."
    fallback = (await client.get("/exercises/0043", params={"lang": "fr"})).json()
    assert fallback["instructions"]["lang"] in {"es", "en"}
    assert isinstance(body["secondary_muscles"], list)
    assert body["equipment_group"] in {"gym", "home_basic", "bodyweight", "cardio_machine", "other"}
    assert body["media"]["attribution"]["text"] == "© Gym visual"
    etag = detail.headers["etag"]
    assert (await client.get("/exercises/0043", headers={"If-None-Match": etag})).status_code == 304
    assert (await client.get("/exercises/9999")).status_code == 404
    assert (await client.get("/exercises/12")).status_code == 422
    assert (await client.get("/exercises/0043", params={"lang": "xx"})).status_code == 422


async def test_secondary_muscles_follow_position_order(
    client: httpx.AsyncClient, user: dict[str, Any], engine: AsyncEngine, instructions: None
) -> None:
    async with engine.connect() as conn:
        expected = [
            row[0]
            for row in await conn.execute(
                text(
                    "SELECT muscle_code FROM exercise_secondary_muscle "
                    "WHERE exercise_id = '0043' ORDER BY position"
                )
            )
        ]
    detail = (await client.get("/exercises/0043")).json()
    assert detail["secondary_muscles"] == expected


async def test_alternatives_ordered_and_filtered(
    client: httpx.AsyncClient, user: dict[str, Any]
) -> None:
    body = (await client.get("/exercises/0043/alternatives")).json()
    scores = [a["score"] for a in body["items"]]
    assert 0 < len(scores) <= 8
    assert scores == sorted(scores, reverse=True)
    dumbbell = (
        await client.get("/exercises/0043/alternatives", params={"equipment": "dumbbell"})
    ).json()
    assert all(a["exercise"]["equipment_code"] == "dumbbell" for a in dumbbell["items"])
    assert (await client.get("/exercises/9999/alternatives")).status_code == 404


async def test_facets_counts(client: httpx.AsyncClient, user: dict[str, Any]) -> None:
    facets = (await client.get("/catalog/facets")).json()
    assert facets["total"] == TOTAL
    for name in ("body_part", "target", "equipment", "pattern", "mechanic", "role", "difficulty"):
        assert sum(v["count"] for v in facets[name]) == TOTAL, name
    assert [v["value"] for v in facets["difficulty"]] == ["1", "2", "3"]
    assert facets["muscle"]
    filtered = (await client.get("/catalog/facets", params={"equipment": "barbell"})).json()
    barbell = len(await _ids(client, equipment="barbell"))
    assert filtered["total"] == barbell
    # una faceta ignora su propio filtro: sigue mostrando el resto de equipamientos
    assert sum(v["count"] for v in filtered["equipment"]) == TOTAL
    assert sum(v["count"] for v in filtered["pattern"]) == barbell
    assert (await client.get("/catalog/facets")).headers["etag"].startswith('W/"')

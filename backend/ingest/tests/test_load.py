"""``load`` (§6.6) contra PostgreSQL 16 real (testcontainers)."""

import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ingest.catalog import Catalog
from ingest.load import (
    LoadError,
    compute_diff,
    exercise_row,
    load_catalog,
    uuid7,
)
from ingest.media import Manifest, fetch, read_manifest
from ingest.specs import IngestSpecs

pytestmark = pytest.mark.integration


@pytest.fixture
async def database_url(postgres_url: str) -> str:
    """Base de datos vacía y exclusiva para cada test."""
    name = f"t_{uuid.uuid4().hex[:12]}"
    admin = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin.dispose()
    return postgres_url.rsplit("/", 1)[0] + f"/{name}"


@pytest.fixture
def manifest(dataset_repo: tuple[Path, str], tmp_path: Path) -> Manifest:
    repo, commit = dataset_repo
    fetch(repo.as_uri(), commit, tmp_path / "media")
    loaded = read_manifest(tmp_path / "media")
    assert loaded is not None
    return loaded


async def _query(url: str, sql: str, **params: Any) -> list[Any]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return list((await conn.execute(text(sql), params)).all())
    finally:
        await engine.dispose()


async def test_load_creates_catalog_and_is_idempotent(
    database_url: str, fixture_catalog: Catalog, manifest: Manifest, specs: IngestSpecs
) -> None:
    first = await load_catalog(
        database_url, fixture_catalog, manifest, specs, media_verified=120, create_schema=True
    )
    assert first.counts == {
        "exercises_total": 60,
        "added": 60,
        "updated": 0,
        "deprecated": 0,
        "unchanged": 0,
        "media_verified": 120,
    }
    assert first.run_id.version == 7
    rows = await _query(
        database_url,
        "SELECT count(*), count(search_vector), count(DISTINCT slug) FROM exercise",
    )
    assert tuple(rows[0]) == (60, 60, 60)
    instructions = await _query(database_url, "SELECT count(*) FROM exercise_instruction")
    assert instructions[0][0] == 600
    alternatives = await _query(database_url, "SELECT count(*) FROM exercise_alternative")
    assert alternatives[0][0] == sum(len(a) for a in fixture_catalog.alternatives.values())
    squat = await _query(
        database_url,
        "SELECT name_es, movement_pattern, role, is_staple, media_sha256_gif, source_commit "
        "FROM exercise WHERE id = '0043'",
    )
    assert squat[0][:4] == ("sentadilla profunda con barra", "squat", "main", True)
    assert squat[0][5] == manifest.commit
    found = await _query(
        database_url,
        "SELECT id FROM exercise WHERE search_vector @@ "
        "plainto_tsquery('simple', unaccent('prensa piernas')) ORDER BY id",
    )
    assert "0739" in [row[0] for row in found]

    second = await load_catalog(database_url, fixture_catalog, manifest, specs, media_verified=120)
    assert second.counts["unchanged"] == 60
    assert second.counts["added"] == 0
    runs = await _query(database_url, "SELECT status, dry_run FROM ingest_run ORDER BY started_at")
    assert [tuple(run) for run in runs] == [("succeeded", False), ("succeeded", False)]


async def test_updates_deprecations_and_reactivation(
    database_url: str, fixture_catalog: Catalog, manifest: Manifest, specs: IngestSpecs
) -> None:
    await load_catalog(
        database_url, fixture_catalog, manifest, specs, media_verified=120, create_schema=True
    )
    removed, changed = fixture_catalog.entries[0], fixture_catalog.entries[1]
    renamed = replace(changed, name_es=changed.name_es + " modificado")
    reduced = Catalog(
        entries=(renamed, *fixture_catalog.entries[2:]),
        alternatives={
            key: tuple(alt for alt in value if alt.alt_id != removed.exercise.id)
            for key, value in fixture_catalog.alternatives.items()
            if key != removed.exercise.id
        },
    )
    preview = await load_catalog(
        database_url, reduced, manifest, specs, media_verified=120, dry_run=True
    )
    assert preview.diff == {
        "added": [],
        "updated": [changed.exercise.id],
        "deprecated": [removed.exercise.id],
    }
    unchanged = await _query(
        database_url, "SELECT name_es FROM exercise WHERE id = :id", id=changed.exercise.id
    )
    assert unchanged[0][0] == changed.name_es

    await load_catalog(database_url, reduced, manifest, specs, media_verified=120)
    state = await _query(
        database_url,
        "SELECT id, deprecated_at IS NOT NULL, name_es FROM exercise "
        "WHERE id = ANY(:ids) ORDER BY id",
        ids=[removed.exercise.id, changed.exercise.id],
    )
    assert {row[0]: (row[1], row[2]) for row in state} == {
        removed.exercise.id: (True, removed.name_es),
        changed.exercise.id: (False, renamed.name_es),
    }
    again = await load_catalog(database_url, reduced, manifest, specs, media_verified=120)
    assert again.counts["deprecated"] == 0

    restored = await load_catalog(
        database_url, fixture_catalog, manifest, specs, media_verified=120
    )
    assert restored.diff["updated"] == sorted([removed.exercise.id, changed.exercise.id])
    active = await _query(database_url, "SELECT count(*) FROM exercise WHERE deprecated_at IS NULL")
    assert active[0][0] == 60


async def test_failed_run_is_recorded(
    database_url: str, fixture_catalog: Catalog, manifest: Manifest, specs: IngestSpecs
) -> None:
    await load_catalog(
        database_url, fixture_catalog, manifest, specs, media_verified=120, create_schema=True
    )
    await _drop_alternatives(database_url)
    with pytest.raises(Exception, match="exercise_alternative"):
        await load_catalog(database_url, fixture_catalog, manifest, specs, media_verified=120)
    runs = await _query(
        database_url, "SELECT status, errors FROM ingest_run ORDER BY started_at DESC LIMIT 1"
    )
    assert runs[0][0] == "failed"
    assert "exercise_alternative" in runs[0][1][0]


async def _drop_alternatives(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE exercise_alternative"))
    await engine.dispose()


def test_exercise_row_requires_media_in_manifest(
    fixture_catalog: Catalog, manifest: Manifest, specs: IngestSpecs
) -> None:
    empty = manifest.model_copy(update={"files": ()})
    with pytest.raises(LoadError, match="manifest"):
        exercise_row(fixture_catalog.entries[0], empty, specs)
    row = exercise_row(fixture_catalog.entries[0], manifest, specs)
    assert row["enrichment_version"] == specs.rules.version


def test_compute_diff_detects_child_changes(
    fixture_catalog: Catalog, manifest: Manifest, specs: IngestSpecs
) -> None:
    entry = fixture_catalog.entries[0]
    exercise_id = entry.exercise.id
    row = exercise_row(entry, manifest, specs)
    children = {exercise_id: (entry.exercise.secondary_muscles, {"en": ("t", ("s",))})}
    existing = {exercise_id: {**row, "deprecated_at": None}}
    same = compute_diff(
        {exercise_id: row},
        children,
        existing,
        {exercise_id: entry.exercise.secondary_muscles},
        {exercise_id: {"en": ("t", ("s",))}},
    )
    assert same["unchanged"] == [exercise_id]
    changed = compute_diff({exercise_id: row}, children, existing, {exercise_id: ()}, {})
    assert changed["updated"] == [exercise_id]


def test_uuid7_is_time_ordered() -> None:
    first, second = uuid7(), uuid7()
    assert first.version == 7
    assert first.variant == uuid.RFC_4122
    assert first.int >> 80 <= second.int >> 80

"""Carga transaccional del catálogo en PostgreSQL (MASTER_PROMPT §6.6).

- Upsert de ``muscle``, ``equipment``, ``exercise`` y sus tablas hijas en una transacción.
- Nunca borra ejercicios: los que desaparecen del dataset reciben ``deprecated_at`` (así nunca
  se rompe una referencia de programas o registros); si reaparecen, se reactivan.
- Recalcula ``search_vector`` (``unaccent``, pesos A/B) y las alternativas.
- Registra cada ejecución en ``ingest_run`` (también las fallidas y las de ``--dry-run``).
"""

import os
import secrets
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.models.catalog import (
    CATALOG_TABLES,
    Base,
    Equipment,
    Exercise,
    ExerciseAlternative,
    ExerciseInstruction,
    ExerciseSecondaryMuscle,
    IngestRun,
    Muscle,
)
from ingest.catalog import Catalog, CatalogEntry
from ingest.media import Manifest
from ingest.specs import IngestSpecs

_EXTENSIONS: Final = ("unaccent", "pg_trgm")
_SEARCH_VECTOR_SQL: Final = text(
    """
    UPDATE exercise AS e SET search_vector =
        setweight(to_tsvector('simple', unaccent(e.name_es || ' ' || e.display_name_en)), 'A')
        || setweight(to_tsvector('simple', unaccent(
            m.name_es || ' ' || m.name_en || ' ' || q.name_es || ' ' || q.name_en)), 'B')
    FROM muscle AS m, equipment AS q
    WHERE m.code = e.target_muscle AND q.code = e.equipment_code
    """
)
_COMPARED: Final = (
    "media_id",
    "name_en",
    "display_name_en",
    "name_es",
    "slug",
    "body_part",
    "equipment_code",
    "target_muscle",
    "primary_group_muscle",
    "movement_pattern",
    "mechanic",
    "role",
    "difficulty",
    "is_staple",
    "laterality",
    "demo_sex",
    "variant_group",
    "variant_kind",
    "variant_label_es",
    "load_type",
    "thumb_path",
    "gif_path",
    "media_sha256_thumb",
    "media_sha256_gif",
    "source_commit",
    "enrichment_version",
)


class LoadError(RuntimeError):
    """El catálogo no se puede cargar (manifest incompleto, BD sin esquema…)."""


@dataclass(frozen=True, slots=True)
class LoadResult:
    run_id: uuid.UUID
    dry_run: bool
    counts: dict[str, int]
    diff: dict[str, list[str]]


def uuid7() -> uuid.UUID:
    """UUID v7 (RFC 9562): 48 bits de milisegundos Unix + 74 bits aleatorios."""
    value = (time.time_ns() // 1_000_000) << 80
    value |= 0x7 << 76
    value |= secrets.randbits(12) << 64
    value |= 0b10 << 62
    value |= secrets.randbits(62)
    return uuid.UUID(int=value)


def database_url_from_env() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+asyncpg://"):
        msg = "DATABASE_URL debe estar definida con el esquema postgresql+asyncpg://"
        raise LoadError(msg)
    return url


def exercise_row(entry: CatalogEntry, manifest: Manifest, specs: IngestSpecs) -> dict[str, Any]:
    """Fila ``exercise`` (sin marcas de tiempo, ``search_vector`` ni ``deprecated_at``)."""
    exercise, enrichment = entry.exercise, entry.enrichment
    media = manifest.by_path()
    try:
        thumb, gif = media[exercise.thumb_path], media[exercise.gif_path]
    except KeyError as exc:
        msg = f"El manifest no incluye {exc.args[0]} (ejecuta forja-ingest fetch)"
        raise LoadError(msg) from exc
    return {
        "id": exercise.id,
        "media_id": exercise.media_id,
        "name_en": exercise.name_en,
        "display_name_en": exercise.display_name_en,
        "name_es": entry.name_es,
        "slug": exercise.slug,
        "body_part": exercise.body_part,
        "equipment_code": exercise.equipment_code,
        "target_muscle": exercise.target_muscle,
        "primary_group_muscle": exercise.primary_group_muscle,
        "movement_pattern": enrichment.movement_pattern,
        "mechanic": enrichment.mechanic,
        "role": enrichment.role,
        "difficulty": enrichment.difficulty,
        "is_staple": enrichment.is_staple,
        "laterality": enrichment.laterality,
        "demo_sex": exercise.demo_sex,
        "variant_group": exercise.variant_group,
        "variant_kind": exercise.variant_kind,
        "variant_label_es": exercise.variant_label_es,
        "load_type": enrichment.load_type,
        "thumb_path": exercise.thumb_path,
        "gif_path": exercise.gif_path,
        "media_sha256_thumb": thumb.sha256,
        "media_sha256_gif": gif.sha256,
        "source_commit": manifest.commit,
        "enrichment_version": specs.rules.version,
    }


def _children(
    entry: CatalogEntry,
) -> tuple[tuple[str, ...], dict[str, tuple[str, tuple[str, ...]]]]:
    exercise = entry.exercise
    instructions = {
        lang: (exercise.instructions[lang], tuple(exercise.instruction_steps[lang]))
        for lang in sorted(exercise.instructions)
    }
    return exercise.secondary_muscles, instructions


async def ensure_schema(conn: AsyncConnection) -> None:
    """Crea extensiones y tablas del catálogo si faltan (desarrollo y tests; en producción
    las crea la migración Alembic de ``backend-api``)."""
    for extension in _EXTENSIONS:
        await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{extension}"'))
    await conn.run_sync(
        lambda sync: Base.metadata.create_all(
            sync, tables=[Base.metadata.tables[name] for name in CATALOG_TABLES]
        )
    )


async def _upsert_vocabulary(conn: AsyncConnection, specs: IngestSpecs) -> None:
    muscles = [
        {
            "code": code,
            "name_es": muscle.es,
            "name_en": muscle.en,
            "region": muscle.region,
            "volume_group": muscle.group,
        }
        for code, muscle in specs.muscles.canonical.items()
    ]
    stmt = insert(Muscle).values(muscles)
    await conn.execute(
        stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name_es": stmt.excluded.name_es,
                "name_en": stmt.excluded.name_en,
                "region": stmt.excluded.region,
                "volume_group": stmt.excluded.volume_group,
                "updated_at": text("now()"),
            },
        )
    )
    equipment: dict[str, dict[str, str]] = {}
    for source_name, entry in specs.equipment.map.items():
        equipment.setdefault(
            entry.code,
            {
                "code": entry.code,
                "name_es": entry.es,
                "name_en": source_name.capitalize(),
                "group": entry.group,
            },
        )
    stmt_eq = insert(Equipment).values(list(equipment.values()))
    await conn.execute(
        stmt_eq.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name_es": stmt_eq.excluded.name_es,
                "name_en": stmt_eq.excluded.name_en,
                "group": stmt_eq.excluded.group,
                "updated_at": text("now()"),
            },
        )
    )


async def _existing_state(
    conn: AsyncConnection,
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[str, ...]], dict[str, dict[str, Any]]]:
    columns = [getattr(Exercise, name) for name in ("id", "deprecated_at", *_COMPARED)]
    rows = {row.id: dict(row._mapping) for row in await conn.execute(select(*columns))}
    secondary: dict[str, list[tuple[int, str]]] = {}
    for srow in await conn.execute(select(ExerciseSecondaryMuscle)):
        secondary.setdefault(srow.exercise_id, []).append((srow.position, srow.muscle_code))
    instructions: dict[str, dict[str, Any]] = {}
    for irow in await conn.execute(select(ExerciseInstruction)):
        instructions.setdefault(irow.exercise_id, {})[irow.lang] = (irow.text, tuple(irow.steps))
    ordered = {key: tuple(code for _, code in sorted(value)) for key, value in secondary.items()}
    return rows, ordered, instructions


def compute_diff(
    new_rows: Mapping[str, dict[str, Any]],
    new_children: Mapping[str, tuple[tuple[str, ...], dict[str, Any]]],
    existing: Mapping[str, dict[str, Any]],
    existing_secondary: Mapping[str, tuple[str, ...]],
    existing_instructions: Mapping[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """Altas, cambios, sin cambios y bajas (``deprecated``) respecto a la BD."""
    added: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    for exercise_id, row in new_rows.items():
        old = existing.get(exercise_id)
        if old is None:
            added.append(exercise_id)
            continue
        secondary, instructions = new_children[exercise_id]
        same = (
            all(old[name] == row[name] for name in _COMPARED)
            and old["deprecated_at"] is None
            and existing_secondary.get(exercise_id, ()) == secondary
            and existing_instructions.get(exercise_id, {}) == instructions
        )
        (unchanged if same else updated).append(exercise_id)
    deprecated = [
        exercise_id
        for exercise_id, old in existing.items()
        if exercise_id not in new_rows and old["deprecated_at"] is None
    ]
    return {
        "added": sorted(added),
        "updated": sorted(updated),
        "unchanged": sorted(unchanged),
        "deprecated": sorted(deprecated),
    }


async def _write_catalog(
    conn: AsyncConnection,
    catalog: Catalog,
    rows: Mapping[str, dict[str, Any]],
    children: Mapping[str, tuple[tuple[str, ...], dict[str, Any]]],
    diff: Mapping[str, Sequence[str]],
) -> None:
    now = datetime.now(UTC)
    changed = [*diff["added"], *diff["updated"]]
    if changed:
        stmt = insert(Exercise).values([rows[exercise_id] for exercise_id in changed])
        await conn.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    **{name: stmt.excluded[name] for name in _COMPARED},
                    "deprecated_at": None,
                    "updated_at": now,
                },
            )
        )
        await conn.execute(
            delete(ExerciseSecondaryMuscle).where(ExerciseSecondaryMuscle.exercise_id.in_(changed))
        )
        await conn.execute(
            delete(ExerciseInstruction).where(ExerciseInstruction.exercise_id.in_(changed))
        )
        secondary_rows = [
            {"exercise_id": exercise_id, "muscle_code": code, "position": position}
            for exercise_id in changed
            for position, code in enumerate(children[exercise_id][0])
        ]
        if secondary_rows:
            await conn.execute(insert(ExerciseSecondaryMuscle).values(secondary_rows))
        instruction_rows = [
            {"exercise_id": exercise_id, "lang": lang, "text": body, "steps": list(steps)}
            for exercise_id in changed
            for lang, (body, steps) in children[exercise_id][1].items()
        ]
        await conn.execute(insert(ExerciseInstruction).values(instruction_rows))
    if diff["deprecated"]:
        await conn.execute(
            update(Exercise)
            .where(Exercise.id.in_(diff["deprecated"]))
            .values(deprecated_at=now, updated_at=now)
        )
    await conn.execute(delete(ExerciseAlternative))
    alternative_rows = [
        {"exercise_id": alt.exercise_id, "alt_id": alt.alt_id, "score": alt.score, "rank": alt.rank}
        for alternatives in catalog.alternatives.values()
        for alt in alternatives
    ]
    if alternative_rows:
        await conn.execute(insert(ExerciseAlternative).values(alternative_rows))
    await conn.execute(_SEARCH_VECTOR_SQL)


async def load_catalog(
    database_url: str,
    catalog: Catalog,
    manifest: Manifest,
    specs: IngestSpecs,
    *,
    media_verified: int,
    dry_run: bool = False,
    create_schema: bool = False,
    triggered_by: uuid.UUID | None = None,
) -> LoadResult:
    """``forja-ingest load``: upsert transaccional y registro en ``ingest_run``."""
    rows = {entry.exercise.id: exercise_row(entry, manifest, specs) for entry in catalog.entries}
    children = {entry.exercise.id: _children(entry) for entry in catalog.entries}
    engine = create_async_engine(database_url)
    run_id = uuid7()
    try:
        if create_schema:
            async with engine.begin() as conn:
                await ensure_schema(conn)
        async with engine.begin() as conn:
            await conn.execute(
                insert(IngestRun).values(
                    id=run_id,
                    commit=manifest.commit,
                    status="running",
                    dry_run=dry_run,
                    triggered_by=triggered_by,
                    started_at=datetime.now(UTC),
                    checksums_sha256=manifest.sha256(),
                    errors=[],
                    warnings=[],
                )
            )
        try:
            async with engine.begin() as conn:
                existing, secondary, instructions = await _existing_state(conn)
                diff = compute_diff(rows, children, existing, secondary, instructions)
                if not dry_run:
                    await _upsert_vocabulary(conn, specs)
                    await _write_catalog(conn, catalog, rows, children, diff)
                counts = {
                    "exercises_total": len(rows),
                    "added": len(diff["added"]),
                    "updated": len(diff["updated"]),
                    "deprecated": len(diff["deprecated"]),
                    "unchanged": len(diff["unchanged"]),
                    "media_verified": media_verified,
                }
                public_diff = {key: diff[key] for key in ("added", "updated", "deprecated")}
                await conn.execute(
                    update(IngestRun)
                    .where(IngestRun.id == run_id)
                    .values(
                        status="succeeded",
                        finished_at=datetime.now(UTC),
                        counts=counts,
                        diff=public_diff,
                        updated_at=datetime.now(UTC),
                    )
                )
        except Exception as exc:
            async with engine.begin() as conn:
                await conn.execute(
                    update(IngestRun)
                    .where(IngestRun.id == run_id)
                    .values(
                        status="failed",
                        finished_at=datetime.now(UTC),
                        errors=[f"{type(exc).__name__}: {exc}"[:2000]],
                        updated_at=datetime.now(UTC),
                    )
                )
            raise
    finally:
        await engine.dispose()
    return LoadResult(run_id=run_id, dry_run=dry_run, counts=counts, diff=public_diff)

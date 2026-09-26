"""Catálogo: DTOs de ejercicio, detalle con instrucciones, facetas, alternativas y favoritos."""

import uuid
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import Row
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import encode_cursor
from app.core.errors import ProblemError, not_found
from app.models.catalog import Equipment, Exercise
from app.models.user import FavoriteExercise, User
from app.repositories import catalog as repo
from app.schemas import api
from app.services import labels

ATTRIBUTION = api.MediaAttribution(text="© Gym visual", url="https://gymvisual.com/")


def summary_dto(ex: Exercise, *, is_favorite: bool) -> api.ExerciseSummary:
    return api.ExerciseSummary(
        id=ex.id,
        slug=ex.slug,
        name_es=ex.name_es,
        name_en=ex.display_name_en,
        variant_label_es=ex.variant_label_es,
        body_part=cast("Any", ex.body_part),
        equipment_code=cast("Any", ex.equipment_code),
        target_muscle=cast("Any", ex.target_muscle),
        movement_pattern=cast("Any", ex.movement_pattern),
        mechanic=cast("Any", ex.mechanic),
        role=cast("Any", ex.role),
        difficulty=ex.difficulty,
        is_staple=ex.is_staple,
        laterality=cast("Any", ex.laterality),
        load_type=cast("Any", ex.load_type),
        demo_sex=cast("Any", ex.demo_sex),
        variant_group=ex.variant_group,
        media=api.ExerciseMedia(
            thumb_url=f"/media/{ex.thumb_path}",
            gif_url=f"/media/{ex.gif_path}",
            width=180,
            height=180,
            attribution=ATTRIBUTION,
        ),
        is_favorite=is_favorite,
        deprecated=ex.deprecated_at is not None,
    )


def rows_to_summaries(rows: Sequence[Row[Any]]) -> list[api.ExerciseSummary]:
    return [summary_dto(row.Exercise, is_favorite=bool(row.is_favorite)) for row in rows]


async def summaries_for(
    db: AsyncSession, ids: Sequence[str], user_id: uuid.UUID
) -> list[api.ExerciseSummary]:
    """Resúmenes de los ids indicados (sin repetir, en orden de aparición; ids ausentes se omiten)."""
    unique = list(dict.fromkeys(ids))
    return rows_to_summaries(await repo.summaries_by_ids(db, unique, user_id))


async def list_page(
    db: AsyncSession,
    filters: repo.ExerciseFilters,
    user: User,
    *,
    cursor: dict[str, Any] | None,
    limit: int,
) -> api.ExercisePage:
    rows, next_cursor = await repo.list_exercises(db, filters, user.id, cursor=cursor, limit=limit)
    return api.ExercisePage(
        items=rows_to_summaries(rows),
        next_cursor=encode_cursor(next_cursor) if next_cursor else None,
    )


async def get_detail(
    db: AsyncSession, user: User, exercise_id: str, lang: str | None
) -> api.ExerciseDetail:
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise not_found("El ejercicio no existe.")
    favorite = await db.get(FavoriteExercise, (user.id, exercise_id))
    texts = await repo.instructions(db, exercise_id)
    if not texts:
        raise ProblemError(404, "not_found", "El ejercicio no tiene instrucciones cargadas.")
    chosen = next(
        (code for code in (lang, user.locale, "en") if code and code in texts), next(iter(texts))
    )
    instruction = texts[chosen]
    others = await repo.variants(db, exercise)
    base = summary_dto(exercise, is_favorite=favorite is not None)
    return api.ExerciseDetail(
        **base.model_dump(),
        secondary_muscles=cast("Any", await repo.secondary_muscles(db, exercise_id)),
        primary_group_muscle=cast("Any", exercise.primary_group_muscle),
        equipment_group=cast("Any", await _equipment_group(db, exercise.equipment_code)),
        instructions=api.ExerciseInstructions(
            lang=cast("Any", chosen), text=instruction.text, steps=list(instruction.steps)
        ),
        available_langs=cast("Any", sorted(texts)),
        variants=[
            api.ExerciseVariantRef(
                id=other.id,
                name_es=other.name_es,
                label_es=other.variant_label_es or labels.VARIANT_LABEL_BASE,
                kind=cast("Any", other.variant_kind or "version"),
                demo_sex=cast("Any", other.demo_sex),
            )
            for other in others
        ],
        source_commit=exercise.source_commit,
        enrichment_version=exercise.enrichment_version,
        deprecated_at=exercise.deprecated_at,
    )


async def _equipment_group(db: AsyncSession, code: str) -> str:

    equipment = await db.get(Equipment, code)
    return equipment.group if equipment else "other"


async def get_alternatives(
    db: AsyncSession, user: User, exercise_id: str, equipment: Sequence[str]
) -> api.ExerciseAlternativeList:
    if await db.get(Exercise, exercise_id) is None:
        raise not_found("El ejercicio no existe.")
    found = await repo.alternatives(db, exercise_id, equipment, user.id)
    return api.ExerciseAlternativeList(
        items=[
            api.ExerciseAlternative(
                exercise=summary_dto(row.Exercise, is_favorite=bool(row.is_favorite)),
                score=min(1.0, max(0.0, score)),
            )
            for row, score in found
        ]
    )


def _facet(
    counts: dict[str, int], names: dict[str, tuple[str, str]], order: Sequence[str] | None = None
) -> list[api.FacetValue]:
    keys = list(order) if order else sorted(names, key=lambda k: names[k][0].lower())
    values = [
        api.FacetValue(
            value=key, label_es=names[key][0], label_en=names[key][1], count=counts.get(key, 0)
        )
        for key in keys
        if key in names
    ]
    return values


async def get_facets(
    db: AsyncSession, user: User, filters: repo.ExerciseFilters
) -> api.CatalogFacets:
    total, counts = await repo.facet_counts(db, filters, user.id)
    muscles = await repo.muscle_names(db)
    equipment = await repo.equipment_names(db)
    return api.CatalogFacets(
        total=total,
        body_part=_facet(counts["body_part"], labels.BODY_PART),
        target=_facet(counts["target"], muscles),
        muscle=_facet(counts["muscle"], muscles),
        equipment=_facet(counts["equipment"], equipment),
        pattern=_facet(counts["pattern"], labels.PATTERN),
        mechanic=_facet(counts["mechanic"], labels.MECHANIC),
        difficulty=_facet(counts["difficulty"], labels.DIFFICULTY, order=("1", "2", "3")),
        role=_facet(counts["role"], labels.ROLE),
    )


async def set_favorite(db: AsyncSession, user: User, exercise_id: str, *, favorite: bool) -> None:
    if await db.get(Exercise, exercise_id) is None:
        raise not_found("El ejercicio no existe.")
    if favorite:
        await db.execute(
            insert(FavoriteExercise)
            .values(user_id=user.id, exercise_id=exercise_id)
            .on_conflict_do_nothing()
        )
    else:
        existing = await db.get(FavoriteExercise, (user.id, exercise_id))
        if existing:
            await db.delete(existing)
    await db.commit()

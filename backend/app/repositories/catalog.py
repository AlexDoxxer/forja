"""Consultas SQL del catálogo de ejercicios (listado, facetas, detalle, alternativas)."""

import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy import ColumnElement, Integer, Row, and_, exists, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    Equipment,
    Exercise,
    ExerciseAlternative,
    ExerciseInstruction,
    ExerciseSecondaryMuscle,
    Muscle,
)
from app.models.user import FavoriteExercise

TOKEN_SPLIT: Final = str.maketrans({c: " " for c in "&|!():*<>'\"\\-,.;:/"})


def fold(value: str) -> str:
    """Minúsculas y sin acentos (equivale a ``unaccent`` en el lado de la consulta)."""
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tsquery_text(q: str) -> str | None:
    """Consulta ``to_tsquery`` con prefijos: ``«sentad prensa»`` → ``sentad:* & prensa:*``."""
    tokens = [t for t in fold(q).translate(TOKEN_SPLIT).split() if t]
    return " & ".join(f"{t}:*" for t in tokens) if tokens else None


@dataclass
class ExerciseFilters:
    q: str | None = None
    body_part: Sequence[str] = ()
    target: Sequence[str] = ()
    muscle: Sequence[str] = ()
    equipment: Sequence[str] = ()
    pattern: Sequence[str] = ()
    mechanic: str | None = None
    difficulty: Sequence[int] = ()
    role: Sequence[str] = ()
    favorites: bool = False
    include_deprecated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def conditions(
    f: ExerciseFilters, user_id: uuid.UUID, *, skip: str | None = None
) -> list[ColumnElement[bool]]:
    """Condiciones WHERE: OR dentro de un filtro, AND entre filtros (``skip`` omite uno)."""
    found: list[ColumnElement[bool]] = []
    if not f.include_deprecated:
        found.append(Exercise.deprecated_at.is_(None))
    tsq = tsquery_text(f.q) if f.q else None
    if f.q and skip != "q":
        folded = fold(f.q)
        parts: list[ColumnElement[bool]] = [
            func.unaccent(Exercise.name_es).op("%")(folded),
            func.unaccent(Exercise.display_name_en).op("%")(folded),
        ]
        if tsq:
            parts.append(Exercise.search_vector.op("@@")(func.to_tsquery("simple", tsq)))
        found.append(or_(*parts))
    if f.body_part and skip != "body_part":
        found.append(Exercise.body_part.in_(f.body_part))
    if f.target and skip != "target":
        found.append(Exercise.target_muscle.in_(f.target))
    if f.muscle and skip != "muscle":
        found.append(
            or_(
                Exercise.target_muscle.in_(f.muscle),
                exists().where(
                    ExerciseSecondaryMuscle.exercise_id == Exercise.id,
                    ExerciseSecondaryMuscle.muscle_code.in_(f.muscle),
                ),
            )
        )
    if f.equipment and skip != "equipment":
        found.append(Exercise.equipment_code.in_(f.equipment))
    if f.pattern and skip != "pattern":
        found.append(Exercise.movement_pattern.in_(f.pattern))
    if f.mechanic and skip != "mechanic":
        found.append(Exercise.mechanic == f.mechanic)
    if f.difficulty and skip != "difficulty":
        found.append(Exercise.difficulty.in_(f.difficulty))
    if f.role and skip != "role":
        found.append(Exercise.role.in_(f.role))
    if f.favorites and skip != "favorites":
        found.append(
            exists().where(
                FavoriteExercise.exercise_id == Exercise.id, FavoriteExercise.user_id == user_id
            )
        )
    return found


def rank_expression(q: str) -> ColumnElement[float]:
    """Relevancia: ``ts_rank`` sobre el vector sin acentos + similitud de trigramas."""
    tsq = tsquery_text(q)
    folded = fold(q)
    similarity = func.greatest(
        func.similarity(func.unaccent(Exercise.name_es), folded),
        func.similarity(func.unaccent(Exercise.display_name_en), folded),
    )
    if tsq:
        return func.coalesce(
            func.ts_rank(Exercise.search_vector, func.to_tsquery("simple", tsq)), 0.0
        ) + similarity
    return similarity


async def list_exercises(
    db: AsyncSession,
    f: ExerciseFilters,
    user_id: uuid.UUID,
    *,
    cursor: dict[str, Any] | None,
    limit: int,
) -> tuple[list[Row[Any]], dict[str, Any] | None]:
    """Página de (Exercise, is_favorite, rank); devuelve también el cursor siguiente."""
    favorite = exists().where(
        FavoriteExercise.exercise_id == Exercise.id, FavoriteExercise.user_id == user_id
    )
    where = conditions(f, user_id)
    if f.q:
        rank = func.floor(rank_expression(f.q) * 10000).cast(Integer).label("rank")
        stmt = select(Exercise, favorite.label("is_favorite"), rank).where(*where)
        if cursor:
            r, n, i = int(cursor["r"]), str(cursor["n"]), str(cursor["i"])
            stmt = stmt.where(
                or_(
                    rank < r,
                    and_(rank == r, or_(Exercise.name_es > n, and_(Exercise.name_es == n, Exercise.id > i))),
                )
            )
        stmt = stmt.order_by(rank.desc(), Exercise.name_es, Exercise.id)
    else:
        stmt = select(Exercise, favorite.label("is_favorite"), literal(0).label("rank")).where(*where)
        if cursor:
            n, i = str(cursor["n"]), str(cursor["i"])
            stmt = stmt.where(
                or_(Exercise.name_es > n, and_(Exercise.name_es == n, Exercise.id > i))
            )
        stmt = stmt.order_by(Exercise.name_es, Exercise.id)
    rows = list((await db.execute(stmt.limit(limit + 1))).all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = {"r": int(last.rank), "n": last.Exercise.name_es, "i": last.Exercise.id}
    return rows, next_cursor


async def facet_counts(
    db: AsyncSession, f: ExerciseFilters, user_id: uuid.UUID
) -> tuple[int, dict[str, dict[str, int]]]:
    """Total y recuentos por valor de cada faceta (cada faceta ignora su propio filtro)."""
    total = (
        await db.execute(select(func.count()).select_from(Exercise).where(*conditions(f, user_id)))
    ).scalar_one()
    result: dict[str, dict[str, int]] = {}
    simple = {
        "body_part": Exercise.body_part,
        "target": Exercise.target_muscle,
        "equipment": Exercise.equipment_code,
        "pattern": Exercise.movement_pattern,
        "mechanic": Exercise.mechanic,
        "difficulty": Exercise.difficulty,
        "role": Exercise.role,
    }
    for name, column in simple.items():
        rows = await db.execute(
            select(column, func.count()).where(*conditions(f, user_id, skip=name)).group_by(column)
        )
        result[name] = {str(value): count for value, count in rows}
    matching = select(Exercise.id).where(*conditions(f, user_id, skip="muscle"))
    both = union_all(
        select(Exercise.id.label("id"), Exercise.target_muscle.label("muscle")).where(
            Exercise.id.in_(matching)
        ),
        select(
            ExerciseSecondaryMuscle.exercise_id.label("id"),
            ExerciseSecondaryMuscle.muscle_code.label("muscle"),
        ).where(ExerciseSecondaryMuscle.exercise_id.in_(matching)),
    ).subquery()
    rows = await db.execute(
        select(both.c.muscle, func.count(func.distinct(both.c.id))).group_by(both.c.muscle)
    )
    result["muscle"] = {value: count for value, count in rows}
    return total, result


async def muscle_names(db: AsyncSession) -> dict[str, tuple[str, str]]:
    rows = await db.execute(select(Muscle.code, Muscle.name_es, Muscle.name_en))
    return {code: (es, en) for code, es, en in rows}


async def equipment_names(db: AsyncSession) -> dict[str, tuple[str, str]]:
    rows = await db.execute(select(Equipment.code, Equipment.name_es, Equipment.name_en))
    return {code: (es, en) for code, es, en in rows}


async def summaries_by_ids(
    db: AsyncSession, ids: Sequence[str], user_id: uuid.UUID
) -> list[Row[Any]]:
    """Filas (Exercise, is_favorite) de los ids pedidos, en el orden dado."""
    if not ids:
        return []
    favorite = exists().where(
        FavoriteExercise.exercise_id == Exercise.id, FavoriteExercise.user_id == user_id
    )
    rows = (
        await db.execute(select(Exercise, favorite.label("is_favorite")).where(Exercise.id.in_(ids)))
    ).all()
    order = {exercise_id: position for position, exercise_id in enumerate(ids)}
    return sorted(rows, key=lambda row: order[row.Exercise.id])


async def secondary_muscles(db: AsyncSession, exercise_id: str) -> list[str]:
    rows = await db.execute(
        select(ExerciseSecondaryMuscle.muscle_code)
        .where(ExerciseSecondaryMuscle.exercise_id == exercise_id)
        .order_by(ExerciseSecondaryMuscle.position)
    )
    return [code for (code,) in rows]


async def instructions(db: AsyncSession, exercise_id: str) -> dict[str, ExerciseInstruction]:
    rows = await db.execute(
        select(ExerciseInstruction).where(ExerciseInstruction.exercise_id == exercise_id)
    )
    return {row.lang: row for row in rows.scalars()}


async def variants(db: AsyncSession, exercise: Exercise) -> list[Exercise]:
    rows = await db.execute(
        select(Exercise)
        .where(Exercise.variant_group == exercise.variant_group, Exercise.id != exercise.id)
        .order_by(Exercise.id)
    )
    return list(rows.scalars())


async def alternatives(
    db: AsyncSession, exercise_id: str, equipment: Sequence[str], user_id: uuid.UUID
) -> list[tuple[Row[Any], float]]:
    favorite = exists().where(
        FavoriteExercise.exercise_id == Exercise.id, FavoriteExercise.user_id == user_id
    )
    stmt = (
        select(Exercise, favorite.label("is_favorite"), ExerciseAlternative.score)
        .join(ExerciseAlternative, ExerciseAlternative.alt_id == Exercise.id)
        .where(ExerciseAlternative.exercise_id == exercise_id, Exercise.deprecated_at.is_(None))
        .order_by(ExerciseAlternative.rank)
    )
    if equipment:
        stmt = stmt.where(Exercise.equipment_code.in_(equipment))
    return [(row, float(row.score)) for row in (await db.execute(stmt)).all()]

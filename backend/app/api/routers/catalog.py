"""Biblioteca de ejercicios: listado, detalle, alternativas, facetas y favoritos."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, Path, Query, Response, status
from forja_engine.models import (
    BodyPart,
    EquipmentCode,
    ExerciseRole,
    Mechanic,
    MovementPattern,
    MuscleCode,
)
from pydantic import Field

from app.api.common import decode_cursor, errors, etag_json
from app.api.deps import CurrentUserDep, Db
from app.repositories.catalog import ExerciseFilters
from app.schemas import api
from app.services import catalog as service

router = APIRouter(tags=["catalog"])

ExerciseIdPath = Annotated[str, Path(pattern=r"^[0-9]{4}$")]
IfNoneMatch = Annotated[str | None, Header(alias="If-None-Match")]
NOT_MODIFIED: dict[int | str, dict[str, Any]] = {
    304: {"description": "Sin cambios desde el ETag indicado."}
}


@router.get(
    "/exercises",
    operation_id="listExercises",
    response_model=api.ExercisePage,
    responses={**NOT_MODIFIED, **errors(401, 422)},
)
async def list_exercises(
    user: CurrentUserDep,
    db: Db,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    body_part: Annotated[list[BodyPart] | None, Query()] = None,
    target: Annotated[list[MuscleCode] | None, Query()] = None,
    muscle: Annotated[list[MuscleCode] | None, Query()] = None,
    equipment: Annotated[list[EquipmentCode] | None, Query()] = None,
    pattern: Annotated[list[MovementPattern] | None, Query()] = None,
    mechanic: Mechanic | None = None,
    difficulty: Annotated[list[Annotated[int, Field(ge=1, le=3)]] | None, Query()] = None,
    role: Annotated[list[ExerciseRole] | None, Query()] = None,
    favorites: bool = False,
    include_deprecated: bool = False,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    if_none_match: IfNoneMatch = None,
) -> Response:
    filters = ExerciseFilters(
        q=q.strip() if q else None,
        body_part=[str(v) for v in body_part or ()],
        target=[str(v) for v in target or ()],
        muscle=[str(v) for v in muscle or ()],
        equipment=[str(v) for v in equipment or ()],
        pattern=[str(v) for v in pattern or ()],
        mechanic=str(mechanic) if mechanic else None,
        difficulty=list(difficulty or ()),
        role=[str(v) for v in role or ()],
        favorites=favorites,
        include_deprecated=include_deprecated,
    )
    page = await service.list_page(db, filters, user, cursor=decode_cursor(cursor), limit=limit)
    return etag_json(if_none_match, page)


@router.get(
    "/catalog/facets",
    operation_id="getCatalogFacets",
    response_model=api.CatalogFacets,
    responses={**NOT_MODIFIED, **errors(401, 422)},
)
async def get_catalog_facets(
    user: CurrentUserDep,
    db: Db,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    body_part: Annotated[list[BodyPart] | None, Query()] = None,
    muscle: Annotated[list[MuscleCode] | None, Query()] = None,
    equipment: Annotated[list[EquipmentCode] | None, Query()] = None,
    pattern: Annotated[list[MovementPattern] | None, Query()] = None,
    favorites: bool = False,
    if_none_match: IfNoneMatch = None,
) -> Response:
    filters = ExerciseFilters(
        q=q.strip() if q else None,
        body_part=[str(v) for v in body_part or ()],
        muscle=[str(v) for v in muscle or ()],
        equipment=[str(v) for v in equipment or ()],
        pattern=[str(v) for v in pattern or ()],
        favorites=favorites,
    )
    return etag_json(if_none_match, await service.get_facets(db, user, filters))


@router.get(
    "/exercises/{exercise_id}",
    operation_id="getExercise",
    response_model=api.ExerciseDetail,
    responses={**NOT_MODIFIED, **errors(401, 404)},
)
async def get_exercise(
    exercise_id: ExerciseIdPath,
    user: CurrentUserDep,
    db: Db,
    lang: Annotated[str | None, Query(pattern=r"^(en|es|it|tr|ru|zh|hi|pl|ko|fr)$")] = None,
    if_none_match: IfNoneMatch = None,
) -> Response:
    return etag_json(if_none_match, await service.get_detail(db, user, exercise_id, lang))


@router.get(
    "/exercises/{exercise_id}/alternatives",
    operation_id="listExerciseAlternatives",
    response_model=api.ExerciseAlternativeList,
    responses={**NOT_MODIFIED, **errors(401, 404)},
)
async def list_exercise_alternatives(
    exercise_id: ExerciseIdPath,
    user: CurrentUserDep,
    db: Db,
    equipment: Annotated[list[EquipmentCode] | None, Query()] = None,
    if_none_match: IfNoneMatch = None,
) -> Response:
    result = await service.get_alternatives(
        db, user, exercise_id, [str(v) for v in equipment or ()]
    )
    return etag_json(if_none_match, result)


@router.put(
    "/exercises/{exercise_id}/favorite",
    operation_id="addFavoriteExercise",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def add_favorite(exercise_id: ExerciseIdPath, user: CurrentUserDep, db: Db) -> None:
    await service.set_favorite(db, user, exercise_id, favorite=True)


@router.delete(
    "/exercises/{exercise_id}/favorite",
    operation_id="removeFavoriteExercise",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def remove_favorite(exercise_id: ExerciseIdPath, user: CurrentUserDep, db: Db) -> None:
    await service.set_favorite(db, user, exercise_id, favorite=False)

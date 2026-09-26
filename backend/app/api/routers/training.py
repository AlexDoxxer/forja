"""Sesiones, series, sincronización offline, progreso y récords."""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Path, Query, Response, status
from fastapi.encoders import jsonable_encoder

from app.api.common import decode_cursor, errors
from app.api.deps import Catalog, CurrentUserDep, Db, EngineTables
from app.schemas import api
from app.services import idempotency, stats, training

router = APIRouter(tags=["sessions", "stats"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=100)]
IdemKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]
ExerciseIdPath = Annotated[str, Path(pattern=r"^[0-9]{4}$")]


def _replayed(response: Response, *, replayed: bool) -> None:
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"


@router.post(
    "/sessions",
    operation_id="startWorkoutSession",
    status_code=status.HTTP_201_CREATED,
    response_model=api.WorkoutSession,
    responses=errors(401, 403, 404, 409, 422),
)
async def start_workout_session(
    body: api.WorkoutSessionCreate,
    response: Response,
    user: CurrentUserDep,
    db: Db,
    idempotency_key: IdemKey,
) -> dict[str, object]:
    async def handler() -> tuple[int, dict[str, object]]:
        created = await training.start_session(db, user, body)
        return 201, jsonable_encoder(created)

    code, payload, replayed = await idempotency.run_idempotent(
        db, user, f"session:{idempotency_key}", body.model_dump(mode="json"), handler
    )
    response.status_code = code
    _replayed(response, replayed=replayed)
    return payload


@router.get(
    "/sessions",
    operation_id="listWorkoutSessions",
    response_model=api.WorkoutSessionPage,
    responses=errors(401, 422),
)
async def list_workout_sessions(
    user: CurrentUserDep,
    db: Db,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    status_: Annotated[
        Literal["in_progress", "completed", "abandoned"] | None, Query(alias="status")
    ] = None,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> api.WorkoutSessionPage:
    return await training.list_sessions(
        db,
        user,
        from_date=from_,
        to_date=to,
        status=status_,
        cursor=decode_cursor(cursor),
        limit=limit,
    )


@router.get(
    "/sessions/next",
    operation_id="getNextSession",
    response_model=api.NextSession,
    responses=errors(401),
)
async def get_next_session(
    user: CurrentUserDep, db: Db, catalog: Catalog, tables: EngineTables
) -> api.NextSession:
    snapshot = await catalog.snapshot()
    return await stats.next_session(db, user, snapshot.by_id, snapshot.cards, tables)


@router.get(
    "/sessions/{session_id}",
    operation_id="getWorkoutSession",
    response_model=api.WorkoutSession,
    responses=errors(401, 404),
)
async def get_workout_session(
    session_id: uuid.UUID, user: CurrentUserDep, db: Db
) -> api.WorkoutSession:
    return await training.session_dto(db, await training.get_owned_session(db, user, session_id))


@router.patch(
    "/sessions/{session_id}",
    operation_id="updateWorkoutSession",
    response_model=api.WorkoutSession,
    responses=errors(401, 403, 404, 409, 422),
)
async def update_workout_session(
    session_id: uuid.UUID, body: api.WorkoutSessionUpdate, user: CurrentUserDep, db: Db
) -> api.WorkoutSession:
    return await training.update_session(db, user, session_id, body)


@router.post(
    "/sessions/{session_id}/sets",
    operation_id="logSet",
    status_code=status.HTTP_201_CREATED,
    response_model=api.SetLog,
    responses=errors(401, 403, 404, 409, 422),
)
async def log_set(
    session_id: uuid.UUID,
    body: api.SetLogCreate,
    response: Response,
    user: CurrentUserDep,
    db: Db,
    idempotency_key: IdemKey,
) -> dict[str, object]:
    async def handler() -> tuple[int, dict[str, object]]:
        return 201, jsonable_encoder(await training.log_set(db, user, session_id, body))

    code, payload, replayed = await idempotency.run_idempotent(
        db,
        user,
        f"set:{session_id}:{idempotency_key}",
        body.model_dump(mode="json"),
        handler,
    )
    response.status_code = code
    _replayed(response, replayed=replayed)
    return payload


@router.patch(
    "/sessions/{session_id}/sets/{set_id}",
    operation_id="updateSet",
    response_model=api.SetLog,
    responses=errors(401, 403, 404, 422),
)
async def update_set(
    session_id: uuid.UUID, set_id: uuid.UUID, body: api.SetLogUpdate, user: CurrentUserDep, db: Db
) -> api.SetLog:
    return await training.update_set(db, user, session_id, set_id, body)


@router.delete(
    "/sessions/{session_id}/sets/{set_id}",
    operation_id="deleteSet",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def delete_set(
    session_id: uuid.UUID, set_id: uuid.UUID, user: CurrentUserDep, db: Db
) -> None:
    await training.delete_set(db, user, session_id, set_id)


@router.post(
    "/sessions/{session_id}/finish",
    operation_id="finishWorkoutSession",
    response_model=api.SessionSummary,
    responses=errors(401, 403, 404, 409, 422),
)
async def finish_workout_session(
    session_id: uuid.UUID, body: api.SessionFinishRequest, user: CurrentUserDep, db: Db
) -> api.SessionSummary:
    return await training.finish_session(db, user, session_id, body)


@router.post(
    "/sync",
    operation_id="syncOfflineBatch",
    response_model=api.SyncResponse,
    response_model_exclude_unset=True,
    responses=errors(401, 403, 413, 422),
)
async def sync_offline_batch(
    body: api.SyncRequest, user: CurrentUserDep, db: Db
) -> api.SyncResponse:
    return await training.sync_batch(db, user, body)


@router.get(
    "/stats/overview",
    operation_id="getStatsOverview",
    response_model=api.StatsOverview,
    responses=errors(401),
)
async def get_stats_overview(user: CurrentUserDep, db: Db) -> api.StatsOverview:
    return await stats.overview(db, user)


@router.get(
    "/stats/volume",
    operation_id="getVolumeStats",
    response_model=api.VolumeStats,
    responses=errors(401, 422),
)
async def get_volume_stats(
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    weeks: Annotated[int, Query(ge=1, le=52)] = 8,
) -> api.VolumeStats:
    return await stats.volume(db, user, (await catalog.snapshot()).by_id, weeks)


@router.get(
    "/stats/exercise/{exercise_id}",
    operation_id="getExerciseStats",
    response_model=api.ExerciseStats,
    responses=errors(401, 404, 422),
)
async def get_exercise_stats(
    exercise_id: ExerciseIdPath,
    user: CurrentUserDep,
    db: Db,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
) -> api.ExerciseStats:
    return await stats.exercise_stats(db, user, exercise_id, from_, to)


@router.get(
    "/records",
    operation_id="listPersonalRecords",
    response_model=api.PersonalRecordPage,
    responses=errors(401, 422),
)
async def list_personal_records(
    user: CurrentUserDep,
    db: Db,
    exercise_id: Annotated[str | None, Query(pattern=r"^[0-9]{4}$")] = None,
    kind: Literal["e1rm", "heaviest_set", "volume"] | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> api.PersonalRecordPage:
    return await training.list_records(
        db, user, exercise_id=exercise_id, kind=kind, cursor=decode_cursor(cursor), limit=limit
    )

"""Perfil, PAR-Q y métricas corporales."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.common import decode_cursor, errors
from app.api.deps import CurrentUserDep, Db
from app.schemas import api
from app.services import profile as service

router = APIRouter(tags=["profile"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/profile", operation_id="getProfile", response_model=api.Profile, responses=errors(401))
async def get_profile(user: CurrentUserDep, db: Db) -> api.Profile:
    return await service.get_profile(db, user)


@router.put(
    "/profile",
    operation_id="updateProfile",
    response_model=api.Profile,
    responses=errors(401, 403, 422),
)
async def update_profile(body: api.ProfileUpdate, user: CurrentUserDep, db: Db) -> api.Profile:
    return await service.update_profile(db, user, body)


@router.put(
    "/profile/parq",
    operation_id="submitParq",
    response_model=api.ParqResult,
    responses=errors(401, 403, 422),
)
async def submit_parq(body: api.ParqSubmission, user: CurrentUserDep, db: Db) -> api.ParqResult:
    return await service.submit_parq(db, user, body)


@router.get(
    "/body-metrics",
    operation_id="listBodyMetrics",
    response_model=api.BodyMetricPage,
    responses=errors(401, 422),
)
async def list_body_metrics(
    user: CurrentUserDep,
    db: Db,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> api.BodyMetricPage:
    return await service.list_metrics(
        db, user, from_date=from_, to_date=to, cursor=decode_cursor(cursor), limit=limit
    )


@router.post(
    "/body-metrics",
    operation_id="upsertBodyMetric",
    response_model=api.BodyMetric,
    responses={201: {"model": api.BodyMetric, "description": "Creada"}, **errors(401, 403, 422)},
)
async def upsert_body_metric(
    body: api.BodyMetricCreate, user: CurrentUserDep, db: Db, response: Response
) -> api.BodyMetric:
    metric, created = await service.upsert_metric(db, user, body)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return metric


@router.delete(
    "/body-metrics/{metric_id}",
    operation_id="deleteBodyMetric",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def delete_body_metric(metric_id: uuid.UUID, user: CurrentUserDep, db: Db) -> None:
    await service.delete_metric(db, user, metric_id)

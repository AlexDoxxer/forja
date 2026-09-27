"""Datos de cuenta (``/me``) y administración (``/admin``)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response, status

from app.api.common import decode_cursor, errors
from app.api.deps import (
    AdminUser,
    AppSettings,
    Catalog,
    CurrentUserDep,
    Db,
    get_rate_limiter,
)
from app.schemas import api
from app.security.tokens import clear_session_cookie
from app.services import account
from app.services import admin as service

router = APIRouter(tags=["data", "admin"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get(
    "/me/export",
    operation_id="exportAccountData",
    response_model=api.UserExport,
    responses=errors(401),
)
async def export_account_data(user: CurrentUserDep, db: Db, response: Response) -> api.UserExport:
    # S-09 (docs/reviews/f3-security.md): fuerza la descarga como fichero en vez de abrirse
    # inline en el navegador (riesgo bajo, pero un export de "mis datos" no debería quedar
    # pegado en el historial de un navegador compartido).
    response.headers["Content-Disposition"] = 'attachment; filename="forja-export.json"'
    return await account.export_account(db, user)


@router.post(
    "/me/import",
    operation_id="importAccountData",
    response_model=api.ImportResult,
    responses=errors(401, 403, 413, 422),
)
async def import_account_data(
    body: api.UserExport, user: CurrentUserDep, db: Db, catalog: Catalog
) -> api.ImportResult:
    known = set((await catalog.snapshot()).by_id)
    return await account.import_account(db, user, body, known)


@router.delete(
    "/me",
    operation_id="deleteAccount",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 409, 422, 429),
)
async def delete_account(
    body: api.AccountDeleteRequest,
    request: Request,
    response: Response,
    user: CurrentUserDep,
    db: Db,
) -> None:
    get_rate_limiter(request).check("delete_account", str(user.id))
    await account.delete_account(db, user, body)
    clear_session_cookie(response)


@router.get(
    "/admin/settings",
    operation_id="getAdminSettings",
    response_model=api.AdminSettings,
    responses=errors(401, 403),
)
async def get_admin_settings(_admin: AdminUser, db: Db, settings: AppSettings) -> api.AdminSettings:
    return await service.get_admin_settings(db, settings)


@router.put(
    "/admin/settings",
    operation_id="updateAdminSettings",
    response_model=api.AdminSettings,
    responses=errors(401, 403, 422),
)
async def update_admin_settings(
    body: api.AdminSettingsUpdate, admin: AdminUser, db: Db, settings: AppSettings
) -> api.AdminSettings:
    return await service.update_admin_settings(db, settings, admin, body)


@router.get(
    "/admin/users",
    operation_id="listUsers",
    response_model=api.AdminUserPage,
    responses=errors(401, 403),
)
async def list_users(
    _admin: AdminUser,
    db: Db,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> api.AdminUserPage:
    return await service.list_users(db, q=q, cursor=decode_cursor(cursor), limit=limit)


@router.patch(
    "/admin/users/{user_id}",
    operation_id="updateUser",
    response_model=api.AdminUser,
    responses=errors(401, 403, 404, 409, 422),
)
async def update_user(
    user_id: uuid.UUID, body: api.AdminUserUpdate, admin: AdminUser, db: Db
) -> api.AdminUser:
    return await service.update_user(db, admin, user_id, body)


@router.post(
    "/admin/ingest",
    operation_id="startIngest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=api.IngestRun,
    responses=errors(401, 403, 409, 422),
)
async def start_ingest(
    body: api.IngestRequest,
    request: Request,
    tasks: BackgroundTasks,
    admin: AdminUser,
    db: Db,
    settings: AppSettings,
    catalog: Catalog,
) -> api.IngestRun:
    run = await service.start_ingest(db, settings, admin, body)
    tasks.add_task(
        service.run_ingest_task, request.app.state.sessionmaker, settings, catalog, run.id
    )
    return service.run_dto(run)


@router.get(
    "/admin/ingest/runs",
    operation_id="listIngestRuns",
    response_model=api.IngestRunPage,
    responses=errors(401, 403),
)
async def list_ingest_runs(
    _admin: AdminUser, db: Db, cursor: Cursor = None, limit: Limit = 20
) -> api.IngestRunPage:
    return await service.list_runs(db, cursor=decode_cursor(cursor), limit=limit)

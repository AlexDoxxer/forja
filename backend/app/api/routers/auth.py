"""Autenticación (ADR 0003, ADR 0009)."""

import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.common import errors
from app.api.deps import (
    AppSettings,
    CurrentAuth,
    Db,
    find_valid_session,
    get_rate_limiter,
    rate_limit_key,
)
from app.core.errors import ProblemError
from app.schemas import api
from app.security.tokens import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_csrf_cookie,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf", operation_id="issueCsrfToken", status_code=status.HTTP_204_NO_CONTENT)
async def issue_csrf(response: Response) -> None:
    set_csrf_cookie(response)


@router.post(
    "/register",
    operation_id="register",
    status_code=status.HTTP_201_CREATED,
    response_model=api.CurrentUser,
    responses=errors(403, 409, 422, 429),
)
async def register(
    body: api.RegisterRequest,
    request: Request,
    response: Response,
    db: Db,
    settings: AppSettings,
) -> api.CurrentUser:
    get_rate_limiter(request).check("register", rate_limit_key(request, settings))
    user = await auth_service.register(db, settings, request, response, body)
    return await auth_service.current_user_dto(db, settings, user)


@router.post(
    "/login",
    operation_id="login",
    response_model=api.CurrentUser,
    responses=errors(401, 422, 429),
)
async def login(
    body: api.LoginRequest,
    request: Request,
    response: Response,
    db: Db,
    settings: AppSettings,
) -> api.CurrentUser:
    limiter = get_rate_limiter(request)
    limiter.check("login", rate_limit_key(request, settings))
    limiter.check("login", f"email:{body.email.lower()}")
    user = await auth_service.login(db, settings, request, response, body)
    return await auth_service.current_user_dto(db, settings, user)


@router.post(
    "/logout",
    operation_id="logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403),
)
async def logout(auth: CurrentAuth, db: Db, response: Response) -> None:
    await auth_service.revoke_session(db, auth.session)
    clear_session_cookie(response)


@router.get(
    "/me", operation_id="getCurrentUser", response_model=api.CurrentUser, responses=errors(401)
)
async def get_current_user(auth: CurrentAuth, db: Db, settings: AppSettings) -> api.CurrentUser:
    return await auth_service.current_user_dto(db, settings, auth.user)


@router.post(
    "/password",
    operation_id="changePassword",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 422, 429),
)
async def change_password(
    body: api.PasswordChangeRequest,
    request: Request,
    response: Response,
    auth: CurrentAuth,
    db: Db,
    settings: AppSettings,
) -> None:
    get_rate_limiter(request).check("password", str(auth.user.id))
    await auth_service.change_password(
        db, settings, request, response, auth.user, auth.session, body
    )


@router.get(
    "/check",
    operation_id="checkSession",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"description": "Sin sesión válida (sin cuerpo)."}},
)
async def check_session(request: Request, db: Db) -> Response:
    """Para ``auth_request`` de nginx: 204/401 sin cuerpo; no renueva la sesión."""
    auth = await find_valid_session(db, request.cookies.get(SESSION_COOKIE))
    return Response(status_code=204 if auth else 401)


@router.get(
    "/sessions",
    operation_id="listAuthSessions",
    response_model=api.AuthSessionList,
    responses=errors(401),
)
async def list_auth_sessions(auth: CurrentAuth, db: Db) -> api.AuthSessionList:
    return await auth_service.list_sessions(db, auth.user, auth.session.id)


@router.delete(
    "/sessions/{auth_session_id}",
    operation_id="revokeAuthSession",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def revoke_auth_session(auth_session_id: uuid.UUID, auth: CurrentAuth, db: Db) -> None:
    await auth_service.revoke_owned_session(db, auth.user, auth_session_id)


_ = ProblemError

"""Registro, inicio y cierre de sesión, contraseñas y sesiones activas (ADR 0003)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ProblemError, forbidden, not_found, unprocessable
from app.models.user import AuthSession, Profile, User
from app.schemas import api
from app.security import passwords
from app.security.tokens import (
    client_ip,
    hash_ip,
    hash_token,
    new_token,
    set_csrf_cookie,
    set_session_cookie,
)
from app.services import settings as app_settings
from app.services.audit import audit

DEFAULT_EQUIPMENT = {"preset": "full_gym", "items": []}
DEFAULT_LIMITATIONS: dict[str, Any] = {"avoid_muscles": [], "avoid_patterns": [], "notes": None}
DEFAULT_PREFERENCES = {"theme": "system", "sounds": True, "vibration": True, "default_rest_s": None}


def default_profile(user_id: uuid.UUID) -> Profile:
    return Profile(
        user_id=user_id,
        equipment_profile=dict(DEFAULT_EQUIPMENT),
        limitations=dict(DEFAULT_LIMITATIONS),
        preferences=dict(DEFAULT_PREFERENCES),
    )


def onboarding_completed(profile: Profile) -> bool:
    return (
        profile.birth_date is not None
        and profile.height_cm is not None
        and profile.parq_completed_at is not None
    )


async def current_user_dto(db: AsyncSession, settings: Settings, user: User) -> api.CurrentUser:
    profile = await db.get(Profile, user.id)
    diet_on = await app_settings.diet_feature_enabled(db, settings)
    return api.CurrentUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,  # type: ignore[arg-type]  # validado por CHECK en BD
        locale=user.locale,  # type: ignore[arg-type]
        units=user.units,  # type: ignore[arg-type]
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        onboarding_completed=onboarding_completed(profile) if profile else False,
        diet_available=bool(diet_on and profile and profile.diet_enabled),
    )


async def start_session(
    db: AsyncSession, settings: Settings, request: Request, response: Response, user: User
) -> AuthSession:
    """Crea una sesión nueva (rotación), fija ambas cookies y devuelve la fila."""
    now = datetime.now(UTC)
    ttl = timedelta(days=settings.session_ttl_days)
    token = new_token()
    agent = request.headers.get("user-agent")
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=now + ttl,
        last_seen_at=now,
        user_agent=agent[:256] if agent else None,
        ip_hash=hash_ip(
            client_ip(request, settings.trusted_proxy_count),
            settings.secret_key.get_secret_value(),
        ),
    )
    db.add(session)
    await db.flush()
    set_session_cookie(response, token, int(ttl.total_seconds()))
    set_csrf_cookie(response)
    return session


async def register(
    db: AsyncSession,
    settings: Settings,
    request: Request,
    response: Response,
    body: api.RegisterRequest,
) -> User:
    if not await app_settings.registration_open(db, settings):
        raise forbidden("registration_closed", "El registro está cerrado.")
    if passwords.is_weak_password(body.password, body.email):
        raise unprocessable(
            "validation_error",
            "La contraseña es demasiado común o fácil de adivinar.",
            errors=[
                {
                    "loc": ["body", "password"],
                    "msg": "Contraseña demasiado común",
                    "type": "weak_password",
                }
            ],
        )
    first = (await db.execute(select(func.count()).select_from(User))).scalar_one() == 0
    user = User(
        email=body.email,
        password_hash=await passwords.hash_password_async(body.password),
        display_name=body.display_name,
        role="admin" if first else "user",
        locale=body.locale or settings.default_locale,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ProblemError(409, "email_taken", "Ya existe una cuenta con ese correo.") from exc
    db.add(default_profile(user.id))
    await start_session(db, settings, request, response, user)
    await audit(db, "auth.register", actor=user.id, target=str(user.id))
    await db.commit()
    return user


async def login(
    db: AsyncSession,
    settings: Settings,
    request: Request,
    response: Response,
    body: api.LoginRequest,
) -> User:
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    stored = user.password_hash if user else passwords.decoy_hash()
    valid = await passwords.verify_password_async(stored, body.password)
    ip = hash_ip(
        client_ip(request, settings.trusted_proxy_count), settings.secret_key.get_secret_value()
    )
    if user is None or not valid or not user.is_active:
        await audit(
            db,
            "auth.login.failed",
            actor=user.id if user else None,
            ip_hash=ip,
        )
        await db.commit()
        raise ProblemError(401, "invalid_credentials", "Correo o contraseña incorrectos.")
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = await passwords.hash_password_async(body.password)
    user.last_login_at = datetime.now(UTC)
    await start_session(db, settings, request, response, user)
    await db.commit()
    return user


async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
    session.revoked_at = datetime.now(UTC)
    await db.commit()


async def change_password(
    db: AsyncSession,
    settings: Settings,
    request: Request,
    response: Response,
    auth_user: User,
    current_session: AuthSession,
    body: api.PasswordChangeRequest,
) -> None:
    if not await passwords.verify_password_async(auth_user.password_hash, body.current_password):
        raise unprocessable(
            "validation_error",
            "La contraseña actual no es correcta.",
            errors=[
                {
                    "loc": ["body", "current_password"],
                    "msg": "Contraseña incorrecta",
                    "type": "invalid_password",
                }
            ],
        )
    if passwords.is_weak_password(body.new_password, auth_user.email):
        raise unprocessable(
            "validation_error",
            "La contraseña nueva es demasiado común o fácil de adivinar.",
            errors=[
                {
                    "loc": ["body", "new_password"],
                    "msg": "Contraseña demasiado común",
                    "type": "weak_password",
                }
            ],
        )
    auth_user.password_hash = await passwords.hash_password_async(body.new_password)
    now = datetime.now(UTC)
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == auth_user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await start_session(db, settings, request, response, auth_user)
    await audit(db, "auth.password.change", actor=auth_user.id)
    await db.commit()
    _ = current_session


async def list_sessions(db: AsyncSession, user: User, current_id: uuid.UUID) -> api.AuthSessionList:
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(AuthSession)
            .where(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.last_seen_at.desc())
        )
    ).scalars()
    return api.AuthSessionList(
        items=[
            api.AuthSession(
                id=s.id,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                expires_at=s.expires_at,
                user_agent=s.user_agent,
                current=s.id == current_id,
            )
            for s in rows
        ]
    )


async def revoke_owned_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> None:
    target = await db.get(AuthSession, session_id)
    if target is None or target.user_id != user.id or target.revoked_at is not None:
        raise not_found("La sesión no existe.")
    target.revoked_at = datetime.now(UTC)
    await db.commit()

"""Dependencias de FastAPI: base de datos, autenticación y autorización."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final

from fastapi import Depends, Request, Response
from forja_engine import Tables
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import forbidden, unauthenticated
from app.db.session import get_db
from app.models.user import AuthSession, User
from app.security.ratelimit import RateLimiter
from app.security.tokens import (
    SESSION_COOKIE,
    client_ip,
    hash_ip,
    hash_token,
    set_session_cookie,
)
from app.services.catalog_cache import CatalogCache

# Como mucho una escritura de renovación por minuto y sesión (ADR 0003).
RENEW_INTERVAL: Final = timedelta(minutes=1)

Db = Annotated[AsyncSession, Depends(get_db)]


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_rate_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


def rate_limit_key(request: Request, settings: Settings) -> str:
    ip = client_ip(request, settings.trusted_proxy_count)
    return hash_ip(ip, settings.secret_key.get_secret_value()) or "unknown"


@dataclass(frozen=True)
class Auth:
    user: User
    session: AuthSession


async def find_valid_session(db: AsyncSession, token: str | None) -> Auth | None:
    """Sesión no revocada ni caducada de usuario activo, por índice único de ``token_hash``."""
    if not token:
        return None
    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == hash_token(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.is_active.is_(True),
            )
        )
    ).first()
    return Auth(user=row[1], session=row[0]) if row else None


async def current_auth(request: Request, response: Response, db: Db, settings: AppSettings) -> Auth:
    """Usuario autenticado; renueva de forma deslizante la sesión y la cookie."""
    auth = await find_valid_session(db, request.cookies.get(SESSION_COOKIE))
    if auth is None:
        raise unauthenticated()
    now = datetime.now(UTC)
    if now - auth.session.last_seen_at >= RENEW_INTERVAL:
        ttl = timedelta(days=settings.session_ttl_days)
        auth.session.last_seen_at = now
        auth.session.expires_at = now + ttl
        await db.commit()
        token = request.cookies.get(SESSION_COOKIE, "")
        set_session_cookie(response, token, int(ttl.total_seconds()))
    return auth


CurrentAuth = Annotated[Auth, Depends(current_auth)]


async def current_user(auth: CurrentAuth) -> User:
    return auth.user


CurrentUserDep = Annotated[User, Depends(current_user)]


async def require_admin(auth: CurrentAuth) -> User:
    if auth.user.role != "admin":
        raise forbidden("admin_required", "Se necesita el rol de administrador.")
    return auth.user


AdminUser = Annotated[User, Depends(require_admin)]


def get_catalog(request: Request) -> CatalogCache:
    cache: CatalogCache = request.app.state.catalog
    return cache


def get_tables(request: Request) -> Tables:
    tables: Tables = request.app.state.tables
    return tables


Catalog = Annotated[CatalogCache, Depends(get_catalog)]
EngineTables = Annotated[Tables, Depends(get_tables)]

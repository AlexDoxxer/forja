"""Fábrica de la aplicación FastAPI de Forja (prefijo ``/api/v1``)."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

from fastapi import APIRouter, FastAPI
from forja_engine import Tables, load_tables

from app.api.routers import auth, profile, system
from app.core.config import Settings, get_settings
from app.core.errors import install_handlers
from app.core.logging import configure_logging
from app.db.session import create_engine, create_sessionmaker
from app.security.middleware import BodyLimitAndCsrfMiddleware, RequestContextMiddleware
from app.security.ratelimit import RateLimiter
from app.services.catalog_cache import CatalogCache

API_PREFIX: Final = "/api/v1"
SPECS_DIR_ENV: Final = "FORJA_SPECS_DIR"


def find_specs_dir() -> Path:
    """``$FORJA_SPECS_DIR``, ``/app/specs`` (imagen) o el ``specs/`` del repositorio."""
    configured = os.environ.get(SPECS_DIR_ENV)
    if configured:
        return Path(configured)
    image = Path("/app/specs")
    if image.is_dir():
        return image
    return Path(__file__).resolve().parents[2] / "specs"


def create_app(settings: Settings | None = None, *, rate_limit_scale: int = 1) -> FastAPI:
    """Crea la app. ``rate_limit_scale`` multiplica los límites (solo pruebas)."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)
    tables: Tables = load_tables(find_specs_dir())  # falla rápido si las tablas no son válidas

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(resolved)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        app.state.catalog = CatalogCache(app.state.sessionmaker)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Forja API",
        version="1.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.tables = tables
    app.state.rate_limiter = RateLimiter(scale=rate_limit_scale)
    install_handlers(app)
    # El último middleware añadido es el más externo.
    app.add_middleware(BodyLimitAndCsrfMiddleware)
    app.add_middleware(RequestContextMiddleware)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(system.router)
    api.include_router(auth.router)
    api.include_router(profile.router)
    app.include_router(api)
    return app

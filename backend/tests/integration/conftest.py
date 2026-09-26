"""Fixtures de integración: PostgreSQL 16 efímero (testcontainers), migraciones, catálogo real
(1.324 ejercicios sin instrucciones) y cliente HTTP contra la app FastAPI."""

import asyncio
import hashlib
import re
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.core.config import Settings
from app.main import create_app
from app.security.tokens import CSRF_COOKIE, CSRF_HEADER
from ingest.catalog import build_catalog
from ingest.load import load_catalog
from ingest.media import Manifest, ManifestFile
from ingest.specs import load_specs
from ingest.tests.conftest import index_records
from tests.contract.test_openapi_contract import (
    operations as contract_operations,
)
from tests.contract.test_openapi_contract import resolve as contract_resolve
from tests.contract.test_openapi_contract import validator_for as contract_validator

POSTGRES_IMAGE = "postgres:16-alpine"
BACKEND_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "brasa-y-yunque-2026"  # noqa: S105 (contraseña de prueba)


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """URL ``postgresql+asyncpg://`` de un PostgreSQL 16 desechable para la sesión de tests."""
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        yield container.get_connection_url()


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["url"] = url
    return config


async def migrate(url: str, revision: str = "head", *, down: bool = False) -> None:
    config = alembic_config(url)
    action = command.downgrade if down else command.upgrade
    await asyncio.to_thread(action, config, revision)


def synthetic_manifest(commit: str, paths: list[tuple[str, str, str]]) -> Manifest:
    """Manifest con hashes sintéticos (los tests de la API no leen medios)."""
    files = tuple(
        ManifestFile(
            exercise_id=exercise_id,
            kind=kind,  # type: ignore[arg-type]  # 'thumb' | 'gif'
            path=path,
            bytes=1,
            sha256=hashlib.sha256(path.encode()).hexdigest(),
            width=180,
            height=180,
        )
        for exercise_id, kind, path in paths
    )
    return Manifest(repo="https://example.invalid/dataset", commit=commit, files=files)


@pytest.fixture(scope="session")
async def db_url(postgres_url: str) -> str:
    """Base con migraciones aplicadas y el catálogo completo cargado por la ingesta."""
    name = "forja_api"
    admin = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin.dispose()
    url = postgres_url.rsplit("/", 1)[0] + f"/{name}"
    await migrate(url)
    specs = load_specs()
    catalog = build_catalog(index_records(), specs)
    paths = [
        (entry.exercise.id, kind, path)
        for entry in catalog.entries
        for kind, path in (("thumb", entry.exercise.thumb_path), ("gif", entry.exercise.gif_path))
    ]
    manifest = synthetic_manifest("7455efae41b330c265e7cd4b78dfa848e7ce5ebd", paths)
    await load_catalog(url, catalog, manifest, specs, media_verified=len(paths))
    return url


@pytest.fixture(scope="session")
def media_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("media")
    (root / "manifest.json").write_text("{}", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def settings(db_url: str, media_root: Path) -> Settings:
    return Settings(
        database_url=db_url,  # type: ignore[arg-type]  # str → PostgresDsn
        secret_key="s" * 48,  # type: ignore[arg-type]
        public_base_url="https://forja.test",  # type: ignore[arg-type]
        media_root=media_root,
        registration_open=True,
    )


@pytest.fixture(scope="session")
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, rate_limit_scale=10_000)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture(scope="session")
async def engine(db_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(db_url)
    yield eng
    await eng.dispose()


@pytest.fixture
async def clean_state(engine: AsyncEngine, app: FastAPI) -> None:
    """Deja vacías las tablas de usuario entre tests (el catálogo se conserva)."""
    async with engine.begin() as conn:
        await conn.execute(
            text('TRUNCATE "user", app_setting, audit_log, meal_plan, idempotency_key CASCADE')
        )
    app.state.rate_limiter.reset()


def _operations() -> list[tuple[str, re.Pattern[str], dict[str, Any]]]:
    found = []
    for method, path, operation in contract_operations():
        regex = re.sub(r"\{[^}]+\}", "[^/]+", path)
        found.append((method, re.compile(f"^{regex}$"), operation))
    return found


CONTRACT_ROUTES = _operations()


async def _assert_matches_contract(response: httpx.Response) -> None:
    """Toda respuesta JSON de la API debe cumplir el esquema del contrato para su operación."""
    path = response.request.url.path.removeprefix("/api/v1")
    method = response.request.method.lower()
    operation = next(
        (op for m, rx, op in CONTRACT_ROUTES if m == method and rx.match(path)), None
    )
    if operation is None or "json" not in response.headers.get("content-type", ""):
        return
    spec = operation["responses"].get(str(response.status_code))
    if spec is None:
        return
    body = contract_resolve(spec).get("content", {})
    media = next((v for k, v in body.items() if "json" in k), None)
    if media is None or "schema" not in media:
        return
    await response.aread()
    errors = list(contract_validator(media["schema"]).iter_errors(response.json()))
    assert not errors, (
        f"{method.upper()} {path} -> {response.status_code} incumple el contrato: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:3])
    )


def _sync_csrf(client: httpx.AsyncClient) -> Callable[[httpx.Response], Any]:
    async def hook(response: httpx.Response) -> None:
        token = client.cookies.get(CSRF_COOKIE)
        if token:
            client.headers[CSRF_HEADER] = token
        await _assert_matches_contract(response)

    return hook


@pytest.fixture
async def client(app: FastAPI, clean_state: None) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente sin sesión (HTTPS para que la cookie ``__Host-`` con ``Secure`` se envíe)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://forja.test/api/v1"
    ) as http:
        http.event_hooks["response"] = [_sync_csrf(http)]
        response = await http.get("/auth/csrf")
        assert response.status_code == 204
        yield http


async def register_user(
    http: httpx.AsyncClient, email: str = "lucia@example.org", name: str = "Lucía"
) -> dict[str, Any]:
    response = await http.post(
        "/auth/register", json={"email": email, "password": PASSWORD, "display_name": name}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
async def user(client: httpx.AsyncClient) -> dict[str, Any]:
    """Cliente autenticado (primer usuario ⇒ admin)."""
    return await register_user(client)


@pytest.fixture
async def other_client(app: FastAPI, user: dict[str, Any]) -> AsyncIterator[httpx.AsyncClient]:
    """Segundo usuario (rol ``user``) con su propia sesión; ``user`` (admin) se crea antes."""
    _ = user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://forja.test/api/v1"
    ) as http:
        http.event_hooks["response"] = [_sync_csrf(http)]
        await http.get("/auth/csrf")
        await register_user(http, "mario@example.org", "Mario")
        yield http

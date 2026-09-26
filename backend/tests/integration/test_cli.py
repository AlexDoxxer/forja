"""CLI operativa: ``create-admin`` y ``seed-demo``."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from typer.testing import CliRunner

from app.cli import DEMO_EMAIL, app
from app.core.config import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture
def cli_env(monkeypatch: pytest.MonkeyPatch, db_url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://forja.test")
    get_settings.cache_clear()


def test_seed_demo_and_create_admin(cli_env: None, engine: AsyncEngine) -> None:
    runner = CliRunner()
    first = runner.invoke(app, ["seed-demo"])
    assert first.exit_code == 0, first.output
    assert "created" in first.output
    assert "exists" in runner.invoke(app, ["seed-demo"]).output
    weak = runner.invoke(
        app,
        ["create-admin", "--email", "root@forja.local", "--password", "password123"],
        input="password123\n",
    )
    assert weak.exit_code == 1
    ok = runner.invoke(
        app,
        ["create-admin", "--email", "root@forja.local", "--password", "clave-larga-de-admin-9"],
        input="clave-larga-de-admin-9\n",
    )
    assert ok.exit_code == 0, ok.output
    get_settings.cache_clear()
    assert DEMO_EMAIL == "demo@forja.local"
    _ = engine


async def test_cleanup(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE "user" CASCADE'))

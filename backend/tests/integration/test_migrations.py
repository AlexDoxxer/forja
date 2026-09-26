"""Migración inicial reversible: upgrade → downgrade → upgrade y coincidencia con los modelos."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.catalog import Base
from tests.integration.conftest import migrate

pytestmark = pytest.mark.integration

EXPECTED_INDEXES = {
    "ix_exercise_search_vector",
    "ix_exercise_name_es_trgm",
    "ix_set_log_session_id_exercise_id",
    "ix_workout_session_user_id_started_at",
    "uq_program_user_id_active",
}


async def _tables(url: str) -> tuple[set[str], set[str]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            tables = {
                row[0]
                for row in await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            }
            indexes = {
                row[0]
                for row in await conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
                )
            }
    finally:
        await engine.dispose()
    return tables, indexes


async def test_upgrade_downgrade_upgrade(postgres_url: str) -> None:
    name = f"mig_{uuid.uuid4().hex[:10]}"
    admin = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin.dispose()
    url = postgres_url.rsplit("/", 1)[0] + f"/{name}"

    await migrate(url)
    tables, indexes = await _tables(url)
    assert set(Base.metadata.tables) <= tables
    assert EXPECTED_INDEXES <= indexes

    await migrate(url, "base", down=True)
    tables, _ = await _tables(url)
    assert tables == {"alembic_version"}

    await migrate(url)
    tables, _ = await _tables(url)
    assert set(Base.metadata.tables) <= tables


async def test_extensions_and_position_column(db_url: str) -> None:
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            extensions = {
                row[0] for row in await conn.execute(text("SELECT extname FROM pg_extension"))
            }
            column = (
                await conn.execute(
                    text(
                        "SELECT is_nullable FROM information_schema.columns "
                        "WHERE table_name = 'exercise_secondary_muscle' AND column_name = 'position'"
                    )
                )
            ).scalar_one()
    finally:
        await engine.dispose()
    assert {"unaccent", "pg_trgm", "citext"} <= extensions
    assert column == "NO"

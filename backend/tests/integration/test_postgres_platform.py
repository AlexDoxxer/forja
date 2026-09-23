"""La plataforma de BD fijada en MASTER_PROMPT §4.1/§5 ofrece lo que el modelo necesita."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

REQUIRED_EXTENSIONS = ("unaccent", "pg_trgm")
POSTGRES_MAJOR = 16


async def test_postgres_major_version(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as conn:
            version_num = (await conn.execute(text("SHOW server_version_num"))).scalar_one()
    finally:
        await engine.dispose()
    assert int(version_num) // 10000 == POSTGRES_MAJOR


async def test_required_extensions_install_and_work(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.begin() as conn:
            for extension in REQUIRED_EXTENSIONS:
                await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{extension}"'))
            unaccented = (
                await conn.execute(text("SELECT unaccent('elevación de talones')"))
            ).scalar_one()
            similarity = (
                await conn.execute(text("SELECT similarity('sentadilla', 'sentadila')"))
            ).scalar_one()
    finally:
        await engine.dispose()
    assert unaccented == "elevacion de talones"
    assert float(similarity) > 0.5

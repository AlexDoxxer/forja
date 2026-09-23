"""Fixtures de integración: PostgreSQL 16 efímero con testcontainers (requiere Docker)."""

from collections.abc import Iterator

import pytest
from testcontainers.community.postgres import PostgresContainer

POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """URL ``postgresql+asyncpg://`` de un PostgreSQL 16 desechable para la sesión de tests."""
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        yield container.get_connection_url()

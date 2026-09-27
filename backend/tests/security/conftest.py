"""Reutiliza las fixtures de integración (PostgreSQL efímero, cliente, dos usuarios)."""

from tests.integration.conftest import (  # noqa: F401
    app,
    clean_state,
    client,
    db_url,
    engine,
    media_root,
    other_client,
    postgres_url,
    settings,
    user,
)

"""Ejecuta ``alembic upgrade head`` bajo un bloqueo consultivo de PostgreSQL.

Varios contenedores (api, ingest) pueden arrancar a la vez: el bloqueo de sesión
``pg_advisory_lock`` serializa las migraciones y garantiza que solo una las aplica.
"""

import asyncio
import os
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

import asyncpg

# Entero fijo derivado de "forja-migrate"; único en la base de datos de Forja.
LOCK_ID = 0x46_4F_52_4A_41_01
RETRIES = 30


def _dsn() -> str:
    url = os.environ["DATABASE_URL"]
    parts = urlsplit(url)
    scheme = parts.scheme.split("+", 1)[0]
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))


async def _connect() -> asyncpg.Connection:
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return await asyncpg.connect(_dsn())
        except (OSError, asyncpg.PostgresError) as exc:
            last = exc
            print(f"migrate: base de datos no disponible ({exc}); reintento {attempt + 1}", flush=True)
            await asyncio.sleep(2)
    raise SystemExit(f"migrate: no se pudo conectar: {last}")


async def main() -> int:
    conn = await _connect()
    try:
        print("migrate: esperando el bloqueo consultivo...", flush=True)
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_ID)
        print("migrate: alembic upgrade head", flush=True)
        proc = await asyncio.create_subprocess_exec("alembic", "upgrade", "head", cwd="/app")
        return await proc.wait()
    finally:
        await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""``Idempotency-Key`` (ADR 0009): repetición segura de POST de sesiones y series."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.models.program import IdempotencyKey
from app.models.user import User

RETENTION: Final = timedelta(hours=24)
IN_PROGRESS: Final = 0


def request_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


async def run_idempotent(
    db: AsyncSession,
    user: User,
    key: str,
    payload: Any,
    handler: Callable[[], Awaitable[tuple[int, dict[str, Any]]]],
) -> tuple[int, dict[str, Any], bool]:
    """Ejecuta ``handler`` una sola vez por (usuario, clave). Devuelve (estado, cuerpo, repetida)."""
    digest = request_hash(payload)
    user_id = user.id
    now = datetime.now(UTC)
    await db.execute(
        delete(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id, IdempotencyKey.expires_at < now
        )
    )
    existing = await db.get(IdempotencyKey, (user_id, key))
    if existing is not None:
        return _replay(existing, digest)
    db.add(
        IdempotencyKey(
            user_id=user_id,
            key=key,
            request_hash=digest,
            status_code=IN_PROGRESS,
            response=None,
            expires_at=now + RETENTION,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raced = await db.get(IdempotencyKey, (user_id, key))
        if raced is None:
            raise
        return _replay(raced, digest)
    try:
        status, body = await handler()
    except BaseException:
        await db.rollback()
        await db.execute(
            delete(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.key == key
            )
        )
        await db.commit()
        raise
    record = await db.get(IdempotencyKey, (user_id, key))
    if record is not None:
        record.status_code = status
        record.response = body
    await db.commit()
    return status, body, False


def _replay(row: IdempotencyKey, digest: str) -> tuple[int, dict[str, Any], bool]:
    if row.request_hash != digest:
        raise ProblemError(
            422,
            "idempotency_key_reused",
            "La clave de idempotencia ya se usó con otro cuerpo.",
        )
    if row.status_code == IN_PROGRESS or row.response is None:
        raise ProblemError(
            409, "idempotency_in_progress", "Hay una petición en curso con esa clave."
        )
    return row.status_code, row.response, True

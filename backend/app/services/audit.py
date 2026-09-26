"""Registro de auditoría de acciones de seguridad y de administración (sin PII sensible)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nutrition import AuditLog


async def audit(
    db: AsyncSession,
    action: str,
    *,
    actor: uuid.UUID | None,
    target: str | None = None,
    details: dict[str, Any] | None = None,
    ip_hash: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor,
            action=action,
            target=target,
            details=details or {},
            ip_hash=ip_hash,
        )
    )

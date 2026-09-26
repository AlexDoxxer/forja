"""Ajustes globales (``app_setting``) que prevalecen sobre el entorno (ADR 0003)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.nutrition import AppSetting

REGISTRATION_OPEN = "registration_open"
DIET_FEATURE_ENABLED = "diet_feature_enabled"


async def get_bool(db: AsyncSession, key: str, default: bool) -> bool:
    row = (
        await db.execute(select(AppSetting.value).where(AppSetting.key == key))
    ).scalar_one_or_none()
    return bool(row) if row is not None else default


async def set_bool(db: AsyncSession, key: str, value: bool) -> None:
    stmt = insert(AppSetting).values(key=key, value=value)
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[AppSetting.key],
            set_={"value": value, "updated_at": datetime.now(UTC)},
        )
    )


async def registration_open(db: AsyncSession, settings: Settings) -> bool:
    return await get_bool(db, REGISTRATION_OPEN, settings.registration_open)


async def diet_feature_enabled(db: AsyncSession, settings: Settings) -> bool:
    return await get_bool(db, DIET_FEATURE_ENABLED, settings.diet_feature_enabled)

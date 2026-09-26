"""Perfil, PAR-Q y métricas corporales."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import encode_cursor
from app.core.errors import not_found, unprocessable
from app.models.user import BodyMetric, Profile, User
from app.schemas import api
from app.services.auth import default_profile, onboarding_completed

PARQ_RECOMMENDATION = (
    "Te recomendamos consultar con un profesional sanitario antes de empezar. "
    "Hemos ajustado tu nivel a principiante; puedes cambiarlo en tu perfil."
)


async def load_profile(db: AsyncSession, user: User) -> Profile:
    profile = await db.get(Profile, user.id)
    if profile is None:  # cuentas creadas por importación o CLI sin perfil
        profile = default_profile(user.id)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
    return profile


def profile_dto(user: User, profile: Profile) -> api.Profile:
    return api.Profile(
        display_name=user.display_name,
        locale=cast("Any", user.locale),
        units=cast("Any", user.units),
        sex=cast("Any", profile.sex),
        birth_date=profile.birth_date,
        height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
        experience=cast("Any", profile.experience),
        activity_level=cast("Any", profile.activity_level),
        equipment=api.EquipmentSelection.model_validate(profile.equipment_profile),
        limitations=api.Limitations.model_validate(profile.limitations),
        diet_enabled=profile.diet_enabled,
        preferences=api.Preferences.model_validate(profile.preferences),
        parq_flagged=profile.parq_flagged,
        parq_completed_at=profile.parq_completed_at,
        onboarding_completed=onboarding_completed(profile),
        updated_at=profile.updated_at,
    )


async def get_profile(db: AsyncSession, user: User) -> api.Profile:
    return profile_dto(user, await load_profile(db, user))


async def update_profile(db: AsyncSession, user: User, body: api.ProfileUpdate) -> api.Profile:
    if body.equipment.preset == "custom" and not body.equipment.items:
        raise unprocessable(
            "validation_error",
            "Con el preset «custom» debes indicar al menos un equipamiento.",
            errors=[
                {
                    "loc": ["body", "equipment", "items"],
                    "msg": "Se necesita al menos un elemento",
                    "type": "too_short",
                }
            ],
        )
    profile = await load_profile(db, user)
    user.display_name = body.display_name
    user.locale = body.locale
    user.units = body.units
    profile.sex = body.sex
    profile.birth_date = body.birth_date
    profile.height_cm = Decimal(str(body.height_cm)) if body.height_cm is not None else None
    profile.experience = body.experience
    profile.activity_level = body.activity_level
    profile.equipment_profile = body.equipment.model_dump(mode="json")
    profile.limitations = body.limitations.model_dump(mode="json")
    profile.diet_enabled = body.diet_enabled
    profile.preferences = body.preferences.model_dump(mode="json")
    profile.updated_at = datetime.now(UTC)
    await db.commit()
    return profile_dto(user, profile)


async def submit_parq(db: AsyncSession, user: User, body: api.ParqSubmission) -> api.ParqResult:
    profile = await load_profile(db, user)
    answers = body.answers.model_dump(mode="json")
    flagged = any(answers.values())
    forced = flagged and profile.experience != "beginner"
    profile.parq_answers = answers
    profile.parq_flagged = flagged
    profile.parq_completed_at = datetime.now(UTC)
    if flagged:
        profile.experience = "beginner"
    profile.updated_at = datetime.now(UTC)
    await db.commit()
    return api.ParqResult(
        parq_flagged=flagged,
        experience_forced=forced,
        recommendation_es=PARQ_RECOMMENDATION if flagged else None,
        profile=profile_dto(user, profile),
    )


def metric_dto(row: BodyMetric) -> api.BodyMetric:
    return api.BodyMetric(
        id=row.id,
        date=row.date,
        weight_kg=float(row.weight_kg),
        body_fat_pct=float(row.body_fat_pct) if row.body_fat_pct is not None else None,
        waist_cm=float(row.waist_cm) if row.waist_cm is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_metrics(
    db: AsyncSession,
    user: User,
    *,
    from_date: date | None,
    to_date: date | None,
    cursor: dict[str, Any] | None,
    limit: int,
) -> api.BodyMetricPage:
    stmt = select(BodyMetric).where(BodyMetric.user_id == user.id)
    if from_date:
        stmt = stmt.where(BodyMetric.date >= from_date)
    if to_date:
        stmt = stmt.where(BodyMetric.date <= to_date)
    if cursor and "d" in cursor:
        stmt = stmt.where(BodyMetric.date < date.fromisoformat(str(cursor["d"])))
    rows = (
        (await db.execute(stmt.order_by(BodyMetric.date.desc()).limit(limit + 1))).scalars().all()
    )
    page = rows[:limit]
    next_cursor = encode_cursor({"d": page[-1].date.isoformat()}) if len(rows) > limit else None
    return api.BodyMetricPage(items=[metric_dto(r) for r in page], next_cursor=next_cursor)


async def upsert_metric(
    db: AsyncSession, user: User, body: api.BodyMetricCreate
) -> tuple[api.BodyMetric, bool]:
    """Devuelve la métrica y ``True`` si se ha creado (``False`` si sustituye la de esa fecha)."""
    existing = (
        await db.execute(
            select(BodyMetric).where(BodyMetric.user_id == user.id, BodyMetric.date == body.date)
        )
    ).scalar_one_or_none()
    values: dict[str, Any] = {
        "weight_kg": Decimal(str(body.weight_kg)),
        "body_fat_pct": Decimal(str(body.body_fat_pct)) if body.body_fat_pct is not None else None,
        "waist_cm": Decimal(str(body.waist_cm)) if body.waist_cm is not None else None,
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(UTC)
        row = existing
    else:
        row = BodyMetric(user_id=user.id, date=body.date, **values)
        db.add(row)
        await db.flush()
    await db.commit()
    await db.refresh(row)
    return metric_dto(row), existing is None


async def delete_metric(db: AsyncSession, user: User, metric_id: uuid.UUID) -> None:
    row = await db.get(BodyMetric, metric_id)
    if row is None or row.user_id != user.id:
        raise not_found("La métrica no existe.")
    await db.delete(row)
    await db.commit()

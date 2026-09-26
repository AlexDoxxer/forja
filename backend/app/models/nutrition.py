"""Nutrición y ajustes de sistema (``contracts/domain.md`` §4.4 y §4.5)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import uuid7
from app.models.catalog import Base, TimestampMixin
from app.models.program import fk_cascade
from app.models.user import fk_user, pk_uuid


class NutritionSettings(TimestampMixin, Base):
    __tablename__ = "nutrition_settings"

    user_id: Mapped[uuid.UUID] = fk_user(primary_key=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    pace: Mapped[str] = mapped_column(Text, nullable=False)
    diet_type: Mapped[str] = mapped_column(Text, nullable=False)
    meals_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    allergens: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_food_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    disliked_food_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    pregnant: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    breastfeeding: Mapped[bool] = mapped_column(nullable=False, server_default=false())


class Food(TimestampMixin, Base):
    __tablename__ = "food"
    __table_args__ = (
        Index(
            "ix_food_name_es_trgm",
            "name_es",
            postgresql_using="gin",
            postgresql_ops={"name_es": "gin_trgm_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_es: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    fdc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    per_100g: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    diet_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    allergens: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    macro_role: Mapped[str] = mapped_column(Text, nullable=False)
    typical_portion_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    unit_grams: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    unit_name_es: Mapped[str | None] = mapped_column(Text, nullable=True)


class NutritionTarget(TimestampMixin, Base):
    __tablename__ = "nutrition_target"

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 1), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 1), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 1), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 1), nullable=True)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 1), nullable=True)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)


class MealPlan(TimestampMixin, Base):
    __tablename__ = "meal_plan"

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    diet_type: Mapped[str] = mapped_column(Text, nullable=False)
    meals_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nutrition_version: Mapped[str] = mapped_column(Text, nullable=False)
    foods_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    notices: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)


class MealPlanItem(TimestampMixin, Base):
    __tablename__ = "meal_plan_item"

    id: Mapped[uuid.UUID] = pk_uuid()
    plan_id: Mapped[uuid.UUID] = fk_cascade("meal_plan")
    day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    meal: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    food_id: Mapped[str] = mapped_column(ForeignKey("food.id"), nullable=False)
    grams: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    units: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class AppSetting(TimestampMixin, Base):
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

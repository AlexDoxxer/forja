"""Usuarios, sesiones de autenticación, perfil y métricas (``contracts/domain.md`` §4.2)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column

from app.core.ids import uuid7
from app.models.catalog import Base, TimestampMixin, in_check

USER_ROLES: Final = ("user", "admin")
LOCALES: Final = ("es", "en")
UNITS: Final = ("metric", "imperial")
SEXES: Final = ("male", "female", "unspecified")
EXPERIENCES: Final = ("beginner", "intermediate", "advanced")
ACTIVITY_LEVELS: Final = ("sedentary", "light", "moderate", "high")


def pk_uuid() -> MappedColumn[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


def fk_user(*, primary_key: bool = False) -> MappedColumn[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(in_check("role", USER_ROLES), name="role"),
        CheckConstraint(in_check("locale", LOCALES), name="locale"),
        CheckConstraint(in_check("units", UNITS), name="units"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="es")
    units: Mapped[str] = mapped_column(Text, nullable=False, default="metric")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(TimestampMixin, Base):
    __tablename__ = "session"
    __table_args__ = (Index("ix_session_user_id_revoked_at", "user_id", "revoked_at"),)

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Profile(TimestampMixin, Base):
    __tablename__ = "profile"
    __table_args__ = (
        CheckConstraint(in_check("sex", SEXES), name="sex"),
        CheckConstraint(in_check("experience", EXPERIENCES), name="experience"),
        CheckConstraint(in_check("activity_level", ACTIVITY_LEVELS), name="activity_level"),
    )

    user_id: Mapped[uuid.UUID] = fk_user(primary_key=True)
    sex: Mapped[str] = mapped_column(Text, nullable=False, default="unspecified")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    experience: Mapped[str] = mapped_column(Text, nullable=False, default="beginner")
    activity_level: Mapped[str] = mapped_column(Text, nullable=False, default="light")
    equipment_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parq_answers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    parq_flagged: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    parq_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    diet_enabled: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class BodyMetric(TimestampMixin, Base):
    __tablename__ = "body_metric"
    __table_args__ = (UniqueConstraint("user_id", "date", name="user_date"),)

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    waist_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)


class FavoriteExercise(TimestampMixin, Base):
    __tablename__ = "favorite_exercise"

    user_id: Mapped[uuid.UUID] = fk_user(primary_key=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), primary_key=True)

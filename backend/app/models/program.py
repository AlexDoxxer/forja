"""Programas, sesiones de entreno y récords (``contracts/domain.md`` §4.3)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column

from app.models.catalog import Base, TimestampMixin, in_check
from app.models.user import fk_user, pk_uuid

PROGRAM_SOURCES: Final = ("generated", "manual", "imported")
WEEK_PHASES: Final = ("accumulation", "intensification", "deload")
BLOCK_KINDS: Final = ("warmup", "main", "superset", "circuit", "finisher", "cooldown")
SESSION_STATUSES: Final = ("in_progress", "completed", "abandoned")
RECORD_KINDS: Final = ("e1rm", "heaviest_set", "volume")


def fk_cascade(table: str) -> MappedColumn[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{table}.id", ondelete="CASCADE"), nullable=False
    )


def fk_set_null(table: str) -> MappedColumn[uuid.UUID | None]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{table}.id", ondelete="SET NULL"), nullable=True
    )


class Program(TimestampMixin, Base):
    __tablename__ = "program"
    __table_args__ = (
        CheckConstraint(in_check("source", PROGRAM_SOURCES), name="source"),
        Index(
            "uq_program_user_id_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    generator_input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    generator_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    tables_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weeks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    weekly_volume: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    rationale_es: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)


class ProgramWeek(TimestampMixin, Base):
    __tablename__ = "program_week"
    __table_args__ = (
        UniqueConstraint("program_id", "index", name="program_index"),
        CheckConstraint(in_check("phase", WEEK_PHASES), name="phase"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    program_id: Mapped[uuid.UUID] = fk_cascade("program")
    index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    phase: Mapped[str] = mapped_column(Text, nullable=False)
    target_rir: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    volume_ratio: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)


class ProgramDay(TimestampMixin, Base):
    __tablename__ = "program_day"
    __table_args__ = (UniqueConstraint("week_id", "index", name="week_index"),)

    id: Mapped[uuid.UUID] = pk_uuid()
    week_id: Mapped[uuid.UUID] = fk_cascade("program_week")
    index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekday: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recovery: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class ProgramBlock(TimestampMixin, Base):
    __tablename__ = "program_block"
    __table_args__ = (CheckConstraint(in_check("kind", BLOCK_KINDS), name="kind"),)

    id: Mapped[uuid.UUID] = pk_uuid()
    day_id: Mapped[uuid.UUID] = fk_cascade("program_day")
    order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    rounds: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    rest_between_rounds_s: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class ProgramExercise(TimestampMixin, Base):
    __tablename__ = "program_exercise"
    __table_args__ = (
        CheckConstraint(
            "(rep_min IS NOT NULL AND rep_max IS NOT NULL) OR duration_s IS NOT NULL",
            name="reps_or_duration",
        ),
        CheckConstraint("rep_min <= rep_max", name="rep_range"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    block_id: Mapped[uuid.UUID] = fk_cascade("program_block")
    order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), nullable=False)
    slot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sets: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rep_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rep_max: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    target_rir: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    tempo: Mapped[str | None] = mapped_column(Text, nullable=True)
    rest_s: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_s: Mapped[int | None] = mapped_column(nullable=True)
    per_side: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    load_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternatives: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class WorkoutSession(TimestampMixin, Base):
    __tablename__ = "workout_session"
    __table_args__ = (
        UniqueConstraint("user_id", "client_uuid", name="user_client_uuid"),
        CheckConstraint(in_check("status", SESSION_STATUSES), name="status"),
        CheckConstraint("perceived_effort BETWEEN 1 AND 10", name="perceived_effort"),
        Index("ix_workout_session_user_id_started_at", "user_id", text("started_at DESC")),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    client_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    program_id: Mapped[uuid.UUID | None] = fk_set_null("program")
    program_day_id: Mapped[uuid.UUID | None] = fk_set_null("program_day")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="in_progress")
    perceived_effort: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SetLog(TimestampMixin, Base):
    __tablename__ = "set_log"
    __table_args__ = (
        UniqueConstraint("client_uuid", name="client_uuid"),
        Index("ix_set_log_session_id_exercise_id", "session_id", "exercise_id"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    session_id: Mapped[uuid.UUID] = fk_cascade("workout_session")
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), nullable=False)
    program_exercise_id: Mapped[uuid.UUID | None] = fk_set_null("program_exercise")
    set_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    reps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rir: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    duration_s: Mapped[int | None] = mapped_column(nullable=True)
    is_warmup: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PersonalRecord(TimestampMixin, Base):
    __tablename__ = "personal_record"
    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", "kind", name="user_exercise_kind"),
        CheckConstraint(in_check("kind", RECORD_KINDS), name="kind"),
    )

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = fk_user()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    reps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_id: Mapped[uuid.UUID] = fk_cascade("workout_session")
    set_id: Mapped[uuid.UUID | None] = fk_set_null("set_log")


class IdempotencyKey(TimestampMixin, Base):
    __tablename__ = "idempotency_key"

    user_id: Mapped[uuid.UUID] = fk_user(primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

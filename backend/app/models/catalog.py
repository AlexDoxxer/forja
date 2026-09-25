"""Modelos SQLAlchemy del catálogo y de ``ingest_run`` (``contracts/domain.md`` §4.1 y §4.5).

Creado por ``ingesta-datos`` porque ``backend-api`` aún no tenía modelos (ADR 0002, zona
compartida); a partir de ahora lo mantiene ``backend-api``, que también escribe la migración
Alembic equivalente. Las enumeraciones se guardan como ``text`` con ``CHECK``.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION: Final = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


MUSCLE_REGIONS: Final = ("upper", "lower", "core", "cardio", "other")
EQUIPMENT_GROUPS: Final = ("gym", "home_basic", "bodyweight", "cardio_machine", "other")
BODY_PARTS: Final = (
    "upper_arms",
    "upper_legs",
    "back",
    "waist",
    "chest",
    "shoulders",
    "lower_legs",
    "lower_arms",
    "cardio",
    "neck",
)
MOVEMENT_PATTERNS: Final = (
    "squat",
    "lunge",
    "hinge",
    "horizontal_push",
    "vertical_push",
    "horizontal_pull",
    "vertical_pull",
    "elbow_flexion",
    "elbow_extension",
    "shoulder_raise",
    "chest_fly",
    "rear_delt",
    "knee_extension",
    "knee_flexion",
    "hip_abduction",
    "hip_adduction",
    "glute_isolation",
    "calf",
    "core_flexion",
    "core_anti_extension",
    "core_rotation",
    "core_lateral",
    "shrug",
    "forearm",
    "neck",
    "carry",
    "plyometric",
    "cardio",
    "mobility",
    "other",
)
MECHANICS: Final = ("compound", "isolation")
ROLES: Final = ("main", "accessory", "core", "cardio", "mobility", "warmup")
LATERALITIES: Final = ("bilateral", "unilateral")
DEMO_SEXES: Final = ("male", "female")
LOAD_TYPES: Final = ("external", "bodyweight", "assisted", "time")
VARIANT_KINDS: Final = ("version", "demonstrator", "camera_angle", "duplicate")
INSTRUCTION_LANGS: Final = ("en", "es", "it", "tr", "ru", "zh", "hi", "pl", "ko", "fr")
INGEST_STATUSES: Final = ("queued", "running", "succeeded", "failed")


class Base(DeclarativeBase):
    """Base declarativa con convención de nombres estable para Alembic."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Muscle(TimestampMixin, Base):
    __tablename__ = "muscle"
    __table_args__ = (CheckConstraint(_in("region", MUSCLE_REGIONS), name="region"),)

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name_es: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(Text, nullable=False)
    volume_group: Mapped[str | None] = mapped_column(Text, nullable=True)


class Equipment(TimestampMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (CheckConstraint(_in('"group"', EQUIPMENT_GROUPS), name="group"),)

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name_es: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    group: Mapped[str] = mapped_column(Text, nullable=False)


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercise"
    __table_args__ = (
        CheckConstraint("id ~ '^[0-9]{4}$'", name="id_format"),
        CheckConstraint(_in("body_part", BODY_PARTS), name="body_part"),
        CheckConstraint(_in("movement_pattern", MOVEMENT_PATTERNS), name="movement_pattern"),
        CheckConstraint(_in("mechanic", MECHANICS), name="mechanic"),
        CheckConstraint(_in("role", ROLES), name="role"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="difficulty"),
        CheckConstraint(_in("laterality", LATERALITIES), name="laterality"),
        CheckConstraint(f"demo_sex IS NULL OR {_in('demo_sex', DEMO_SEXES)}", name="demo_sex"),
        CheckConstraint(
            f"variant_kind IS NULL OR {_in('variant_kind', VARIANT_KINDS)}", name="variant_kind"
        ),
        CheckConstraint(_in("load_type", LOAD_TYPES), name="load_type"),
        Index("ix_exercise_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_exercise_name_es_trgm",
            "name_es",
            postgresql_using="gin",
            postgresql_ops={"name_es": "gin_trgm_ops"},
        ),
        Index(
            "ix_exercise_display_name_en_trgm",
            "display_name_en",
            postgresql_using="gin",
            postgresql_ops={"display_name_en": "gin_trgm_ops"},
        ),
        Index("ix_exercise_movement_pattern", "movement_pattern"),
        Index("ix_exercise_equipment_code", "equipment_code"),
        Index("ix_exercise_target_muscle", "target_muscle"),
        Index("ix_exercise_variant_group", "variant_group"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    media_id: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    display_name_en: Mapped[str] = mapped_column(Text, nullable=False)
    name_es: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    body_part: Mapped[str] = mapped_column(Text, nullable=False)
    equipment_code: Mapped[str] = mapped_column(ForeignKey("equipment.code"), nullable=False)
    target_muscle: Mapped[str] = mapped_column(ForeignKey("muscle.code"), nullable=False)
    primary_group_muscle: Mapped[str] = mapped_column(ForeignKey("muscle.code"), nullable=False)
    movement_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    mechanic: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_staple: Mapped[bool] = mapped_column(nullable=False)
    laterality: Mapped[str] = mapped_column(Text, nullable=False)
    demo_sex: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_group: Mapped[str] = mapped_column(Text, nullable=False)
    variant_kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_label_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    load_type: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_path: Mapped[str] = mapped_column(Text, nullable=False)
    gif_path: Mapped[str] = mapped_column(Text, nullable=False)
    media_sha256_thumb: Mapped[str] = mapped_column(String(64), nullable=False)
    media_sha256_gif: Mapped[str] = mapped_column(String(64), nullable=False)
    source_commit: Mapped[str] = mapped_column(String(40), nullable=False)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)
    enrichment_version: Mapped[int] = mapped_column(nullable=False)


class ExerciseSecondaryMuscle(Base):
    __tablename__ = "exercise_secondary_muscle"

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True
    )
    muscle_code: Mapped[str] = mapped_column(ForeignKey("muscle.code"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class ExerciseInstruction(TimestampMixin, Base):
    __tablename__ = "exercise_instruction"
    __table_args__ = (CheckConstraint(_in("lang", INSTRUCTION_LANGS), name="lang"),)

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True
    )
    lang: Mapped[str] = mapped_column(Text, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class ExerciseAlternative(Base):
    __tablename__ = "exercise_alternative"
    __table_args__ = (CheckConstraint("rank BETWEEN 1 AND 8", name="rank"),)

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True
    )
    alt_id: Mapped[str] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class IngestRun(TimestampMixin, Base):
    __tablename__ = "ingest_run"
    __table_args__ = (CheckConstraint(_in("status", INGEST_STATUSES), name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    commit: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    dry_run: Mapped[bool] = mapped_column(nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counts: Mapped[dict[str, int] | None] = mapped_column(JSONB, nullable=True)
    diff: Mapped[dict[str, list[str]] | None] = mapped_column(JSONB, nullable=True)
    checksums_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


CATALOG_TABLES: Final[tuple[str, ...]] = (
    "muscle",
    "equipment",
    "exercise",
    "exercise_secondary_muscle",
    "exercise_instruction",
    "exercise_alternative",
    "ingest_run",
)

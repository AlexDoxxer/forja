"""Catálogo ``ExerciseCard[]`` en memoria por proceso, invalidado tras una ingesta.

Con varios workers (gunicorn) una ingesta lanzada por CLI no puede invalidar la caché de los
demás procesos, así que cada lectura comprueba como mucho cada ``REFRESH_SECONDS`` una huella
barata (``count`` + ``max(updated_at)`` de ``exercise``) y recarga si cambió.
"""

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from forja_engine.models import ExerciseCard
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.catalog import Equipment, Exercise, ExerciseSecondaryMuscle

REFRESH_SECONDS: Final = 30.0


@dataclass
class CatalogSnapshot:
    cards: tuple[ExerciseCard, ...]
    by_id: dict[str, ExerciseCard]
    fingerprint: str


@dataclass
class CatalogCache:
    sessionmaker: async_sessionmaker[AsyncSession]
    refresh_seconds: float = REFRESH_SECONDS
    loads: int = 0
    _snapshot: CatalogSnapshot | None = None
    _checked_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def invalidate(self) -> None:
        """Descarta la caché (tras una ingesta): la próxima lectura recarga de la BD."""
        self._snapshot = None
        self._checked_at = 0.0

    async def snapshot(self) -> CatalogSnapshot:
        now = time.monotonic()
        current = self._snapshot
        if current is not None and now - self._checked_at < self.refresh_seconds:
            return current
        async with self._lock, self.sessionmaker() as db:
            fingerprint = await _fingerprint(db)
            if self._snapshot is None or self._snapshot.fingerprint != fingerprint:
                self._snapshot = await _load(db, fingerprint)
                self.loads += 1
            self._checked_at = time.monotonic()
            return self._snapshot

    async def cards(self) -> Sequence[ExerciseCard]:
        return (await self.snapshot()).cards


async def _fingerprint(db: AsyncSession) -> str:
    count, newest = (
        await db.execute(select(func.count(), func.max(Exercise.updated_at)).select_from(Exercise))
    ).one()
    deprecated = (
        await db.execute(
            select(func.count()).select_from(Exercise).where(Exercise.deprecated_at.is_not(None))
        )
    ).scalar_one()
    return f"{count}:{deprecated}:{newest.isoformat() if newest else ''}"


async def _load(db: AsyncSession, fingerprint: str) -> CatalogSnapshot:
    secondary: dict[str, list[str]] = {}
    for exercise_id, muscle in await db.execute(
        select(ExerciseSecondaryMuscle.exercise_id, ExerciseSecondaryMuscle.muscle_code).order_by(
            ExerciseSecondaryMuscle.exercise_id, ExerciseSecondaryMuscle.position
        )
    ):
        secondary.setdefault(exercise_id, []).append(muscle)
    rows = await db.execute(
        select(Exercise, Equipment.group)
        .join(Equipment, Equipment.code == Exercise.equipment_code)
        .order_by(Exercise.id)
    )
    cards = tuple(
        ExerciseCard.model_validate(
            {
                "id": ex.id,
                "name_es": ex.name_es,
                "display_name_en": ex.display_name_en,
                "variant_group": ex.variant_group,
                "body_part": ex.body_part,
                "equipment_code": ex.equipment_code,
                "equipment_group": group,
                "target_muscle": ex.target_muscle,
                "primary_group_muscle": ex.primary_group_muscle,
                "secondary_muscles": secondary.get(ex.id, []),
                "movement_pattern": ex.movement_pattern,
                "mechanic": ex.mechanic,
                "role": ex.role,
                "difficulty": ex.difficulty,
                "is_staple": ex.is_staple,
                "laterality": ex.laterality,
                "load_type": ex.load_type,
                "demo_sex": ex.demo_sex,
                "deprecated": ex.deprecated_at is not None,
            }
        )
        for ex, group in rows
    )
    return CatalogSnapshot(cards=cards, by_id={c.id: c for c in cards}, fingerprint=fingerprint)

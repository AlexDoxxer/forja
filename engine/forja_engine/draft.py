"""Estructuras de trabajo mutables del pipeline (antes de componer los DTOs inmutables).

Los pasos 5 a 8 construyen y ajustan días en borrador; el paso 9 (``compose``) los convierte
en ``PlanDay``/``PlanBlock``/``PlanExercise`` congelados.
"""

import copy
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from forja_engine.models import (
    BlockKind,
    ExerciseCard,
    ExerciseRole,
    SlotRef,
    Weekday,
)


class TimedExercise(Protocol):
    """Lo que necesitan la estimación de tiempo y el cómputo de volumen de un ejercicio."""

    @property
    def exercise_id(self) -> str: ...
    @property
    def sets(self) -> int: ...
    @property
    def rep_min(self) -> int | None: ...
    @property
    def rep_max(self) -> int | None: ...
    @property
    def duration_s(self) -> int | None: ...
    @property
    def per_side(self) -> bool: ...
    @property
    def tempo(self) -> str | None: ...
    @property
    def rest_s(self) -> int: ...
    @property
    def target_rir(self) -> int | None: ...


class TimedBlock(Protocol):
    """Bloque con los datos necesarios para estimar su duración."""

    @property
    def kind(self) -> BlockKind: ...
    @property
    def rounds(self) -> int: ...
    @property
    def rest_between_rounds_s(self) -> int | None: ...
    @property
    def exercises(self) -> Sequence[TimedExercise]: ...


@dataclass
class DraftExercise:
    """Ejercicio en borrador con su prescripción y los límites que usa el ajuste al tiempo."""

    card: ExerciseCard
    slot: SlotRef | None
    rx_role: ExerciseRole
    sets: int
    rep_min: int | None
    rep_max: int | None
    duration_s: int | None
    per_side: bool
    target_rir: int | None
    tempo: str | None
    rest_s: int
    rest_floor_s: int
    load_hint: str | None = None
    notes_es: str | None = None
    alternatives: tuple[str, ...] = ()

    @property
    def exercise_id(self) -> str:
        return self.card.id

    @property
    def priority(self) -> int:
        """Prioridad del slot (1 alta … 3 baja); sin slot se considera la más baja."""
        return self.slot.priority if self.slot is not None else 4


@dataclass
class DraftBlock:
    """Bloque en borrador; en superseries y circuitos ``sets`` de cada ejercicio = ``rounds``."""

    kind: BlockKind
    exercises: list[DraftExercise]
    rounds: int = 1
    rest_between_rounds_s: int | None = None


@dataclass
class DraftDay:
    """Día en borrador de la semana tipo (o de una semana concreta tras periodizar)."""

    index: int
    template: str
    name_es: str
    focus_es: str
    is_recovery: bool
    weekday: Weekday | None
    blocks: list[DraftBlock] = field(default_factory=list)

    def working_exercises(self) -> list[DraftExercise]:
        return [
            exercise
            for block in self.blocks
            if block.kind in {BlockKind.MAIN, BlockKind.SUPERSET, BlockKind.CIRCUIT}
            for exercise in block.exercises
        ]

    def clone(self) -> "DraftDay":
        return copy.deepcopy(self)

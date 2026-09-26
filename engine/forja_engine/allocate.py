"""Paso 4 (§7.2): repartir el volumen semanal en los slots de cada día.

Cada slot parte de las series base de ``prescription.yaml`` (objetivo por rol por nivel) y se
ajusta de forma determinista, serie a serie, hacia el objetivo semanal de cada grupo, sin
superar ``max_effective_sets_per_group_per_session`` (10) por grupo y sesión ni los límites
por ejercicio de ``engine-rules.yaml#allocation``.
"""

from collections.abc import Callable

from forja_engine.draft import DraftBlock, DraftDay, DraftExercise
from forja_engine.models import (
    BlockKind,
    ExerciseRole,
    Experience,
    Goal,
    PlanWarning,
    PlanWarningCode,
    SlotRef,
    VolumeGroup,
)
from forja_engine.split import DaySpec
from forja_engine.tables import Range, Tables
from forja_engine.texts import number_es
from forja_engine.volume import Credits, GroupTarget, slot_credits

SlotKey = tuple[int, int]
ALLOCATED_ROLES = frozenset({ExerciseRole.MAIN, ExerciseRole.ACCESSORY, ExerciseRole.CORE})


def pick_from_range(values: Range, rule: str) -> int:
    """Valor de un rango según la regla de nivel: ``min``, ``mid`` (media, a la baja) o ``max``."""
    low, high = values
    if rule == "min":
        return low
    if rule == "max":
        return high
    return (low + high) // 2


def base_sets(goal: Goal, role: ExerciseRole, level: Experience, tables: Tables) -> int:
    """Series de partida de un slot (§7.5; principiantes en el mínimo del rango)."""
    rx = tables.prescription
    rule = rx.experience_adjustments[level].sets
    if role is ExerciseRole.CORE:
        return pick_from_range(rx.common.core.sets, rule)
    return pick_from_range(
        rx.table[goal]["main" if role is ExerciseRole.MAIN else "accessory"].sets, rule
    )


def role_bounds(role: ExerciseRole, goal: Goal, level: Experience, tables: Tables) -> Range:
    """Series mínimas y máximas por ejercicio (B2).

    Main y accesorio salen de ``prescription.yaml`` (``[sets.min, sets.max]`` del objetivo,
    con suelo ``min_sets_per_exercise``); los principiantes quedan fijados en el mínimo del
    rango. El core usa ``allocation.core_bounds``.
    """
    allocation = tables.engine_rules.allocation
    if role is ExerciseRole.CORE:
        return allocation.core_bounds
    rx = tables.prescription.table[goal]["main" if role is ExerciseRole.MAIN else "accessory"]
    floor = allocation.min_sets_per_exercise
    low = max(floor, rx.sets[0])
    if tables.prescription.experience_adjustments[level].sets == "min":
        return (low, low)
    return (low, max(low, rx.sets[1]))


class _Allocator:
    def __init__(
        self,
        days: list[DaySpec],
        targets: dict[VolumeGroup, GroupTarget],
        goal: Goal,
        level: Experience,
        tables: Tables,
    ) -> None:
        self.tables = tables
        self.goal = goal
        self.level = level
        self.targets = targets
        self.cap = tables.volume_targets.max_effective_sets_per_group_per_session
        self.tolerance = tables.engine_rules.allocation.tolerance_sets
        self.slots: dict[SlotKey, SlotRef] = {}
        self.credits: dict[SlotKey, Credits] = {}
        self.sets: dict[SlotKey, int] = {}
        self.week: dict[VolumeGroup, float] = dict.fromkeys(VolumeGroup, 0.0)
        self.day: dict[tuple[int, VolumeGroup], float] = {}
        for day in days:
            if day.is_recovery:
                continue
            for slot in day.slots:
                if slot.role not in ALLOCATED_ROLES:
                    continue
                key = (day.index, slot.slot_index)
                self.slots[key] = slot
                self.credits[key] = slot_credits(slot, tables)
                low, high = self._bounds(slot.role)
                self._change(key, min(max(base_sets(goal, slot.role, level, tables), low), high))

    def _bounds(self, role: ExerciseRole) -> Range:
        return role_bounds(role, self.goal, self.level, self.tables)

    def _change(self, key: SlotKey, sets: int) -> None:
        delta = sets - self.sets.get(key, 0)
        self.sets[key] = sets
        for group, credit in self.credits[key]:
            self.week[group] += credit * delta
            day_key = (key[0], group)
            self.day[day_key] = self.day.get(day_key, 0.0) + credit * delta

    def _targets_group(self, key: SlotKey, group: VolumeGroup) -> bool:
        return self.slots[key].group.value == group.value

    def _fits_cap(self, key: SlotKey) -> bool:
        return all(
            self.day[(key[0], group)] + credit <= self.cap for group, credit in self.credits[key]
        )

    def reduce_overshoot(self) -> None:
        for group in VolumeGroup:
            limit = self.targets[group].target + self.tolerance
            while self.week[group] > limit:
                options = [
                    key
                    for key in self.slots
                    if self._targets_group(key, group)
                    and self.sets[key] > self._bounds(self.slots[key].role)[0]
                ]
                if not options:
                    break
                key = max(options, key=lambda k: (self.slots[k].priority, self.sets[k], k))
                self._change(key, self.sets[key] - 1)

    def enforce_cap(self) -> None:
        for (day_index, group), total in sorted(self.day.items()):
            current = total
            while current > self.cap:
                options = [
                    key
                    for key in self.slots
                    if key[0] == day_index
                    and any(g is group for g, _ in self.credits[key])
                    and self.sets[key] > self._bounds(self.slots[key].role)[0]
                ]
                if not options:
                    break
                key = max(options, key=lambda k: (self.slots[k].priority, self.sets[k], k))
                self._change(key, self.sets[key] - 1)
                current = self.day[(day_index, group)]

    def fill_deficit(self) -> None:
        for group in VolumeGroup:
            limit = self.targets[group].target - self.tolerance
            while self.week[group] < limit:
                options = [
                    key
                    for key in self.slots
                    if self._targets_group(key, group)
                    and self.sets[key] < self._bounds(self.slots[key].role)[1]
                    and self._fits_cap(key)
                ]
                if not options:
                    break
                key = min(options, key=lambda k: (self.slots[k].priority, self.sets[k], k))
                self._change(key, self.sets[key] + 1)


def allocate_sets(
    days: list[DaySpec],
    targets: dict[VolumeGroup, GroupTarget],
    goal: Goal,
    level: Experience,
    tables: Tables,
    *,
    circuit: bool,
) -> dict[SlotKey, int]:
    """Series por (día, slot) de la semana tipo.

    En circuitos (resistencia) todas las estaciones hacen las mismas rondas: se usan las
    series base sin reparto.
    """
    allocator = _Allocator(days, targets, goal, level, tables)
    if not circuit:
        allocator.reduce_overshoot()
        allocator.enforce_cap()
        allocator.fill_deficit()
    return dict(allocator.sets)


def enforce_session_cap(
    day: DraftDay, credits_of: Callable[[str], Credits], cap: float
) -> list[PlanWarning]:
    """Recorta series de los ejercicios elegidos si algún grupo supera el tope por sesión.

    El reparto del paso 4 usa créditos estimados por slot; tras elegir ejercicios (que pueden
    venir de una relajación con otro grupo objetivo) se vuelve a comprobar con los reales.
    """
    warnings: list[PlanWarning] = []
    for group in VolumeGroup:
        trimmed = False
        while True:
            entries = [
                (block, exercise, credit)
                for block in day.blocks
                if block.kind in {BlockKind.MAIN, BlockKind.CIRCUIT}
                for exercise in block.exercises
                for g, credit in credits_of(exercise.exercise_id)
                if g is group
            ]
            total = sum(exercise.sets * credit for _, exercise, credit in entries)
            options = [(b, e) for b, e, _ in entries if e.sets > 1]
            if total <= cap or not options:
                break
            block, exercise = max(options, key=_trim_order(day))
            _decrement(block, exercise)
            trimmed = True
        if trimmed:
            warnings.append(
                PlanWarning(
                    code=PlanWarningCode.SESSION_GROUP_CAP,
                    message_es=(
                        f"Hemos recortado series en «{day.name_es}» para no superar "
                        f"{number_es(cap)} series efectivas de un mismo grupo en una sesión."
                    ),
                    day_index=day.index,
                )
            )
    return warnings


def _trim_order(day: DraftDay) -> Callable[[tuple[DraftBlock, DraftExercise]], tuple[int, int]]:
    positions = {id(e): i for i, e in enumerate(day.working_exercises())}

    def key(item: tuple[DraftBlock, DraftExercise]) -> tuple[int, int]:
        return (item[1].priority, positions[id(item[1])])

    return key


def _decrement(block: DraftBlock, exercise: DraftExercise) -> None:
    if block.kind is BlockKind.CIRCUIT:
        block.rounds -= 1
        for member in block.exercises:
            member.sets = block.rounds
    else:
        exercise.sets -= 1

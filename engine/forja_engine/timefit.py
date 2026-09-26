"""Paso 7 (§7.2): estimar la duración de cada sesión y ajustarla al presupuesto.

Duración = calentamiento + Σ(series por (tiempo bajo tensión + descanso)) + transiciones
(60 s por ejercicio, 30 s en superseries y circuitos) + vuelta a la calma. En superseries el
descanso se cuenta una vez por ronda. Si la sesión excede ``session_minutes`` en más del 5 %:
(a) superseries de accesorios antagonistas, (b) quitar 1 serie a los accesorios (nunca por
debajo de 2: si no cabe, se quita el slot), (c) quitar slots de menor prioridad (el finisher
primero), (d) descansos de accesorios al mínimo de la tabla;
solo como último recurso se tocan los ``main``, y se avisa.
"""

import math
from collections.abc import Callable, Iterable

from forja_engine.draft import DraftBlock, DraftDay, DraftExercise, TimedBlock, TimedExercise
from forja_engine.models import (
    BlockKind,
    ExerciseRole,
    Mechanic,
    MovementPattern,
    PlanWarning,
    PlanWarningCode,
)
from forja_engine.tables import Tables, TimeModel
from forja_engine.texts import join_es
from forja_engine.volume import Credits, blocks_volume

SUPERSET_NOTE = (
    "Superserie: alterna con el otro ejercicio del bloque y descansa al acabar la ronda."
)


def seconds_per_rep(tempo: str | None, model: TimeModel) -> float:
    if tempo is None:
        return model.seconds_per_rep
    return float(sum(1 if part == "X" else int(part) for part in tempo.split("-")))


def work_seconds(exercise: TimedExercise, model: TimeModel) -> float:
    """Tiempo bajo tensión de una serie (duración o reps medias por segundos por rep)."""
    if exercise.duration_s is not None:
        seconds = float(exercise.duration_s)
    else:
        reps = ((exercise.rep_min or 0) + (exercise.rep_max or 0)) / 2
        seconds = reps * seconds_per_rep(exercise.tempo, model)
    return seconds * 2 if exercise.per_side else seconds


def block_seconds(block: TimedBlock, model: TimeModel) -> float:
    exercises = list(block.exercises)
    between = block.rest_between_rounds_s or 0
    if block.kind is BlockKind.WARMUP:
        return float(model.warmup_minutes * 60)
    if block.kind is BlockKind.COOLDOWN:
        return float(model.cooldown_minutes * 60)
    if block.kind is BlockKind.SUPERSET:
        work = sum(work_seconds(e, model) for e in exercises)
        return block.rounds * (work + between) + model.superset_transition_s * len(exercises)
    if block.kind is BlockKind.CIRCUIT:
        work = sum(work_seconds(e, model) + e.rest_s for e in exercises)
        return block.rounds * (work + between) + model.superset_transition_s * len(exercises)
    return sum(e.sets * (work_seconds(e, model) + e.rest_s) + model.transition_s for e in exercises)


def day_seconds(blocks: Iterable[TimedBlock], model: TimeModel) -> int:
    return math.ceil(sum(block_seconds(block, model) for block in blocks))


def limit_seconds(session_minutes: int, model: TimeModel) -> int:
    """Presupuesto con tolerancia, en minutos enteros para que ``estimated_minutes`` cumpla."""
    return math.floor(session_minutes * (1 + model.budget_tolerance)) * 60


def minutes_of(seconds: int) -> int:
    return max(1, math.ceil(seconds / 60))


# ----------------------------------------------------------------------- superseries
def pair_supersets(
    day: DraftDay,
    tables: Tables,
    credits_of: Callable[[str], Credits],
    *,
    antagonists_only: bool,
) -> bool:
    """Agrupa accesorios sueltos en superseries (antagonistas y, si se pide, no competidores)."""
    antagonists = {frozenset(pair) for pair in tables.engine_rules.antagonist_pairs}
    cap = tables.volume_targets.max_effective_sets_per_group_per_session
    changed = False
    position = 0
    while position < len(day.blocks):
        first = day.blocks[position]
        if _is_loose_accessory(first):
            for later in day.blocks[position + 1 :]:
                if _is_loose_accessory(later) and _can_pair(
                    first.exercises[0],
                    later.exercises[0],
                    antagonists,
                    antagonists_only=antagonists_only,
                ):
                    _merge(day, first, later, credits_of, cap)
                    changed = True
                    break
        position += 1
    return changed


def _is_loose_accessory(block: DraftBlock) -> bool:
    return block.kind is BlockKind.MAIN and block.exercises[0].rx_role is ExerciseRole.ACCESSORY


def _can_pair(
    a: DraftExercise,
    b: DraftExercise,
    antagonists: set[frozenset[MovementPattern]],
    *,
    antagonists_only: bool,
) -> bool:
    if frozenset({a.card.movement_pattern, b.card.movement_pattern}) in antagonists:
        return True
    return (
        not antagonists_only
        and a.slot is not None
        and b.slot is not None
        and a.slot.group is not b.slot.group
    )


def _merge(
    day: DraftDay,
    first: DraftBlock,
    second: DraftBlock,
    credits_of: Callable[[str], Credits],
    cap: float,
) -> None:
    a, b = first.exercises[0], second.exercises[0]
    day.blocks.remove(second)
    first.kind = BlockKind.SUPERSET
    first.exercises = [a, b]
    low, high = sorted((a.sets, b.sets))
    first.rounds = a.sets = b.sets = high
    if any(sets > cap for sets in blocks_volume(day.blocks, credits_of).values()):
        first.rounds = a.sets = b.sets = low
    first.rest_between_rounds_s = max(a.rest_s, b.rest_s)
    for exercise in (a, b):
        exercise.notes_es = SUPERSET_NOTE


# ------------------------------------------------------------------------ ajuste
class _Fitter:
    def __init__(
        self,
        day: DraftDay,
        session_minutes: int,
        tables: Tables,
        credits_of: Callable[[str], Credits],
    ) -> None:
        self.day = day
        self.tables = tables
        self.model = tables.prescription.time_model
        self.limit = limit_seconds(session_minutes, self.model)
        self.credits_of = credits_of
        self.dropped: list[str] = []
        self.trimmed_main = False
        self.session_minutes = session_minutes
        self.min_sets = tables.engine_rules.allocation.min_sets_per_exercise

    def over(self) -> bool:
        return day_seconds(self.day.blocks, self.model) > self.limit

    def working(self) -> list[tuple[DraftBlock, DraftExercise]]:
        return [
            (block, exercise)
            for block in self.day.blocks
            if block.kind in {BlockKind.MAIN, BlockKind.SUPERSET, BlockKind.CIRCUIT}
            for exercise in block.exercises
        ]

    def trim_accessory_sets(self) -> None:
        for block in self.day.blocks:
            if (
                block.kind is BlockKind.MAIN
                and block.exercises[0].rx_role is ExerciseRole.ACCESSORY
            ):
                block.exercises[0].sets = max(self.min_sets, block.exercises[0].sets - 1)
            elif block.kind is BlockKind.SUPERSET and block.rounds > self.min_sets:
                block.rounds -= 1
                for exercise in block.exercises:
                    exercise.sets = block.rounds

    def drop_low_priority(self) -> None:
        while self.over():
            finisher = next((b for b in self.day.blocks if b.kind is BlockKind.FINISHER), None)
            if finisher is not None:
                self.day.blocks.remove(finisher)
                self.dropped.append("el finisher de cardio")
                continue
            working = self.working()
            candidates = [
                (index, block, exercise)
                for index, (block, exercise) in enumerate(working)
                if exercise.rx_role is not ExerciseRole.MAIN
            ]
            if not candidates or len(working) == 1:
                return
            _, block, exercise = max(candidates, key=lambda item: (item[2].priority, item[0]))
            self._remove(block, exercise)
            self.dropped.append(f"«{exercise.card.name_es}»")

    def _remove(self, block: DraftBlock, exercise: DraftExercise) -> None:
        block.exercises.remove(exercise)
        if not block.exercises:
            self.day.blocks.remove(block)
        elif block.kind is BlockKind.SUPERSET:
            block.kind = BlockKind.MAIN
            block.rounds = 1
            block.rest_between_rounds_s = None
            block.exercises[0].notes_es = None

    def reduce_accessory_rests(self) -> None:
        for block, exercise in self.working():
            if exercise.rx_role is not ExerciseRole.MAIN:
                exercise.rest_s = exercise.rest_floor_s
                if block.kind is BlockKind.SUPERSET:
                    block.rest_between_rounds_s = max(e.rest_s for e in block.exercises)

    def trim_mains(self) -> None:
        steps: list[Callable[[], bool]] = [
            lambda: self._main_sets(self.min_sets),
            self._main_rests,
            self._circuit_rounds,
            self._drop_main,
        ]
        for step in steps:
            while self.over() and step():
                self.trimmed_main = True

    def _mains(self) -> list[tuple[DraftBlock, DraftExercise]]:
        return [(b, e) for b, e in self.working() if e.rx_role is ExerciseRole.MAIN]

    def _main_sets(self, low: int) -> bool:
        options = [(b, e) for b, e in self._mains() if b.kind is BlockKind.MAIN and e.sets > low]
        if not options:
            return False
        options[-1][1].sets -= 1
        return True

    def _main_rests(self) -> bool:
        options = [(b, e) for b, e in self._mains() if e.rest_s > e.rest_floor_s]
        for _, exercise in options:
            exercise.rest_s = exercise.rest_floor_s
        return bool(options)

    def _circuit_rounds(self) -> bool:
        for block in self.day.blocks:
            if block.kind is BlockKind.CIRCUIT and block.rounds > 1:
                block.rounds -= 1
                for exercise in block.exercises:
                    exercise.sets = block.rounds
                return True
        return False

    def _drop_main(self) -> bool:
        working = self.working()
        if len(working) <= 1:
            return False
        block, exercise = working[-1]
        self._remove(block, exercise)
        self.dropped.append(f"«{exercise.card.name_es}»")
        return True

    def run(self) -> list[PlanWarning]:
        if self.over():
            pair_supersets(self.day, self.tables, self.credits_of, antagonists_only=True)
        if self.over():
            self.trim_accessory_sets()
        self.drop_low_priority()
        if self.over():
            self.reduce_accessory_rests()
        if self.over():
            self.trim_mains()
        return self.warnings()

    def warnings(self) -> list[PlanWarning]:
        name = self.day.name_es
        result: list[PlanWarning] = []
        if self.dropped:
            result.append(
                PlanWarning(
                    code=PlanWarningCode.SLOT_DROPPED,
                    message_es=(
                        f"Para ajustar «{name}» a {self.session_minutes} minutos hemos quitado "
                        f"{join_es(self.dropped)}."
                    ),
                    day_index=self.day.index,
                )
            )
        if self.trimmed_main:
            result.append(
                PlanWarning(
                    code=PlanWarningCode.MAIN_EXERCISE_TRIMMED,
                    message_es=(
                        f"El tiempo de «{name}» es muy justo: hemos tenido que recortar series o "
                        "descansos de los ejercicios principales."
                    ),
                    day_index=self.day.index,
                )
            )
        if self.over():
            minutes = minutes_of(day_seconds(self.day.blocks, self.model))
            result.append(
                PlanWarning(
                    code=PlanWarningCode.TIME_BUDGET_EXCEEDED,
                    message_es=(
                        f"«{name}» dura unos {minutes} minutos, más de los {self.session_minutes} "
                        "que tienes: considera más tiempo por sesión o más días."
                    ),
                    day_index=self.day.index,
                )
            )
        return result


def order_working_blocks(day: DraftDay) -> None:
    """Compuestos en series rectas primero y después los aislamientos y superseries (C6).

    Solo se reordenan los bloques de trabajo entre sí (orden estable); calentamiento, finisher
    y vuelta a la calma conservan su posición.
    """
    positions = [i for i, b in enumerate(day.blocks) if b.kind in _ORDERED_KINDS]
    ordered = sorted(
        (day.blocks[i] for i in positions),
        key=lambda b: any(e.card.mechanic is Mechanic.ISOLATION for e in b.exercises),
    )
    for position, block in zip(positions, ordered, strict=True):
        day.blocks[position] = block


_ORDERED_KINDS = frozenset({BlockKind.MAIN, BlockKind.SUPERSET})


def fit_day(
    day: DraftDay, session_minutes: int, tables: Tables, credits_of: Callable[[str], Credits]
) -> list[PlanWarning]:
    """Ajusta ``day`` al presupuesto (in situ) y devuelve los avisos generados."""
    return _Fitter(day, session_minutes, tables, credits_of).run()

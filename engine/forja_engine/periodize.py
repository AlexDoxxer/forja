"""Paso 8 (§7.2): periodizar el mesociclo a partir de la semana tipo.

- Acumulación: RIR según ``rir_by_week`` acotado al rango de cada rol y +1 serie por grupo y
  semana (acumulativa) mientras quepa en el tope semanal, en 10 series/grupo/sesión y en el
  presupuesto de tiempo. Principiantes: progresión lineal, sin series extra ni ondulación.
- Descarga (última semana): ``volume_ratio`` de las series, RIR fijo y cargas al 90 %.
- Fuerza (intermedio/avanzado): ondulación diaria pesado/medio en los ``main``; las semanas
  con RIR ≤ 1 se marcan como ``intensification``.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from forja_engine.allocate import role_bounds
from forja_engine.draft import DraftDay, DraftExercise
from forja_engine.models import (
    BlockKind,
    ExerciseRole,
    Experience,
    GeneratorInput,
    Goal,
    VolumeGroup,
    WeekPhase,
)
from forja_engine.prescribe import clamp, load_hint, working_rir
from forja_engine.tables import Tables
from forja_engine.timefit import day_seconds, limit_seconds
from forja_engine.volume import Credits, GroupTarget, blocks_volume

SLOTTED_ROLES = frozenset({ExerciseRole.MAIN, ExerciseRole.ACCESSORY, ExerciseRole.CORE})
INTENSIFICATION_RIR = 1
MAX_RIR = 5


@dataclass
class WeekDraft:
    index: int
    phase: WeekPhase
    target_rir: int
    days: list[DraftDay]


def undulation_enabled(inp: GeneratorInput, tables: Tables) -> bool:
    return (
        inp.goal is Goal.STRENGTH
        and inp.experience in tables.periodization.strength_undulation.enabled_for
    )


def linear_beginner(inp: GeneratorInput, tables: Tables) -> bool:
    return inp.experience is Experience.BEGINNER and tables.periodization.beginner_linear


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


class _Periodizer:
    def __init__(
        self,
        base: list[DraftDay],
        inp: GeneratorInput,
        tables: Tables,
        targets: dict[VolumeGroup, GroupTarget],
        credits_of: Callable[[str], Credits],
    ) -> None:
        self.base = base
        self.inp = inp
        self.tables = tables
        self.targets = targets
        self.credits_of = credits_of
        self.periodization = tables.periodization
        self.model = tables.prescription.time_model
        self.limit = limit_seconds(inp.session_minutes, self.model)
        self.cap = tables.volume_targets.max_effective_sets_per_group_per_session
        self.target_credit = tables.volume_targets.set_credit.target
        training = [d.index for d in base if not d.is_recovery]
        self.heavy_days = {index for n, index in enumerate(training) if n % 2 == 0}

    # ----------------------------------------------------------- series extra
    def add_extra_sets(self, days: list[DraftDay]) -> None:
        accumulation = self.periodization.phases.accumulation
        for group in VolumeGroup:
            ceiling = self.targets[group].target_max * accumulation.cap_ratio_of_max
            for _ in range(accumulation.extra_sets_per_group_per_week):
                weekly = sum(
                    blocks_volume(day.blocks, self.credits_of).get(group, 0.0) for day in days
                )
                options: list[tuple[tuple[int, int, int, int], DraftDay, DraftExercise]] = []
                for day in days:
                    for position, block in enumerate(day.blocks):
                        exercise = block.exercises[0]
                        if (
                            block.kind is BlockKind.MAIN
                            and exercise.rx_role in SLOTTED_ROLES
                            and (group, self.target_credit) in self.credits_of(exercise.exercise_id)
                            and exercise.sets < role_bounds(exercise.rx_role, self.tables)[1]
                            and weekly + self.target_credit <= ceiling
                            and self._fits(day, exercise)
                        ):
                            key = (exercise.priority, exercise.sets, day.index, position)
                            options.append((key, day, exercise))
                if not options:
                    break
                _, _, exercise = min(options, key=lambda item: item[0])
                exercise.sets += 1

    def _fits(self, day: DraftDay, exercise: DraftExercise) -> bool:
        exercise.sets += 1
        volume = blocks_volume(day.blocks, self.credits_of)
        fits = (
            all(sets <= self.cap for sets in volume.values())
            and day_seconds(day.blocks, self.model) <= self.limit
        )
        exercise.sets -= 1
        return fits

    # ------------------------------------------------------------- semana concreta
    def build_week(self, index: int, source: list[DraftDay], *, deload: bool) -> WeekDraft:
        phases = self.periodization.phases
        raw_rir = phases.accumulation.rir_by_week[
            min(index, len(phases.accumulation.rir_by_week) - 1)
        ]
        delta = self.tables.prescription.experience_adjustments[self.inp.experience].rir_delta
        undulating = undulation_enabled(self.inp, self.tables)
        days = [day.clone() for day in source]
        for day in days:
            for block in day.blocks:
                for exercise in block.exercises:
                    if exercise.slot is None or exercise.rx_role not in SLOTTED_ROLES:
                        continue
                    if deload:
                        self._deload_exercise(exercise)
                    else:
                        self._accumulate_exercise(
                            exercise, raw_rir, day.index, undulating=undulating
                        )
                if deload and block.kind in {BlockKind.SUPERSET, BlockKind.CIRCUIT}:
                    block.rounds = max(1, _round_half_up(block.rounds * phases.deload.volume_ratio))
                    for exercise in block.exercises:
                        exercise.sets = block.rounds
        if deload:
            phase, week_rir = WeekPhase.DELOAD, phases.deload.rir
        else:
            week_rir = clamp(raw_rir + delta, 0, MAX_RIR)
            intense = undulating and raw_rir <= INTENSIFICATION_RIR
            phase = WeekPhase.INTENSIFICATION if intense else WeekPhase.ACCUMULATION
        return WeekDraft(index=index, phase=phase, target_rir=week_rir, days=days)

    def _deload_exercise(self, exercise: DraftExercise) -> None:
        deload = self.periodization.phases.deload
        exercise.sets = max(1, _round_half_up(exercise.sets * deload.volume_ratio))
        exercise.target_rir = deload.rir
        percent = round(deload.load_ratio * 100)
        exercise.load_hint = (
            f"Semana de descarga: usa el {percent} % de tu carga habitual y deja "
            f"{deload.rir} repeticiones en reserva"
        )

    def _accumulate_exercise(
        self, exercise: DraftExercise, raw_rir: int, day_index: int, *, undulating: bool
    ) -> None:
        rir = working_rir(self.inp, exercise.rx_role, raw_rir, self.tables)
        if undulating and exercise.rx_role is ExerciseRole.MAIN:
            undulation = self.periodization.strength_undulation
            heavy = day_index in self.heavy_days
            day_rule = undulation.heavy_day if heavy else undulation.medium_day
            rir = max(day_rule.rir, rir)
            if exercise.rep_min is not None and exercise.rep_max is not None:
                exercise.rep_min = max(1, exercise.rep_min + day_rule.reps_shift)
                exercise.rep_max = max(exercise.rep_min, exercise.rep_max + day_rule.reps_shift)
            exercise.notes_es = (
                "Día pesado: menos repeticiones y más carga."
                if heavy
                else "Día medio: carga moderada y técnica impecable."
            )
        exercise.target_rir = rir
        exercise.load_hint = load_hint(exercise.card, rir)

    def run(self) -> list[WeekDraft]:
        weeks: list[WeekDraft] = []
        state = [day.clone() for day in self.base]
        grow = not linear_beginner(self.inp, self.tables)
        for index in range(self.inp.weeks):
            deload = index == self.inp.weeks - 1
            if deload:
                weeks.append(self.build_week(index, self.base, deload=True))
                continue
            if index > 0 and grow:
                self.add_extra_sets(state)
            weeks.append(self.build_week(index, state, deload=False))
        return weeks


def periodize(
    base: list[DraftDay],
    inp: GeneratorInput,
    tables: Tables,
    targets: dict[VolumeGroup, GroupTarget],
    credits_of: Callable[[str], Credits],
) -> list[WeekDraft]:
    """Semanas del mesociclo (la última, de descarga)."""
    return _Periodizer(base, inp, tables, targets, credits_of).run()


def periodization_rationale(inp: GeneratorInput, tables: Tables) -> str:
    deload = tables.periodization.phases.deload
    accumulation = inp.weeks - 1
    text = (
        f"El mesociclo dura {inp.weeks} semanas: {accumulation} de acumulación, en las que las "
        "repeticiones en reserva bajan poco a poco, y una última de descarga con el "
        f"{round(deload.volume_ratio * 100)} % de las series para recuperarte."
    )
    if linear_beginner(inp, tables):
        text += (
            " Como estás empezando, la progresión es lineal: mismas series y un poco más de "
            "carga o repeticiones cada semana."
        )
    else:
        text += (
            " Cada semana de acumulación suma una serie por grupo muscular mientras haya margen."
        )
    if undulation_enabled(inp, tables):
        text += (
            " Alternamos días pesados (menos repeticiones, más carga) y medios en los ejercicios "
            "principales."
        )
    return text

"""Paso 9 (§7.2): componer los DTOs inmutables del plan, resumen de volumen y avisos."""

from collections.abc import Callable, Iterable, Sequence

from forja_engine.draft import DraftBlock, DraftDay, TimedBlock
from forja_engine.models import (
    BlockKind,
    ExerciseRole,
    GeneratorInput,
    GroupSets,
    GroupVolume,
    PlanBlock,
    PlanDay,
    PlanExercise,
    PlanWarning,
    PlanWarningCode,
    VolumeGroup,
)
from forja_engine.tables import Tables
from forja_engine.texts import GOAL_ES, join_es, number_es, seconds_es
from forja_engine.timefit import day_seconds, minutes_of
from forja_engine.volume import Credits, GroupTarget, blocks_volume, ordered_volume

MAX_SESSION_SETS = 10.0
MAX_VOLUME_RATIO = 2.0
MIN_VOLUME_RATIO = 0.01


def day_volume(
    blocks: Iterable[TimedBlock], credits_of: Callable[[str], Credits]
) -> tuple[GroupSets, ...]:
    """Series efectivas por grupo de una sesión (acotadas a 10 en el DTO; ``validate_plan``
    informa de cualquier exceso)."""
    return tuple(
        GroupSets(group=group, sets=min(round(sets, 2), MAX_SESSION_SETS))
        for group, sets in ordered_volume(blocks_volume(blocks, credits_of))
    )


def day_focus(day: DraftDay, tables: Tables) -> str:
    """Foco legible del día a partir de los grupos de sus slots de trabajo."""
    if day.is_recovery:
        return "Cardio suave y movilidad para recuperar"
    names = tables.engine_rules.group_names_es
    groups = list(
        dict.fromkeys(names[e.slot.group] for e in day.working_exercises() if e.slot is not None)
    )
    return f"Trabajo de {join_es(groups[:4])}" if groups else "Sesión adaptada a tu equipamiento"


def _block(order: int, block: DraftBlock) -> PlanBlock:
    return PlanBlock(
        order=order,
        kind=block.kind,
        rounds=block.rounds,
        rest_between_rounds_s=block.rest_between_rounds_s,
        exercises=tuple(
            PlanExercise(
                order=position,
                slot=exercise.slot,
                exercise_id=exercise.card.id,
                sets=exercise.sets,
                rep_min=exercise.rep_min,
                rep_max=exercise.rep_max,
                duration_s=exercise.duration_s,
                per_side=exercise.per_side,
                target_rir=exercise.target_rir,
                tempo=exercise.tempo,
                rest_s=exercise.rest_s,
                load_hint=exercise.load_hint,
                notes_es=exercise.notes_es,
                alternatives=exercise.alternatives,
            )
            for position, exercise in enumerate(block.exercises)
        ),
    )


def to_plan_day(day: DraftDay, tables: Tables, credits_of: Callable[[str], Credits]) -> PlanDay:
    model = tables.prescription.time_model
    return PlanDay(
        index=day.index,
        template=day.template,
        name_es=day.name_es,
        focus_es=day.focus_es,
        weekday=day.weekday,
        is_recovery=day.is_recovery,
        estimated_minutes=minutes_of(day_seconds(day.blocks, model)),
        blocks=tuple(_block(order, block) for order, block in enumerate(day.blocks)),
        volume=day_volume(day.blocks, credits_of),
    )


def week_totals(days: Sequence[PlanDay]) -> dict[VolumeGroup, float]:
    totals: dict[VolumeGroup, float] = {}
    for day in days:
        for entry in day.volume:
            totals[entry.group] = totals.get(entry.group, 0.0) + entry.sets
    return totals


def volume_ratio(days: Sequence[PlanDay], base: Sequence[PlanDay]) -> float:
    base_total = sum(week_totals(base).values())
    if base_total == 0:
        return 1.0
    ratio = sum(week_totals(days).values()) / base_total
    return round(min(MAX_VOLUME_RATIO, max(MIN_VOLUME_RATIO, ratio)), 2)


def weekly_volume(
    base: Sequence[PlanDay], targets: dict[VolumeGroup, GroupTarget]
) -> tuple[GroupVolume, ...]:
    totals = week_totals(base)
    return tuple(
        GroupVolume(
            group=group,
            target_min=targets[group].target_min,
            target_max=targets[group].target_max,
            planned_sets=round(totals.get(group, 0.0), 2),
        )
        for group in VolumeGroup
    )


def volume_warnings(
    volume: Sequence[GroupVolume], targets: dict[VolumeGroup, GroupTarget], tables: Tables
) -> list[PlanWarning]:
    """Aviso por grupo cuyo volumen semanal se aleja más de ±15 % del objetivo."""
    ratio = tables.engine_rules.allocation.volume_warning_ratio
    names = {g.value: n for g, n in tables.engine_rules.group_names_es.items()}
    warnings: list[PlanWarning] = []
    for entry in volume:
        target = targets[entry.group].target
        if abs(entry.planned_sets - target) <= ratio * target:
            continue
        direction = "por debajo" if entry.planned_sets < target else "por encima"
        hint = (
            "Más días o más tiempo por sesión permitirían acercarse."
            if entry.planned_sets < target
            else "Proviene sobre todo del trabajo indirecto de los ejercicios compuestos."
        )
        warnings.append(
            PlanWarning(
                code=PlanWarningCode.VOLUME_OUT_OF_RANGE,
                message_es=(
                    f"Volumen semanal de {names[entry.group.value]}: "
                    f"{number_es(entry.planned_sets)} "
                    f"series efectivas, {direction} del objetivo de {number_es(target)}. {hint}"
                ),
            )
        )
    return warnings


def dedupe(warnings: Iterable[PlanWarning]) -> tuple[PlanWarning, ...]:
    seen: set[PlanWarning] = set()
    result: list[PlanWarning] = []
    for warning in warnings:
        if warning not in seen:
            seen.add(warning)
            result.append(warning)
    return tuple(result)


def prescription_rationale(inp: GeneratorInput, tables: Tables) -> str:
    """Resumen de la prescripción de los ejercicios principales para el objetivo."""
    main = tables.prescription.table[inp.goal]["main"]
    low, high = main.rest_s
    text = (
        f"Para {GOAL_ES[inp.goal]}, los ejercicios principales van a {main.reps[0]}-{main.reps[1]} "
        f"repeticiones con {seconds_es(low)}-{seconds_es(high)} de descanso y dejando algunas "
        "repeticiones en reserva; los accesorios usan rangos algo más altos."
    )
    if main.format == "circuit":
        text += " Los ejercicios se encadenan en circuito con descansos cortos entre estaciones."
    if tables.prescription.table[inp.goal]["accessory"].prefer_supersets:
        text += " Agrupamos accesorios en superseries para ganar densidad."
    return text


def sex_rationale(inp: GeneratorInput, tables: Tables) -> str:
    return (
        f"{tables.sex_modifiers.explanation_es[inp.sex]} El sexo nunca excluye ejercicios ni "
        "limita las cargas."
    )


def time_rationale(inp: GeneratorInput) -> str:
    extras: list[str] = []
    if inp.include_warmup:
        extras.append("calentamiento")
    if inp.include_cooldown:
        extras.append("vuelta a la calma")
    if inp.include_cardio_finisher:
        extras.append("un finisher de cardio")
    included = f", incluyendo {join_es(extras)}" if extras else ""
    return f"Cada sesión está ajustada a unos {inp.session_minutes} minutos{included}."


def recovery_block_kind(role: ExerciseRole) -> BlockKind:
    return BlockKind.COOLDOWN if role is ExerciseRole.MOBILITY else BlockKind.MAIN

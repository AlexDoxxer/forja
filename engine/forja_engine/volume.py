"""Paso 3 (§7.2): volumen semanal objetivo por grupo y cómputo de series efectivas.

Una serie de un ejercicio cuenta ``set_credit.target`` (1,0) para el grupo de su músculo
objetivo y, si es compuesto, ``set_credit.relevant_secondary`` (0,5) para los grupos
secundarios relevantes de su patrón (``engine-rules.yaml#compound_secondary_groups``).
Serie efectiva = serie de trabajo con RIR ≤ 4 (glosario).
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from forja_engine.draft import TimedBlock
from forja_engine.models import (
    WORKING_BLOCKS,
    Emphasis,
    ExerciseCard,
    GeneratorInput,
    Mechanic,
    MovementPattern,
    MuscleGroup,
    SlotRef,
    VolumeGroup,
)
from forja_engine.tables import VOLUME_GROUP_VALUES, Tables
from forja_engine.texts import EMPHASIS_ES, join_es

EFFECTIVE_RIR_MAX = 4
COMPOUND_PATTERNS = frozenset(
    {
        MovementPattern.SQUAT,
        MovementPattern.LUNGE,
        MovementPattern.HINGE,
        MovementPattern.HORIZONTAL_PUSH,
        MovementPattern.VERTICAL_PUSH,
        MovementPattern.HORIZONTAL_PULL,
        MovementPattern.VERTICAL_PULL,
    }
)
"""Patrones de los compuestos cuyo grupo de entrenamiento es el del patrón (B1)."""

Credits = tuple[tuple[VolumeGroup, float], ...]


@dataclass(frozen=True)
class GroupTarget:
    """Rango semanal ajustado por énfasis y punto objetivo al que apunta el reparto."""

    group: VolumeGroup
    target_min: float
    target_max: float
    target: float


def weekly_targets(inp: GeneratorInput, tables: Tables) -> dict[VolumeGroup, GroupTarget]:
    """Objetivo por grupo: punto medio por multiplicador de énfasis, con suelo de mantenimiento.

    El sexo no modifica el volumen (``sex-modifiers.yaml`` solo ajusta descansos, reps de
    aislamiento y demostrador).
    """
    volume = tables.volume_targets
    targets: dict[VolumeGroup, GroupTarget] = {}
    for group in VolumeGroup:
        low, high = volume.target_range(inp.goal, inp.experience, group)
        factor = volume.multiplier(inp.emphasis, group)
        floor = low * volume.maintenance_floor_ratio
        target = max((low + high) / 2 * factor, floor)
        targets[group] = GroupTarget(
            group=group,
            target_min=round(max(low * factor, floor), 2),
            target_max=round(max(high * factor, floor), 2),
            target=round(target, 2),
        )
    return targets


def emphasis_rationale(inp: GeneratorInput, tables: Tables) -> str | None:
    """Frase sobre el énfasis (``None`` si es equilibrado)."""
    if inp.emphasis is Emphasis.BALANCED:
        return None
    names = tables.engine_rules.group_names_es
    boosted = [
        names[MuscleGroup(group.value)]
        for group in VolumeGroup
        if tables.volume_targets.multiplier(inp.emphasis, group) > 1
    ]
    return (
        f"Por el énfasis en {EMPHASIS_ES[inp.emphasis]} hemos dado más volumen a "
        f"{join_es(boosted)}, manteniendo el resto por encima de su mínimo de mantenimiento."
    )


def training_group(card: ExerciseCard, tables: Tables) -> MuscleGroup:
    """Grupo que entrena ``card`` a efectos de selección y volumen.

    En los compuestos de patrón principal es el grupo del patrón (sentadilla → cuádriceps,
    bisagra → isquiotibiales…) aunque el dataset marque otro ``target_muscle`` (p. ej. glúteos);
    en el resto (aislamientos) sigue siendo el del músculo objetivo (B1).
    """
    if card.mechanic is Mechanic.COMPOUND and card.movement_pattern in COMPOUND_PATTERNS:
        return tables.engine_rules.pattern_groups[card.movement_pattern]
    return tables.muscle_group(card.target_muscle)


def card_credits(card: ExerciseCard, tables: Tables) -> Credits:
    """Créditos de volumen de una serie de ``card``."""
    volume = tables.volume_targets
    group = training_group(card, tables).value
    target = VolumeGroup(group) if group in VOLUME_GROUP_VALUES else None
    result: dict[VolumeGroup, float] = {}
    if target is not None:
        result[target] = volume.set_credit.target
    if card.mechanic is Mechanic.COMPOUND:
        for secondary in tables.engine_rules.compound_secondary_groups.get(
            card.movement_pattern, ()
        ):
            if secondary is not target:
                result[secondary] = volume.secondary_credit(secondary)
    return tuple(result.items())


def slot_credits(slot: SlotRef, tables: Tables) -> Credits:
    """Créditos estimados de un slot antes de elegir ejercicio (paso 4)."""
    volume = tables.volume_targets
    result: dict[VolumeGroup, float] = {}
    target = VolumeGroup(slot.group.value) if slot.group.value in VOLUME_GROUP_VALUES else None
    if target is not None:
        result[target] = volume.set_credit.target
    for group in tables.engine_rules.compound_secondary_groups.get(slot.pattern, ()):
        if group is not target:
            result[group] = volume.secondary_credit(group)
    return tuple(result.items())


def is_effective(target_rir: int | None) -> bool:
    return target_rir is None or target_rir <= EFFECTIVE_RIR_MAX


def blocks_volume(
    blocks: Iterable[TimedBlock], credits_of: Callable[[str], Credits]
) -> dict[VolumeGroup, float]:
    """Series efectivas por grupo de los bloques de trabajo de una sesión."""
    totals: dict[VolumeGroup, float] = {}
    for block in blocks:
        if block.kind not in WORKING_BLOCKS:
            continue
        for exercise in block.exercises:
            if not is_effective(exercise.target_rir):
                continue
            for group, credit in credits_of(exercise.exercise_id):
                totals[group] = totals.get(group, 0.0) + credit * exercise.sets
    return totals


def ordered_volume(totals: Mapping[VolumeGroup, float]) -> list[tuple[VolumeGroup, float]]:
    """Grupos con series > 0 en el orden de ``VolumeGroup``."""
    return [(group, totals[group]) for group in VolumeGroup if totals.get(group, 0.0) > 0]

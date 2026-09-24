"""Progresión dentro de la app (§7.6): doble progresión, e1RM y series de aproximación.

Todas las sugerencias son informativas: el usuario siempre confirma. Ninguna función recibe
el sexo del usuario: las cargas nunca se limitan por sexo.
"""

import math
from collections.abc import Sequence

from forja_engine.models import (
    BodyPart,
    EquipmentCode,
    ExerciseCard,
    ExerciseHistoryEntry,
    ExercisePrescription,
    Goal,
    LoadType,
    Mechanic,
    PerformedSet,
    ProgressionSuggestion,
    SuggestionKind,
    WarmupSet,
)
from forja_engine.tables import Tables, default_tables
from forja_engine.texts import number_es, reps_in_reserve_es

EPLEY_MAX_REPS = 10
LOWER_BODY = frozenset({BodyPart.UPPER_LEGS, BodyPart.LOWER_LEGS})


def estimate_1rm(weight_kg: float, reps: int, rir: int = 0) -> float | None:
    """e1RM de Epley ``w·(1 + r/30)`` con reps efectivas = reps + RIR (solo si ≤ 10)."""
    effective = reps + rir
    if weight_kg <= 0 or reps < 1 or effective > EPLEY_MAX_REPS:
        return None
    return round(weight_kg * (1 + effective / 30), 2)


def plates_per_side(weight_kg: float, tables: Tables) -> tuple[float, ...]:
    """Discos por lado (de mayor a menor) para cargar ``weight_kg`` sobre la barra."""
    progression = tables.periodization.progression
    remaining = round((weight_kg - progression.bar_kg) / 2, 2)
    plates: list[float] = []
    for plate in sorted(progression.plates_kg, reverse=True):
        while remaining >= plate - 1e-9:
            plates.append(plate)
            remaining = round(remaining - plate, 2)
    return tuple(plates)


def round_load(
    target_kg: float, equipment: EquipmentCode, tables: Tables
) -> tuple[float, tuple[float, ...]]:
    """Carga disponible más cercana y, si va con discos, los discos por lado."""
    loads = tables.engine_rules.progression_loads
    if equipment in loads.plate_loaded:
        progression = tables.periodization.progression
        smallest = min(progression.plates_kg)
        if target_kg <= progression.bar_kg:
            return progression.bar_kg, ()
        per_side = math.floor((target_kg - progression.bar_kg) / 2 / smallest + 0.5) * smallest
        weight = round(progression.bar_kg + 2 * per_side, 2)
        return weight, plates_per_side(weight, tables)
    step = loads.step_for(equipment)
    return round(max(step, math.floor(target_kg / step + 0.5) * step), 2), ()


def warmup_ramp(
    work_weight_kg: float,
    load_type: LoadType,
    equipment: EquipmentCode,
    tables: Tables | None = None,
) -> tuple[WarmupSet, ...]:
    """Aproximación (40 % por 8, 60 % por 5, 80 % por 2) redondeada a la carga disponible."""
    tables = tables or default_tables()
    if load_type is not LoadType.EXTERNAL or work_weight_kg <= 0:
        return ()
    ramp: list[WarmupSet] = []
    for percent, reps in tables.periodization.progression.warmup_ramp:
        weight, plates = round_load(work_weight_kg * percent, equipment, tables)
        ramp.append(
            WarmupSet(percent=percent, reps=reps, weight_kg=weight, plates_per_side_kg=plates)
        )
    return tuple(ramp)


def harder_variant(card: ExerciseCard, catalog: Sequence[ExerciseCard]) -> ExerciseCard | None:
    """Variante más difícil del mismo patrón y equipamiento (la menos difícil de las que hay)."""
    options = [
        other
        for other in catalog
        if other.movement_pattern is card.movement_pattern
        and other.equipment_code is card.equipment_code
        and other.variant_group != card.variant_group
        and other.difficulty > card.difficulty
        and not other.deprecated
    ]
    return min(options, key=lambda c: (c.difficulty, c.id)) if options else None


def _increment(card: ExerciseCard, tables: Tables) -> float:
    progression = tables.periodization.progression
    if card.equipment_code in {EquipmentCode.DUMBBELL, EquipmentCode.KETTLEBELL}:
        return tables.engine_rules.progression_loads.step_for(card.equipment_code)
    if card.mechanic is Mechanic.ISOLATION:
        return progression.isolation_kg
    if card.body_part in LOWER_BODY:
        return progression.lower_compound_kg
    return progression.upper_compound_kg


def _work_sets(entry: ExerciseHistoryEntry) -> list[PerformedSet]:
    return [s for s in entry.sets if not s.is_warmup]


def _suggestion(
    kind: SuggestionKind,
    reason: str,
    *,
    weight: float | None = None,
    plates: tuple[float, ...] = (),
    reps: tuple[int, int] | None = None,
    exercise_id: str | None = None,
    warmup: tuple[WarmupSet, ...] = (),
) -> ProgressionSuggestion:
    return ProgressionSuggestion(
        kind=kind,
        suggested_weight_kg=weight,
        suggested_rep_min=reps[0] if reps else None,
        suggested_rep_max=reps[1] if reps else None,
        suggested_exercise_id=exercise_id,
        plates_per_side_kg=plates,
        reason_es=reason,
        warmup_sets=warmup,
    )


def _timed(
    prescription: ExercisePrescription,
    card: ExerciseCard,
    last: list[PerformedSet],
    catalog: Sequence[ExerciseCard],
    tables: Tables,
) -> ProgressionSuggestion:
    target = prescription.duration_s or 0
    completed = all((s.duration_s or 0) >= target for s in last)
    if not completed:
        return _suggestion(
            SuggestionKind.HOLD,
            f"Mantén {target} s por serie hasta completarlos en todas las series.",
        )
    harder = harder_variant(card, catalog)
    if harder is not None:
        return _suggestion(
            SuggestionKind.HARDER_VARIANT,
            f"Completaste los {target} s en todas las series: prueba «{harder.name_es}».",
            exercise_id=harder.id,
        )
    step = tables.engine_rules.progression_loads.time_step_s
    return _suggestion(
        SuggestionKind.HOLD,
        f"Completaste los {target} s en todas las series: suma {step} s cuando te sientas cómodo.",
    )


def _bodyweight(
    card: ExerciseCard,
    reps: tuple[int, int],
    catalog: Sequence[ExerciseCard],
    tables: Tables,
    *,
    top_reached: bool,
) -> ProgressionSuggestion:
    rep_min, rep_max = reps
    return _bodyweight_rules(card, rep_min, rep_max, catalog, tables, top_reached=top_reached)


def _bodyweight_rules(
    card: ExerciseCard,
    rep_min: int,
    rep_max: int,
    catalog: Sequence[ExerciseCard],
    tables: Tables,
    *,
    top_reached: bool,
) -> ProgressionSuggestion:
    loads = tables.engine_rules.progression_loads
    if not top_reached:
        return _suggestion(
            SuggestionKind.HOLD,
            f"Sigue con {rep_min}-{rep_max} repeticiones hasta llegar a {rep_max} en todas las "
            "series.",
        )
    if rep_max + loads.bodyweight_rep_step <= loads.bodyweight_rep_cap:
        new = (rep_min + loads.bodyweight_rep_step, rep_max + loads.bodyweight_rep_step)
        return _suggestion(
            SuggestionKind.INCREASE_REPS,
            f"Llegaste a {rep_max} repeticiones en todas las series: sube a {new[0]}-{new[1]}.",
            reps=new,
        )
    harder = harder_variant(card, catalog)
    if harder is not None:
        return _suggestion(
            SuggestionKind.HARDER_VARIANT,
            f"Ya haces muchas repeticiones: pasa a «{harder.name_es}» y vuelve al rango "
            f"{rep_min}-{rep_max}.",
            reps=(rep_min, rep_max),
            exercise_id=harder.id,
        )
    return _suggestion(
        SuggestionKind.HOLD,
        "Ya haces muchas repeticiones: ralentiza la bajada para hacerlo más exigente.",
    )


def suggest(
    prescription: ExercisePrescription,
    card: ExerciseCard,
    history: Sequence[ExerciseHistoryEntry],
    catalog: Sequence[ExerciseCard],
    tables: Tables | None = None,
) -> ProgressionSuggestion:
    """Sugerencia para la próxima sesión a partir del historial del ejercicio."""
    tables = tables or default_tables()
    sessions = [e for e in sorted(history, key=lambda e: e.session_date) if _work_sets(e)]
    rir = prescription.target_rir
    if not sessions:
        reserve = f" que te deje {reps_in_reserve_es(rir)} en reserva" if rir is not None else ""
        return _suggestion(
            SuggestionKind.FIRST_TIME,
            f"Primera vez con este ejercicio: elige una carga{reserve} y anótala.",
        )
    last = _work_sets(sessions[-1])
    if prescription.rep_min is None or prescription.rep_max is None:
        return _timed(prescription, card, last, catalog, tables)
    rep_min, rep_max = prescription.rep_min, prescription.rep_max
    top_reached = all(
        s.reps is not None and s.reps >= rep_max and (s.rir is None or rir is None or s.rir >= rir)
        for s in last
    )
    if card.load_type in {LoadType.BODYWEIGHT, LoadType.TIME}:
        return _bodyweight(card, (rep_min, rep_max), catalog, tables, top_reached=top_reached)
    return _loaded(prescription, card, sessions, tables, top_reached=top_reached)


def _loaded(
    prescription: ExercisePrescription,
    card: ExerciseCard,
    sessions: list[ExerciseHistoryEntry],
    tables: Tables,
    *,
    top_reached: bool,
) -> ProgressionSuggestion:
    rep_min = prescription.rep_min or 1
    last = _work_sets(sessions[-1])
    weights = [s.weight_kg for s in last if s.weight_kg is not None]
    if not weights:
        return _suggestion(
            SuggestionKind.HOLD, "Anota el peso de tus series para poder sugerirte la progresión."
        )
    weight = max(weights)
    assisted = card.load_type is LoadType.ASSISTED
    threshold = tables.periodization.progression.miss_threshold_sessions
    recent = sessions[-threshold:]
    missed = len(recent) == threshold and all(
        any(s.reps is not None and s.reps < rep_min for s in _work_sets(e)) for e in recent
    )
    if top_reached:
        step = _increment(card, tables)
        target = max(0.0, weight - step) if assisted else weight + step
        kind = SuggestionKind.INCREASE_LOAD
        reason = (
            "Completaste todas las series en el tope del rango: reduce la asistencia a "
            if assisted
            else "Completaste todas las series en el tope del rango: sube a "
        )
    elif missed:
        worst = max(rep_min - (s.reps or 0) for s in last)
        low, high = tables.periodization.progression.reduce_ratio
        ratio = high if worst > 1 else low
        target = weight * (1 + ratio) if assisted else weight * (1 - ratio)
        kind = SuggestionKind.DECREASE_LOAD
        reason = (
            f"No llegaste al mínimo de {rep_min} repeticiones en {threshold} sesiones seguidas: "
            "prueba con "
        )
    else:
        target = weight
        kind = SuggestionKind.HOLD
        reason = "Mantén la carga hasta completar todas las series en el tope del rango: "
    if assisted:
        suggested, plates = round(max(0.0, target), 2), tuple[float, ...]()
    else:
        suggested, plates = round_load(target, card.equipment_code, tables)
    warmup: tuple[WarmupSet, ...] = ()
    strength_max = tables.prescription.table[Goal.STRENGTH]["main"].reps[1]
    if (
        card.mechanic is Mechanic.COMPOUND
        and prescription.rep_max is not None
        and prescription.rep_max <= strength_max
    ):
        warmup = warmup_ramp(suggested, card.load_type, card.equipment_code, tables)
    return _suggestion(
        kind,
        f"{reason}{number_es(suggested)} kg.",
        weight=suggested,
        plates=plates,
        warmup=warmup,
    )

"""Paso 6 (§7.2, §7.5): series, repeticiones, RIR, tempo y descanso de cada ejercicio.

Reglas de nivel: principiantes con RIR +1 y series en el mínimo del rango. Modificadores de
sexo (§7.4, ``sex-modifiers.yaml``): solo descanso de accesorios (con mínimo de tabla) y
+N repeticiones al tope en aislamiento. Nunca se limita la carga por sexo.
"""

from forja_engine.allocate import pick_from_range
from forja_engine.draft import DraftExercise
from forja_engine.models import (
    ExerciseCard,
    ExerciseRole,
    GeneratorInput,
    Laterality,
    LoadType,
    Mechanic,
    SlotRef,
)
from forja_engine.tables import Range, RoleRx, Tables
from forja_engine.texts import reps_in_reserve_es

MAX_RIR = 5
DUR_STEP = 5


def round_to(value: float, step: int) -> int:
    """Redondeo al múltiplo de ``step`` más cercano (mitades hacia arriba)."""
    return int((value + step / 2) // step * step)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def role_rx(inp: GeneratorInput, role: ExerciseRole, tables: Tables) -> RoleRx:
    return tables.prescription.table[inp.goal]["main" if role is ExerciseRole.MAIN else "accessory"]


def bodyweight_limited(card: ExerciseCard, tables: Tables) -> bool:
    """Dominadas, fondos y similares de peso corporal (C9): techo de repeticiones prescrito."""
    return tables.prescription.bodyweight_rep_limits.matches(card)


def working_rir(inp: GeneratorInput, role: ExerciseRole, week_rir: int, tables: Tables) -> int:
    """RIR de la semana acotado al rango de la tabla del rol, +1 para principiantes."""
    rx = tables.prescription
    low, high = rx.common.core.rir if role is ExerciseRole.CORE else role_rx(inp, role, tables).rir
    delta = rx.experience_adjustments[inp.experience].rir_delta
    return clamp(clamp(week_rir, low, high) + delta, 0, MAX_RIR)


def load_hint(card: ExerciseCard, rir: int | None) -> str | None:
    """Indicación de carga en español según el tipo de carga (sin cifras de peso)."""
    if card.load_type is LoadType.TIME:
        return "Mantén la posición con técnica impecable"
    if rir is None:
        return None
    reserve = reps_in_reserve_es(rir)
    if card.load_type is LoadType.BODYWEIGHT:
        return f"Con tu peso corporal, deja {reserve} en reserva"
    if card.load_type is LoadType.ASSISTED:
        return f"Ajusta la asistencia para dejar {reserve} en reserva"
    return f"Carga que te deje {reserve} en reserva"


def _hold(values: Range, inp: GeneratorInput, tables: Tables) -> int:
    rule = tables.prescription.experience_adjustments[inp.experience].sets
    return max(DUR_STEP, round_to(pick_from_range(values, rule), DUR_STEP))


def prescribe_working(
    card: ExerciseCard,
    slot: SlotRef,
    sets: int,
    inp: GeneratorInput,
    tables: Tables,
    *,
    week_rir: int,
    circuit: bool,
) -> DraftExercise:
    """Prescripción de un ejercicio de fuerza o core de la semana tipo."""
    rx = tables.prescription
    sex = tables.sex_modifiers.for_sex(inp.sex)
    role = slot.role
    per_side = card.laterality is Laterality.UNILATERAL
    rir = working_rir(inp, role, week_rir, tables)
    if role is ExerciseRole.CORE:
        core = rx.common.core
        reps: Range = core.reps
        tempo: str | None = None
        rest = core.rest_s[0]
        floor = max(core.rest_s[0], rx.min_rest_s.core)
    else:
        table = role_rx(inp, role, tables)
        reps = table.reps
        tempo = table.tempo
        low, high = table.rest_s
        if circuit:
            rest = floor = low
        elif role is ExerciseRole.MAIN:
            rest = round_to((low + high) / 2, 15)
            floor = max(low, rx.min_rest_s.main)
        else:
            rest = max(round_to((low + high) / 2 * sex.accessory_rest_multiplier, 5), low)
            floor = max(low, rx.min_rest_s.accessory)
    if circuit and role is ExerciseRole.CORE:
        floor = rest
    duration: int | None = None
    rep_min: int | None = reps[0]
    rep_max: int | None = reps[1]
    if card.load_type is LoadType.TIME:
        duration = _hold(rx.common.core.hold_s, inp, tables)
        rep_min = rep_max = None
        tempo = None
    elif card.mechanic is Mechanic.ISOLATION:
        rep_max = reps[1] + sex.isolation_rep_max_delta
    notes = "Repeticiones o tiempo por lado." if per_side else None
    limits = rx.bodyweight_rep_limits
    if (
        rep_min is not None
        and rep_max is not None
        and card.load_type is LoadType.BODYWEIGHT
        and bodyweight_limited(card, tables)
        and rep_max > limits.max
    ):
        rep_min = clamp(rep_min, limits.min, limits.max)
        rep_max = limits.max
        notes = (
            f"Este ejercicio exigente se limita a {limits.max} repeticiones por serie: "
            "cuando te sobre fuerza, pasa a una variante más difícil."
            + (" Repeticiones por lado." if per_side else "")
        )
    return DraftExercise(
        card=card,
        slot=slot,
        rx_role=role,
        sets=sets,
        rep_min=rep_min,
        rep_max=rep_max,
        duration_s=duration,
        per_side=per_side,
        target_rir=rir,
        tempo=tempo,
        rest_s=rest,
        rest_floor_s=min(floor, rest),
        load_hint=load_hint(card, rir),
        notes_es=notes,
    )


def prescribe_warmup_cardio(card: ExerciseCard, tables: Tables) -> DraftExercise:
    minutes = tables.prescription.time_model.warmup_minutes
    seconds = max(DUR_STEP, round_to(minutes * 60 * tables.engine_rules.warmup.cardio_share, 30))
    return DraftExercise(
        card=card,
        slot=None,
        rx_role=ExerciseRole.WARMUP,
        sets=1,
        rep_min=None,
        rep_max=None,
        duration_s=seconds,
        per_side=False,
        target_rir=None,
        tempo=None,
        rest_s=0,
        rest_floor_s=0,
        notes_es="Ritmo suave que vaya subiendo poco a poco.",
    )


def prescribe_warmup_specific(
    card: ExerciseCard, inp: GeneratorInput, tables: Tables
) -> DraftExercise:
    warmup = tables.prescription.common.warmup
    rule = tables.prescription.experience_adjustments[inp.experience].sets
    timed = card.load_type is LoadType.TIME
    return DraftExercise(
        card=card,
        slot=None,
        rx_role=ExerciseRole.WARMUP,
        sets=pick_from_range(warmup.sets, rule),
        rep_min=None if timed else warmup.reps[0],
        rep_max=None if timed else warmup.reps[1],
        duration_s=_hold(warmup.hold_s, inp, tables) if timed else None,
        per_side=card.laterality is Laterality.UNILATERAL,
        target_rir=None,
        tempo=None,
        rest_s=warmup.rest_s[1],
        rest_floor_s=warmup.rest_s[0],
        notes_es="Aproximación ligera para preparar el primer ejercicio: sin llegar a fatigarte.",
    )


def prescribe_warmup_ramp(card: ExerciseCard, tables: Tables) -> DraftExercise:
    """Series de aproximación (``progression.warmup_ramp``) sobre el propio ejercicio (C7)."""
    ramp = tables.periodization.progression.warmup_ramp
    steps = "; ".join(f"{round(pct * 100)} % × {reps}" for pct, reps in ramp)
    reps_values = [reps for _, reps in ramp]
    return DraftExercise(
        card=card,
        slot=None,
        rx_role=ExerciseRole.WARMUP,
        sets=len(ramp),
        rep_min=min(reps_values),
        rep_max=max(reps_values),
        duration_s=None,
        per_side=card.laterality is Laterality.UNILATERAL,
        target_rir=None,
        tempo=None,
        rest_s=tables.prescription.common.warmup.rest_s[1],
        rest_floor_s=tables.prescription.common.warmup.rest_s[0],
        notes_es=(
            f"Series de aproximación con tu carga de trabajo ({steps}): sin llegar a fatigarte."
        ),
    )


def prescribe_cooldown(card: ExerciseCard, inp: GeneratorInput, tables: Tables) -> DraftExercise:
    cooldown = tables.prescription.common.cooldown
    rule = tables.prescription.experience_adjustments[inp.experience].sets
    return DraftExercise(
        card=card,
        slot=None,
        rx_role=ExerciseRole.MOBILITY,
        sets=pick_from_range(cooldown.sets, rule),
        rep_min=None,
        rep_max=None,
        duration_s=_hold(cooldown.hold_s, inp, tables),
        per_side=cooldown.per_side and card.laterality is Laterality.UNILATERAL,
        target_rir=None,
        tempo=None,
        rest_s=cooldown.rest_s[0],
        rest_floor_s=cooldown.rest_s[0],
        notes_es="Estira sin rebotes y respira con calma.",
    )


def prescribe_finisher(card: ExerciseCard, inp: GeneratorInput, tables: Tables) -> DraftExercise:
    finisher = tables.prescription.common.cardio_finisher
    long_session = inp.session_minutes >= tables.engine_rules.finisher.long_session_minutes
    minutes = finisher.minutes[1] if long_session else finisher.minutes[0]
    return DraftExercise(
        card=card,
        slot=None,
        rx_role=ExerciseRole.CARDIO,
        sets=1,
        rep_min=None,
        rep_max=None,
        duration_s=minutes * 60,
        per_side=False,
        target_rir=None,
        tempo=None,
        rest_s=0,
        rest_floor_s=0,
        notes_es=f"Intensidad {finisher.intensity_es}.",
    )


def prescribe_recovery(
    card: ExerciseCard, slot: SlotRef, inp: GeneratorInput, tables: Tables
) -> DraftExercise:
    """Día de recuperación activa: cardio suave y movilidad (§7.1, 7 días)."""
    recovery = tables.engine_rules.recovery
    if slot.role is ExerciseRole.CARDIO:
        low, high = recovery.cardio_minutes
        minutes = clamp(inp.session_minutes - recovery.reserve_minutes, low, high)
        sets, duration, per_side = 1, minutes * 60, False
        notes = "Intensidad suave (RPE 3-4): puedes hablar con frases completas."
    else:
        sets, duration = recovery.mobility_sets, recovery.mobility_hold_s
        per_side = card.laterality is Laterality.UNILATERAL
        notes = "Movilidad tranquila, sin llegar a molestias."
    return DraftExercise(
        card=card,
        slot=slot,
        rx_role=slot.role,
        sets=sets,
        rep_min=None,
        rep_max=None,
        duration_s=duration,
        per_side=per_side,
        target_rir=None,
        tempo=None,
        rest_s=0,
        rest_floor_s=0,
        notes_es=notes,
    )

"""Operaciones del motor sobre un plan existente (§7.7).

- ``validate_plan``: violaciones duras (invariantes de ``contracts/domain.md`` §5.3).
- ``rebalance_after_edit``: recalcula volumen, duración, orden y avisos tras editar a mano.
- ``swap_exercise``: sustituye un ejercicio por otro válido para su slot.
- ``regenerate_day``: vuelve a elegir los ejercicios de un día conservando el resto.

Las entradas imposibles (dirección inexistente, ejercicio de reemplazo no válido) lanzan
:class:`PlanOperationError` (``ValueError``); la falta de candidatos nunca lanza: degrada y
avisa.
"""

from collections.abc import Collection, Sequence
from typing import Literal

from forja_engine.compose import (
    day_volume,
    dedupe,
    volume_ratio,
    volume_warnings,
    weekly_volume,
)
from forja_engine.generator import BuildOptions, CreditCache, build_plan
from forja_engine.models import (
    WORKING_BLOCKS,
    BlockKind,
    ExerciseCard,
    ExerciseRole,
    Laterality,
    LoadType,
    PlanBlock,
    PlanDay,
    PlanExercise,
    PlanWarning,
    PlanWarningCode,
    ProgramPlan,
    SlotAddress,
    SlotRef,
)
from forja_engine.normalize import derive_seed, rng_for
from forja_engine.prescribe import load_hint
from forja_engine.select import Selector, UsageState
from forja_engine.tables import Tables, default_tables
from forja_engine.texts import number_es
from forja_engine.timefit import day_seconds, limit_seconds, minutes_of
from forja_engine.volume import blocks_volume, weekly_targets

HISTORICAL_CODES = frozenset(
    {
        PlanWarningCode.BEGINNER_HIGH_FREQUENCY,
        PlanWarningCode.RECOVERY_DAY_ENFORCED,
        PlanWarningCode.SLOT_RELAXED,
        PlanWarningCode.SLOT_DROPPED,
        PlanWarningCode.MAIN_EXERCISE_TRIMMED,
        PlanWarningCode.AVOIDED_MUSCLE_SUBSTITUTED,
        PlanWarningCode.EQUIPMENT_INSUFFICIENT,
    }
)
"""Avisos de la generación que describen decisiones tomadas y se conservan tras editar."""

DELOAD_PREFIX = "Semana de descarga"
MAX_MINUTES = 240


class PlanOperationError(ValueError):
    """Operación imposible sobre el plan (dirección o ejercicio de reemplazo inválidos)."""


# ------------------------------------------------------------------------ validate
def _violation(
    code: PlanWarningCode,
    message: str,
    week: int,
    day: int,
    exercise_id: str | None = None,
) -> PlanWarning:
    return PlanWarning(
        code=code, message_es=message, week_index=week, day_index=day, exercise_id=exercise_id
    )


def _exercise_violations(
    plan: ProgramPlan,
    exercise: PlanExercise,
    block: PlanBlock,
    *,
    by_id: dict[str, ExerciseCard],
    tables: Tables,
    where: tuple[int, int],
) -> list[PlanWarning]:
    week, day = where
    inp = plan.input
    card = by_id.get(exercise.exercise_id)
    ex_id = exercise.exercise_id
    if card is None:
        return [
            _violation(
                PlanWarningCode.UNKNOWN_EXERCISE,
                f"El ejercicio {ex_id} no existe en el catálogo actual.",
                week,
                day,
                ex_id,
            )
        ]
    name = card.name_es
    found: list[PlanWarning] = []
    if card.deprecated:
        found.append(
            _violation(
                PlanWarningCode.DEPRECATED_EXERCISE,
                f"«{name}» ya no está en el catálogo vigente: sustitúyelo.",
                week,
                day,
                ex_id,
            )
        )
    if ex_id in inp.excluded_exercise_ids:
        found.append(
            _violation(
                PlanWarningCode.EXCLUDED_EXERCISE,
                f"«{name}» está en tu lista de ejercicios excluidos.",
                week,
                day,
                ex_id,
            )
        )
    if card.target_muscle in inp.avoid_muscles or card.movement_pattern in inp.avoid_patterns:
        found.append(
            _violation(
                PlanWarningCode.AVOIDED_EXERCISE,
                f"«{name}» trabaja un músculo o movimiento que quieres evitar.",
                week,
                day,
                ex_id,
            )
        )
    if card.equipment_code not in inp.equipment.items:
        found.append(
            _violation(
                PlanWarningCode.EQUIPMENT_INSUFFICIENT,
                f"«{name}» necesita un equipamiento que no tienes disponible.",
                week,
                day,
                ex_id,
            )
        )
    if block.kind in WORKING_BLOCKS:
        if card.role is ExerciseRole.MOBILITY:
            found.append(
                _violation(
                    PlanWarningCode.MOBILITY_IN_MAIN_BLOCK,
                    f"«{name}» es un estiramiento: va en la vuelta a la calma, no en el bloque "
                    "principal.",
                    week,
                    day,
                    ex_id,
                )
            )
        role = exercise.slot.role if exercise.slot is not None else card.role
        minimum = tables.prescription.min_rest_s.for_role(role)
        if block.kind is BlockKind.CIRCUIT and minimum is not None:
            minimum = tables.prescription.min_rest_s.accessory
        if minimum is not None and exercise.rest_s < minimum:
            found.append(
                _violation(
                    PlanWarningCode.REST_BELOW_MINIMUM,
                    f"El descanso de «{name}» ({exercise.rest_s} s) está por debajo del mínimo "
                    f"de {minimum} s.",
                    week,
                    day,
                    ex_id,
                )
            )
    return found


def validate_plan(
    plan: ProgramPlan, catalog: Sequence[ExerciseCard], tables: Tables | None = None
) -> tuple[PlanWarning, ...]:
    """Violaciones duras del plan (vacío si es válido)."""
    tables = tables or default_tables()
    by_id = {card.id: card for card in catalog}
    credits = CreditCache(by_id, tables)
    cap = tables.volume_targets.max_effective_sets_per_group_per_session
    names = {g.value: n for g, n in tables.engine_rules.group_names_es.items()}
    found: list[PlanWarning] = []
    for week in plan.weeks:
        for day in week.days:
            where = (week.index, day.index)
            working = [e for b in day.blocks if b.kind in WORKING_BLOCKS for e in b.exercises]
            if not working and not day.is_recovery:
                found.append(
                    _violation(
                        PlanWarningCode.EMPTY_DAY,
                        f"«{day.name_es}» no tiene ningún ejercicio de trabajo.",
                        *where,
                    )
                )
            for block in day.blocks:
                for exercise in block.exercises:
                    found += _exercise_violations(
                        plan, exercise, block, by_id=by_id, tables=tables, where=where
                    )
            for group, sets in blocks_volume(day.blocks, credits).items():
                if sets > cap:
                    found.append(
                        _violation(
                            PlanWarningCode.SESSION_GROUP_CAP,
                            f"«{day.name_es}» acumula {number_es(sets)} series efectivas de "
                            f"{names[group.value]}; el máximo por sesión es {number_es(cap)}.",
                            *where,
                        )
                    )
    return dedupe(found)


# ----------------------------------------------------------------------- rebalance
def _renumber(day: PlanDay, credits: CreditCache, tables: Tables) -> PlanDay:
    blocks = tuple(
        block.model_copy(
            update={
                "order": order,
                "exercises": tuple(
                    e.model_copy(update={"order": position})
                    for position, e in enumerate(block.exercises)
                ),
            }
        )
        for order, block in enumerate(day.blocks)
    )
    seconds = day_seconds(blocks, tables.prescription.time_model)
    return day.model_copy(
        update={
            "blocks": blocks,
            "estimated_minutes": min(MAX_MINUTES, minutes_of(seconds)),
            "volume": day_volume(blocks, credits),
        }
    )


def _time_warnings(plan: ProgramPlan, tables: Tables) -> list[PlanWarning]:
    limit = limit_seconds(plan.input.session_minutes, tables.prescription.time_model) // 60
    return [
        PlanWarning(
            code=PlanWarningCode.TIME_BUDGET_EXCEEDED,
            message_es=(
                f"«{day.name_es}» dura unos {day.estimated_minutes} minutos, más de los "
                f"{plan.input.session_minutes} que tienes."
            ),
            week_index=week.index,
            day_index=day.index,
        )
        for week in plan.weeks
        for day in week.days
        if day.estimated_minutes > limit
    ]


def rebalance_after_edit(
    plan: ProgramPlan, catalog: Sequence[ExerciseCard], tables: Tables | None = None
) -> ProgramPlan:
    """Recalcula orden, duración, volumen y avisos de un plan editado a mano."""
    tables = tables or default_tables()
    credits = CreditCache({card.id: card for card in catalog}, tables)
    days = [[_renumber(day, credits, tables) for day in week.days] for week in plan.weeks]
    weeks = tuple(
        week.model_copy(update={"days": tuple(d), "volume_ratio": volume_ratio(d, days[0])})
        for week, d in zip(plan.weeks, days, strict=True)
    )
    targets = weekly_targets(plan.input, tables)
    volume = weekly_volume(days[0], targets)
    updated = plan.model_copy(update={"weeks": weeks, "weekly_volume": volume})
    kept = [w for w in plan.warnings if w.code in HISTORICAL_CODES and w.week_index is None]
    derived = [
        *volume_warnings(volume, targets, tables),
        *_time_warnings(updated, tables),
        *validate_plan(updated, catalog, tables),
    ]
    return updated.model_copy(update={"warnings": dedupe(kept + derived)})


# ---------------------------------------------------------------------------- swap
def _locate(plan: ProgramPlan, address: SlotAddress) -> tuple[PlanDay, PlanExercise]:
    weeks = [w for w in plan.weeks if w.index == address.week_index]
    days = [d for w in weeks for d in w.days if d.index == address.day_index]
    exercises = [
        e
        for d in days
        for b in d.blocks
        if b.order == address.block_order
        for e in b.exercises
        if e.order == address.exercise_order
    ]
    if not exercises:
        msg = "la dirección no corresponde a ningún ejercicio del plan"
        raise PlanOperationError(msg)
    return days[0], exercises[0]


def _slot_for(exercise: PlanExercise, card: ExerciseCard | None, tables: Tables) -> SlotRef:
    """Slot del ejercicio o, en calentamiento/calma/finisher, uno equivalente a su rol."""
    if exercise.slot is not None:
        return exercise.slot
    if card is None:
        msg = "no se puede sustituir un ejercicio sin slot que no está en el catálogo"
        raise PlanOperationError(msg)
    return SlotRef(
        slot_index=0,
        pattern=card.movement_pattern,
        role=card.role,
        group=tables.muscle_group(card.target_muscle),
        priority=3,
    )


def _usage(
    plan: ProgramPlan, address: SlotAddress, skip: str, by_id: dict[str, ExerciseCard]
) -> UsageState:
    usage = UsageState()
    week = next(w for w in plan.weeks if w.index == address.week_index)
    for day in week.days:
        for block in day.blocks:
            for exercise in block.exercises:
                card = by_id.get(exercise.exercise_id)
                if card is None or card.id == skip:
                    continue
                usage.week_ids.add(card.id)
                usage.week_variants.add(card.variant_group)
                if day.index == address.day_index:
                    usage.day_ids.add(card.id)
                    usage.day_variants.add(card.variant_group)
    return usage


def _adapted(
    exercise: PlanExercise,
    card: ExerciseCard,
    alternatives: tuple[str, ...],
    plan: ProgramPlan,
    tables: Tables,
) -> PlanExercise:
    """Ajusta la prescripción al nuevo ejercicio (reps o duración, lateralidad, indicación)."""
    update: dict[str, object] = {"exercise_id": card.id, "alternatives": alternatives}
    if exercise.slot is None:
        return exercise.model_copy(update=update)
    update["per_side"] = card.laterality is Laterality.UNILATERAL
    if card.load_type is LoadType.TIME and exercise.duration_s is None:
        hold = tables.prescription.common.core.hold_s[0]
        update |= {"rep_min": None, "rep_max": None, "tempo": None, "duration_s": hold}
    elif card.load_type is not LoadType.TIME and exercise.duration_s is not None:
        role = exercise.slot.role
        if role is ExerciseRole.CORE:
            reps = tables.prescription.common.core.reps
        else:
            key: Literal["main", "accessory"] = "main" if role is ExerciseRole.MAIN else "accessory"
            reps = tables.prescription.table[plan.input.goal][key].reps
        update |= {"rep_min": reps[0], "rep_max": reps[1], "duration_s": None}
    if not (exercise.load_hint or "").startswith(DELOAD_PREFIX):
        update["load_hint"] = load_hint(card, exercise.target_rir)
    return exercise.model_copy(update=update)


def _replace_in_weeks(
    plan: ProgramPlan, address: SlotAddress, old_id: str, new: dict[int, PlanExercise]
) -> ProgramPlan:
    def swap_block(block: PlanBlock, week_index: int) -> PlanBlock:
        if block.order != address.block_order:
            return block
        return block.model_copy(
            update={
                "exercises": tuple(
                    new[week_index]
                    if e.order == address.exercise_order and e.exercise_id == old_id
                    else e
                    for e in block.exercises
                )
            }
        )

    weeks = tuple(
        week.model_copy(
            update={
                "days": tuple(
                    day.model_copy(
                        update={"blocks": tuple(swap_block(b, week.index) for b in day.blocks)}
                    )
                    if day.index == address.day_index
                    else day
                    for day in week.days
                )
            }
        )
        if week.index in new
        else week
        for week in plan.weeks
    )
    return plan.model_copy(update={"weeks": weeks})


def swap_exercise(  # noqa: PLR0917 - firma fijada por el contrato (domain.md §5.5)
    plan: ProgramPlan,
    catalog: Sequence[ExerciseCard],
    address: SlotAddress,
    exclude_ids: Collection[str],
    replacement_id: str | None,
    apply_to_all_weeks: bool,  # noqa: FBT001 - firma fijada por el contrato (domain.md §5.5)
    tables: Tables | None = None,
) -> ProgramPlan:
    """Sustituye el ejercicio de ``address`` (y el mismo hueco del resto de semanas)."""
    tables = tables or default_tables()
    day, exercise = _locate(plan, address)
    selector = Selector(catalog, plan.input, tables)
    slot = _slot_for(exercise, selector.by_id.get(exercise.exercise_id), tables)
    usage = _usage(plan, address, exercise.exercise_id, selector.by_id)
    excluded = {*exclude_ids, exercise.exercise_id}
    relaxed = tables.engine_rules.relaxation_order
    pool = selector.candidates(slot, relaxed, usage, excluded)
    if replacement_id is not None:
        card = next((c for c in pool if c.id == replacement_id), None)
        if card is None:
            msg = f"el ejercicio {replacement_id} no es válido para este hueco"
            raise PlanOperationError(msg)
        ranked = sorted(
            (c for c in pool if c.variant_group != card.variant_group),
            key=lambda c: (-selector.score(c, slot, usage), c.id),
        )
        alternatives = tuple(c.id for c in ranked[: tables.engine_rules.max_alternatives])
    else:
        rng = rng_for(plan.seed, "swap", address.model_dump_json(), sorted(excluded))
        choice = selector.choose(slot, rng, usage, excluded)
        if choice is None:
            warning = PlanWarning(
                code=PlanWarningCode.SLOT_RELAXED,
                message_es=(
                    f"No hay otro ejercicio válido para sustituir en «{day.name_es}»: se "
                    "mantiene el actual."
                ),
                week_index=address.week_index,
                day_index=day.index,
                exercise_id=exercise.exercise_id,
            )
            return plan.model_copy(update={"warnings": dedupe((*plan.warnings, warning))})
        card, alternatives = choice.card, choice.alternatives
    replacements: dict[int, PlanExercise] = {}
    for week in plan.weeks:
        if not apply_to_all_weeks and week.index != address.week_index:
            continue
        matches = [
            e
            for d in week.days
            if d.index == day.index
            for b in d.blocks
            if b.order == address.block_order
            for e in b.exercises
            if e.order == address.exercise_order and e.exercise_id == exercise.exercise_id
        ]
        if matches:
            replacements[week.index] = _adapted(matches[0], card, alternatives, plan, tables)
    swapped = _replace_in_weeks(plan, address, exercise.exercise_id, replacements)
    return rebalance_after_edit(swapped, catalog, tables)


# ------------------------------------------------------------------ regenerate day
def regenerate_day(
    plan: ProgramPlan,
    catalog: Sequence[ExerciseCard],
    day_index: int,
    seed: int | None,
    tables: Tables | None = None,
) -> ProgramPlan:
    """Vuelve a elegir los ejercicios del día ``day_index`` en todas las semanas.

    Los demás días no cambian. Sin ``seed`` se deriva una nueva de la semilla del plan y de
    los ejercicios actuales del día, de modo que regenerar varias veces da días distintos;
    los ejercicios actuales se penalizan como «ya usados» para favorecer la variedad.
    """
    tables = tables or default_tables()
    if not 0 <= day_index < len(plan.weeks[0].days):
        msg = f"el día {day_index} no existe en el plan"
        raise PlanOperationError(msg)
    by_id = {card.id: card for card in catalog}
    base = plan.weeks[0]
    current = [e.exercise_id for b in base.days[day_index].blocks for e in b.exercises]
    new_seed = derive_seed(plan.seed, "regenerate", day_index, current) if seed is None else seed
    used = [
        by_id[e.exercise_id]
        for day in base.days
        for b in day.blocks
        if b.kind in WORKING_BLOCKS
        for e in b.exercises
        if e.exercise_id in by_id
    ]
    options = BuildOptions(day_seeds={day_index: new_seed}, pre_used=used)
    rebuilt = build_plan(plan.input, catalog, tables, options)
    weeks = tuple(
        week.model_copy(
            update={
                "days": tuple(
                    new_week.days[day_index] if day.index == day_index else day for day in week.days
                )
            }
        )
        for week, new_week in zip(plan.weeks, rebuilt.weeks, strict=True)
    )
    warnings = [w for w in plan.warnings if w.day_index != day_index] + [
        w for w in rebuilt.warnings if w.day_index == day_index
    ]
    spliced = plan.model_copy(update={"weeks": weeks, "warnings": tuple(warnings)})
    return rebalance_after_edit(spliced, catalog, tables)

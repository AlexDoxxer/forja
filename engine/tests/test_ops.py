"""§7.7: validate_plan, rebalance_after_edit, swap_exercise y regenerate_day."""

from collections.abc import Iterable
from functools import cache

import pytest

from forja_engine import (
    PlanOperationError,
    generate,
    rebalance_after_edit,
    regenerate_day,
    swap_exercise,
    validate_plan,
)
from forja_engine.models import (
    BlockKind,
    EquipmentPreset,
    EquipmentSelection,
    ExerciseRole,
    Goal,
    LoadType,
    PlanWarning,
    PlanWarningCode,
    ProgramPlan,
    SlotAddress,
)
from tests.helpers import catalog, make_input

CARDS = {c.id: c for c in catalog()}


@cache
def base_plan() -> ProgramPlan:
    return generate(make_input(), catalog())


def edit(plan: ProgramPlan, address: SlotAddress, **update: object) -> ProgramPlan:
    weeks = list(plan.weeks)
    week = weeks[address.week_index]
    days = list(week.days)
    day = days[address.day_index]
    blocks = list(day.blocks)
    block = blocks[address.block_order]
    exercises = list(block.exercises)
    exercises[address.exercise_order] = exercises[address.exercise_order].model_copy(update=update)
    blocks[address.block_order] = block.model_copy(update={"exercises": tuple(exercises)})
    days[address.day_index] = day.model_copy(update={"blocks": tuple(blocks)})
    weeks[address.week_index] = week.model_copy(update={"days": tuple(days)})
    return plan.model_copy(update={"weeks": tuple(weeks)})


def first_main(plan: ProgramPlan, day: int = 0, week: int = 0) -> SlotAddress:
    blocks = plan.weeks[week].days[day].blocks
    order = next(b.order for b in blocks if b.kind is BlockKind.MAIN)
    return SlotAddress(week_index=week, day_index=day, block_order=order, exercise_order=0)


def exercise_at(plan: ProgramPlan, address: SlotAddress) -> str:
    day = plan.weeks[address.week_index].days[address.day_index]
    return day.blocks[address.block_order].exercises[address.exercise_order].exercise_id


def codes(warnings: Iterable[PlanWarning]) -> set[PlanWarningCode]:
    return {w.code for w in warnings}


# ------------------------------------------------------------------------ validate
def test_generated_plan_is_valid() -> None:
    assert validate_plan(base_plan(), catalog()) == ()


def test_validate_detects_each_rule() -> None:
    plan = base_plan()
    address = first_main(plan)
    stretch = next(c.id for c in catalog() if c.role is ExerciseRole.MOBILITY)
    assert codes(validate_plan(edit(plan, address, rest_s=10), catalog())) == {
        PlanWarningCode.REST_BELOW_MINIMUM
    }
    assert PlanWarningCode.MOBILITY_IN_MAIN_BLOCK in codes(
        validate_plan(edit(plan, address, exercise_id=stretch), catalog())
    )
    assert codes(validate_plan(edit(plan, address, exercise_id="9999"), catalog())) == {
        PlanWarningCode.DEPRECATED_EXERCISE
    }
    used = exercise_at(plan, address)
    deprecated = [
        c.model_copy(update={"deprecated": True}) if c.id == used else c for c in catalog()
    ]
    assert PlanWarningCode.DEPRECATED_EXERCISE in codes(validate_plan(plan, deprecated))
    excluded = plan.model_copy(
        update={"input": plan.input.model_copy(update={"excluded_exercise_ids": (used,)})}
    )
    assert PlanWarningCode.AVOIDED_MUSCLE_SUBSTITUTED in codes(validate_plan(excluded, catalog()))
    no_gear = plan.model_copy(
        update={
            "input": plan.input.model_copy(
                update={
                    "equipment": EquipmentSelection(preset=EquipmentPreset.BODYWEIGHT, items=())
                }
            )
        }
    )
    assert PlanWarningCode.EQUIPMENT_INSUFFICIENT in codes(validate_plan(no_gear, catalog()))
    capped = edit(plan, address, sets=10)
    capped = edit(
        capped, address.model_copy(update={"block_order": address.block_order + 1}), sets=10
    )
    assert PlanWarningCode.SESSION_GROUP_CAP in codes(validate_plan(capped, catalog()))


def test_validate_detects_empty_days_and_circuit_rest() -> None:
    plan = base_plan()
    day = plan.weeks[0].days[0]
    warmup_only = day.model_copy(update={"blocks": day.blocks[:1]})
    week = plan.weeks[0].model_copy(update={"days": (warmup_only, *plan.weeks[0].days[1:])})
    empty = plan.model_copy(update={"weeks": (week, *plan.weeks[1:])})
    assert PlanWarningCode.EMPTY_DAY in codes(validate_plan(empty, catalog()))
    endurance = generate(make_input(goal=Goal.ENDURANCE), catalog())
    assert validate_plan(endurance, catalog()) == ()
    circuit = next(b for b in endurance.weeks[0].days[0].blocks if b.kind is BlockKind.CIRCUIT)
    address = SlotAddress(week_index=0, day_index=0, block_order=circuit.order, exercise_order=0)
    assert PlanWarningCode.REST_BELOW_MINIMUM in codes(
        validate_plan(edit(endurance, address, rest_s=5), catalog())
    )


# ----------------------------------------------------------------------- rebalance
def test_rebalance_recomputes_volume_time_and_warnings() -> None:
    plan = base_plan()
    address = first_main(plan)
    heavy = edit(plan, address, sets=10, rest_s=600)
    rebalanced = rebalance_after_edit(heavy, catalog())
    day = rebalanced.weeks[0].days[0]
    assert day.estimated_minutes > plan.weeks[0].days[0].estimated_minutes
    assert PlanWarningCode.TIME_BUDGET_EXCEEDED in codes(rebalanced.warnings)
    assert rebalanced.weekly_volume != plan.weekly_volume
    assert rebalance_after_edit(plan, catalog()).weeks == plan.weeks


def test_rebalance_renumbers_blocks_and_exercises() -> None:
    plan = base_plan()
    day = plan.weeks[0].days[0]
    shuffled = day.model_copy(update={"blocks": tuple(reversed(day.blocks))})
    week = plan.weeks[0].model_copy(update={"days": (shuffled, *plan.weeks[0].days[1:])})
    rebalanced = rebalance_after_edit(
        plan.model_copy(update={"weeks": (week, *plan.weeks[1:])}), catalog()
    )
    assert [b.order for b in rebalanced.weeks[0].days[0].blocks] == list(range(len(day.blocks)))


# ---------------------------------------------------------------------------- swap
def test_swap_picks_a_valid_alternative_in_every_week() -> None:
    plan = base_plan()
    address = first_main(plan)
    old = exercise_at(plan, address)
    swapped = swap_exercise(plan, catalog(), address, (), None, apply_to_all_weeks=True)
    new = exercise_at(swapped, address)
    assert new != old
    for week in swapped.weeks:
        assert exercise_at(swapped, address.model_copy(update={"week_index": week.index})) == new
    assert validate_plan(swapped, catalog()) == ()
    only_one = swap_exercise(plan, catalog(), address, (), None, apply_to_all_weeks=False)
    assert exercise_at(only_one, address.model_copy(update={"week_index": 1})) == old


def test_swap_with_user_choice_and_invalid_choices() -> None:
    plan = base_plan()
    address = first_main(plan)
    old = exercise_at(plan, address)
    alternative = plan.weeks[0].days[0].blocks[address.block_order].exercises[0].alternatives[0]
    swapped = swap_exercise(plan, catalog(), address, (), alternative, apply_to_all_weeks=True)
    assert exercise_at(swapped, address) == alternative
    assert old not in swapped.weeks[0].days[0].blocks[address.block_order].exercises[0].alternatives
    with pytest.raises(PlanOperationError, match="no es válido"):
        swap_exercise(plan, catalog(), address, (), old, apply_to_all_weeks=True)
    with pytest.raises(PlanOperationError, match="dirección"):
        swap_exercise(
            plan,
            catalog(),
            address.model_copy(update={"week_index": 9}),
            (),
            None,
            apply_to_all_weeks=True,
        )


def test_swap_warmup_and_cooldown_items() -> None:
    plan = base_plan()
    warmup = SlotAddress(week_index=0, day_index=0, block_order=0, exercise_order=0)
    assert exercise_at(
        swap_exercise(plan, catalog(), warmup, (), None, apply_to_all_weeks=True), warmup
    ) != exercise_at(plan, warmup)
    unknown = edit(plan, warmup, exercise_id="9999")
    with pytest.raises(PlanOperationError, match="sin slot"):
        swap_exercise(unknown, catalog(), warmup, (), None, apply_to_all_weeks=True)


def test_swap_without_candidates_keeps_the_exercise_and_warns() -> None:
    plan = base_plan()
    address = first_main(plan)
    current = CARDS[exercise_at(plan, address)]
    swapped = swap_exercise(plan, [current], address, (), None, apply_to_all_weeks=True)
    assert exercise_at(swapped, address) == current.id
    assert PlanWarningCode.SLOT_RELAXED in codes(swapped.warnings)


def test_swap_converts_between_reps_and_duration() -> None:
    plan = base_plan()
    core = next(
        (b.order, e, e.slot)
        for b in plan.weeks[0].days[1].blocks
        for e in b.exercises
        if e.slot is not None and e.slot.role is ExerciseRole.CORE
    )
    address = SlotAddress(week_index=0, day_index=1, block_order=core[0], exercise_order=0)
    timed = CARDS[core[1].exercise_id].load_type is LoadType.TIME
    wanted = LoadType.TIME if not timed else LoadType.BODYWEIGHT
    target = next(
        c.id
        for c in catalog()
        if c.movement_pattern is core[2].pattern
        and c.load_type is wanted
        and c.role is ExerciseRole.CORE
        and c.difficulty <= 2
    )
    swapped = swap_exercise(plan, catalog(), address, (), target, apply_to_all_weeks=True)
    result = swapped.weeks[0].days[1].blocks[core[0]].exercises[0]
    assert (result.duration_s is not None) == (wanted is LoadType.TIME)
    back = swap_exercise(
        swapped, catalog(), address, (), core[1].exercise_id, apply_to_all_weeks=True
    )
    restored = back.weeks[0].days[1].blocks[core[0]].exercises[0]
    assert (restored.duration_s is not None) == timed


def test_swap_converts_timed_main_back_to_reps() -> None:
    plan = base_plan()
    address = first_main(plan)
    timed = edit(plan, address, rep_min=None, rep_max=None, duration_s=30)
    swapped = swap_exercise(timed, catalog(), address, (), None, apply_to_all_weeks=False)
    assert swapped.weeks[0].days[0].blocks[address.block_order].exercises[0].rep_min is not None


# ------------------------------------------------------------------ regenerate day
def test_regenerate_day_changes_only_that_day() -> None:
    plan = base_plan()
    regenerated = regenerate_day(plan, catalog(), 1, None)
    for week, original in zip(regenerated.weeks, plan.weeks, strict=True):
        assert week.days[0] == original.days[0]
        assert week.days[2:] == original.days[2:]
    old_ids = {e.exercise_id for b in plan.weeks[0].days[1].blocks for e in b.exercises if e.slot}
    new_ids = {
        e.exercise_id for b in regenerated.weeks[0].days[1].blocks for e in b.exercises if e.slot
    }
    assert old_ids != new_ids
    assert validate_plan(regenerated, catalog()) == ()
    assert regenerate_day(plan, catalog(), 1, 5) == regenerate_day(plan, catalog(), 1, 5)


def test_regenerate_rejects_unknown_day() -> None:
    with pytest.raises(PlanOperationError, match="no existe"):
        regenerate_day(base_plan(), catalog(), 6, None)

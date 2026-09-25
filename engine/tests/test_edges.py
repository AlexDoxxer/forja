"""Casos límite puntuales de reparto, ajuste al tiempo, volumen y operaciones."""

from forja_engine import generate, swap_exercise
from forja_engine.allocate import allocate_sets
from forja_engine.draft import DraftBlock, DraftDay
from forja_engine.generator import CreditCache
from forja_engine.models import (
    BlockKind,
    ExerciseRole,
    Experience,
    Goal,
    MovementPattern,
    MuscleGroup,
    SlotAddress,
    SlotRef,
    VolumeGroup,
)
from forja_engine.normalize import normalize_input
from forja_engine.prescribe import prescribe_working
from forja_engine.split import DaySpec
from forja_engine.tables import default_tables
from forja_engine.timefit import _Fitter
from forja_engine.volume import GroupTarget, blocks_volume, slot_credits
from tests.helpers import catalog, make_input

TABLES = default_tables()
CARDS = {c.id: c for c in catalog()}


def test_cap_enforcement_stops_at_the_minimum_sets() -> None:
    slots = tuple(
        SlotRef(
            slot_index=i,
            pattern=MovementPattern.HORIZONTAL_PUSH,
            role=ExerciseRole.MAIN,
            group=MuscleGroup.CHEST,
            priority=1,
        )
        for i in range(6)
    )
    day = DaySpec(0, "custom", "Custom", slots, is_recovery=False, weekday=None)
    targets = {g: GroupTarget(g, 1, 2, 1.5) for g in VolumeGroup}
    sets = allocate_sets([day], targets, Goal.STRENGTH, Experience.ADVANCED, TABLES, circuit=False)
    assert all(value == 2 for value in sets.values())


def test_slot_credits_for_groups_without_volume() -> None:
    other = SlotRef(
        slot_index=0,
        pattern=MovementPattern.HIP_ADDUCTION,
        role=ExerciseRole.ACCESSORY,
        group=MuscleGroup.LEGS_OTHER,
        priority=3,
    )
    assert slot_credits(other, TABLES) == ()


def test_sets_above_rir_4_are_not_effective() -> None:
    plan = generate(make_input(), catalog())
    block = next(b for b in plan.weeks[0].days[0].blocks if b.kind is BlockKind.MAIN)
    easy = block.model_copy(
        update={"exercises": tuple(e.model_copy(update={"target_rir": 5}) for e in block.exercises)}
    )
    credits = CreditCache(CARDS, TABLES)
    assert blocks_volume([easy], credits) == {}
    assert blocks_volume([block], credits) != {}


def test_reducing_accessory_rests_updates_superset_rest() -> None:
    inp = normalize_input(make_input(), TABLES)
    slot = SlotRef(
        slot_index=0,
        pattern=MovementPattern.ELBOW_FLEXION,
        role=ExerciseRole.ACCESSORY,
        group=MuscleGroup.ARMS,
        priority=3,
    )
    pair = [
        prescribe_working(CARDS[i], slot, 3, inp, TABLES, week_rir=2, circuit=False)
        for i in ("0294", "0201")
    ]
    day = DraftDay(0, "t", "Día", "", is_recovery=False, weekday=None)
    day.blocks = [
        DraftBlock(kind=BlockKind.SUPERSET, exercises=pair, rounds=3, rest_between_rounds_s=200)
    ]
    fitter = _Fitter(day, 60, TABLES, CreditCache(CARDS, TABLES))
    fitter.reduce_accessory_rests()
    assert day.blocks[0].rest_between_rounds_s == max(e.rest_floor_s for e in pair)


def test_swap_skips_weeks_where_the_exercise_was_edited() -> None:
    plan = generate(make_input(), catalog())
    blocks = plan.weeks[0].days[0].blocks
    order = next(b.order for b in blocks if b.kind is BlockKind.MAIN)
    address = SlotAddress(week_index=0, day_index=0, block_order=order, exercise_order=0)
    week1 = plan.weeks[1]
    day = week1.days[0]
    edited_block = day.blocks[order].model_copy(
        update={
            "exercises": (
                day.blocks[order].exercises[0].model_copy(update={"exercise_id": "0025"}),
                *day.blocks[order].exercises[1:],
            )
        }
    )
    edited_day = day.model_copy(
        update={"blocks": (*day.blocks[:order], edited_block, *day.blocks[order + 1 :])}
    )
    edited = plan.model_copy(
        update={
            "weeks": (
                plan.weeks[0],
                week1.model_copy(update={"days": (edited_day, *week1.days[1:])}),
                *plan.weeks[2:],
            )
        }
    )
    swapped = swap_exercise(edited, catalog(), address, (), None, apply_to_all_weeks=True)
    assert swapped.weeks[1].days[0].blocks[order].exercises[0].exercise_id == "0025"

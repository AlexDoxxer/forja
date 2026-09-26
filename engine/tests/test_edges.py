"""Casos límite puntuales de reparto, ajuste al tiempo, volumen y operaciones."""

from forja_engine import generate, swap_exercise
from forja_engine.allocate import allocate_sets
from forja_engine.draft import DraftBlock, DraftDay
from forja_engine.generator import CreditCache
from forja_engine.models import (
    BlockKind,
    EquipmentPreset,
    EquipmentSelection,
    ExerciseRole,
    Experience,
    Goal,
    MovementPattern,
    MuscleGroup,
    PlanWarningCode,
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
    assert all(value == 4 for value in sets.values())  # mínimo de la tabla de fuerza (B2)


def test_beginner_bodyweight_vertical_push_falls_back_to_safer_pattern() -> None:
    """Solo hay pino como empuje vertical: cae a flexiones con un aviso específico (B3)."""
    inp = make_input(
        equipment=EquipmentSelection(preset=EquipmentPreset.BODYWEIGHT),
        experience=Experience.BEGINNER,
        days_per_week=2,
    )
    plan = generate(inp, catalog())
    chosen = [
        CARDS[e.exercise_id]
        for b in plan.weeks[0].days[1].blocks
        for e in b.exercises
        if e.slot is not None and e.slot.pattern is MovementPattern.VERTICAL_PUSH
    ]
    assert chosen
    assert chosen[0].difficulty <= 2
    assert chosen[0].movement_pattern is MovementPattern.HORIZONTAL_PUSH
    relaxed = [
        w
        for w in plan.warnings
        if w.code is PlanWarningCode.SLOT_RELAXED and w.exercise_id == chosen[0].id
    ]
    assert relaxed
    assert "sin material no hay un empuje vertical seguro" in relaxed[0].message_es


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
    loose = prescribe_working(CARDS["0294"], slot, 3, inp, TABLES, week_rir=2, circuit=False)
    day.blocks = [
        DraftBlock(kind=BlockKind.MAIN, exercises=[loose]),
        DraftBlock(kind=BlockKind.SUPERSET, exercises=pair, rounds=3, rest_between_rounds_s=200),
    ]
    fitter = _Fitter(day, 60, TABLES, CreditCache(CARDS, TABLES))
    fitter.reduce_accessory_rests()
    assert day.blocks[1].rest_between_rounds_s == max(e.rest_floor_s for e in pair)
    assert loose.rest_s == loose.rest_floor_s


def test_finisher_is_skipped_without_cardio_exercises() -> None:
    no_cardio = [c for c in catalog() if c.role is not ExerciseRole.CARDIO]
    plan = generate(make_input(goal=Goal.FAT_LOSS, session_minutes=90), no_cardio)
    kinds = {b.kind for w in plan.weeks for d in w.days for b in d.blocks}
    assert BlockKind.FINISHER not in kinds


def test_warmup_can_be_disabled() -> None:
    plan = generate(make_input(include_warmup=False), catalog())
    assert all(d.blocks[0].kind is not BlockKind.WARMUP for d in plan.weeks[0].days)


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

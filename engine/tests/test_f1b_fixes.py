"""Hallazgos de la revisión F1b (B1-B5, B8, C2-C9, C16): reglas de seguridad y prescripción."""

import itertools
from collections.abc import Iterator

import pytest

from forja_engine import generate
from forja_engine.models import (
    BlockKind,
    EquipmentPreset,
    ExerciseCard,
    ExerciseRole,
    Experience,
    Goal,
    MovementPattern,
    MuscleCode,
    MuscleGroup,
    PlanBlock,
    PlanDay,
    PlanExercise,
    PlanWarningCode,
    PlanWeek,
    ProgramPlan,
    SlotRef,
)
from forja_engine.normalize import normalize_input
from forja_engine.periodize import undulated_reps
from forja_engine.select import Selector, UsageState
from forja_engine.split import build_days
from forja_engine.tables import default_tables
from tests.helpers import catalog, equipment_for, make_input

TABLES = default_tables()
RULES = TABLES.engine_rules
CARDS = {c.id: c for c in catalog()}
PRESETS = (
    EquipmentPreset.FULL_GYM,
    EquipmentPreset.HOME_DUMBBELLS,
    EquipmentPreset.HOME_BANDS,
    EquipmentPreset.BODYWEIGHT,
)
MAX_DIFFICULTY = 2
WORKING = {BlockKind.MAIN, BlockKind.SUPERSET, BlockKind.CIRCUIT}


def _cards(
    plan: ProgramPlan,
) -> Iterator[tuple[PlanWeek, PlanDay, PlanBlock, PlanExercise, ExerciseCard]]:
    for week in plan.weeks:
        for day in week.days:
            for block in day.blocks:
                for exercise in block.exercises:
                    yield week, day, block, exercise, CARDS[exercise.exercise_id]


@pytest.mark.parametrize(
    ("goal", "level", "preset"),
    list(
        itertools.product(
            (Goal.HYPERTROPHY, Goal.STRENGTH, Goal.ENDURANCE, Goal.FAT_LOSS),
            (Experience.BEGINNER, Experience.INTERMEDIATE),
            PRESETS,
        )
    ),
)
def test_safety_and_bounds_properties(
    goal: Goal, level: Experience, preset: EquipmentPreset
) -> None:
    plan = generate(
        make_input(goal=goal, experience=level, equipment=equipment_for(preset), days_per_week=4),
        catalog(),
    )
    table = TABLES.prescription.table[goal]
    for week, _day, block, exercise, card in _cards(plan):
        assert card.difficulty <= MAX_DIFFICULTY  # B3
        assert not RULES.skill_gated.matches(card)
        assert card.id not in RULES.low_quality_ids
        assert not RULES.contraindicated_default.matches(card)  # B8
        if preset in RULES.fixture_gated.presets:
            assert not RULES.fixture_gated.matches(card)  # B5
        slot = exercise.slot
        if (
            block.kind in WORKING
            and slot is not None
            and slot.role in {ExerciseRole.MAIN, ExerciseRole.ACCESSORY}
            and week.phase.value != "deload"
        ):
            rx = table["main" if slot.role is ExerciseRole.MAIN else "accessory"]
            late = 1 if week.index >= 2 and level is not Experience.BEGINNER else 0
            assert exercise.sets <= rx.sets[1] + late  # B2
            if level is Experience.BEGINNER:
                assert exercise.sets <= rx.sets[0]
        if (
            slot is not None
            and slot.role is ExerciseRole.MAIN
            and slot.pattern in {MovementPattern.SQUAT, MovementPattern.HINGE}
        ):
            assert card.mechanic.value == "compound"  # C2


def test_full_gym_main_squat_and_hinge_use_real_lifts() -> None:
    plan = generate(make_input(experience=Experience.ADVANCED, days_per_week=5), catalog())
    mains = {
        e.exercise_id
        for _, _, _, e, _ in _cards(plan)
        if e.slot is not None
        and e.slot.role is ExerciseRole.MAIN
        and e.slot.pattern in {MovementPattern.SQUAT, MovementPattern.HINGE}
    }
    assert mains
    assert not mains & {"1760", "3533", "0044"}  # B1


def test_heavy_and_medium_days_respect_the_rep_floor() -> None:
    plan = generate(make_input(goal=Goal.STRENGTH, experience=Experience.INTERMEDIATE), catalog())
    ranges = {
        (e.rep_min, e.target_rir)
        for week, _, block, e, _ in _cards(plan)
        if block.kind is BlockKind.MAIN
        and e.slot is not None
        and e.slot.role is ExerciseRole.MAIN
        and week.phase.value != "deload"
    }
    assert all(low is not None and low >= 3 for low, _ in ranges)
    assert all(rir is not None and rir >= 2 for _, rir in ranges)
    undulation = TABLES.periodization.strength_undulation
    assert undulated_reps((3, 6), heavy=True, undulation=undulation) == (3, 5)
    assert undulated_reps((3, 6), heavy=False, undulation=undulation) == (4, 7)
    rationale = " ".join(plan.rationale_es)
    assert "3-5" in rationale
    assert "4-7" in rationale


def test_excluded_and_non_loadable_exercises_do_not_undulate() -> None:
    undulation = TABLES.periodization.strength_undulation
    assert not undulation.undulates(CARDS["0044"])  # buenos días
    bodyweight = next(c for c in catalog() if c.load_type.value == "bodyweight")
    assert not undulation.undulates(bodyweight)


def test_gates_yield_to_favorites_and_match_whole_words() -> None:
    gated = next(c for c in catalog() if RULES.skill_gated.matches(c))
    plain = normalize_input(make_input(), TABLES)
    usable = Selector(catalog(), plain, TABLES).usable.get(gated.movement_pattern, [])
    assert gated.id not in {c.id for c in usable}
    fav = normalize_input(make_input(favorite_exercise_ids=(gated.id,)), TABLES)
    usable = Selector(catalog(), fav, TABLES).usable[gated.movement_pattern]
    assert gated.id in {c.id for c in usable}
    spring = CARDS["0043"].model_copy(update={"display_name_en": "spring squat"})
    assert not RULES.fixture_gated.matches(spring)
    ring = spring.model_copy(update={"display_name_en": "ring dips"})
    assert RULES.fixture_gated.matches(ring)


def test_lumbar_limitation_removes_hinge_and_bent_over_variants() -> None:
    plan = generate(make_input(avoid_muscles=(MuscleCode.LOWER_BACK,), days_per_week=5), catalog())
    for _, _, _, _, card in _cards(plan):
        assert card.movement_pattern is not MovementPattern.HINGE
        assert not RULES.lumbar_avoid.matches(card)
    assert any(w.code is PlanWarningCode.AVOIDED_MUSCLE_SUBSTITUTED for w in plan.warnings)


def test_recovery_day_is_low_impact_with_mobility() -> None:
    plan = generate(make_input(days_per_week=7), catalog())
    day = next(d for d in plan.weeks[0].days if d.template == "active_recovery")
    exercises = [CARDS[e.exercise_id] for b in day.blocks for e in b.exercises]
    cardio = [c for c in exercises if c.role is ExerciseRole.CARDIO]
    assert len(cardio) == 1
    recovery = RULES.recovery
    assert cardio[0].equipment_code in recovery.cardio_equipment_any or (
        cardio[0].id in recovery.cardio_ids_any
    )
    assert len(exercises) - len(cardio) >= 5


def test_strength_warmup_uses_approach_sets_on_the_main_lift() -> None:
    plan = generate(make_input(goal=Goal.STRENGTH), catalog())
    day = plan.weeks[0].days[0]
    warmup = next(b for b in day.blocks if b.kind is BlockKind.WARMUP)
    ramp = warmup.exercises[-1]
    main = next(b for b in day.blocks if b.kind is BlockKind.MAIN).exercises[0]
    assert ramp.exercise_id == main.exercise_id
    assert ramp.sets == len(TABLES.periodization.progression.warmup_ramp)


def test_bodyweight_pullups_are_capped_in_endurance() -> None:
    plan = generate(
        make_input(goal=Goal.ENDURANCE, experience=Experience.INTERMEDIATE, days_per_week=3),
        catalog(),
    )
    limits = TABLES.prescription.bodyweight_rep_limits
    for _, _, _, e, card in _cards(plan):
        if e.rep_max is not None and card.load_type.value == "bodyweight" and limits.matches(card):
            assert e.rep_max <= limits.max


def test_isolation_never_precedes_compound_straight_sets() -> None:
    plan = generate(make_input(goal=Goal.FAT_LOSS, days_per_week=4), catalog())
    for day in plan.weeks[0].days:
        kinds = [
            any(CARDS[e.exercise_id].mechanic.value == "isolation" for e in b.exercises)
            for b in day.blocks
            if b.kind in {BlockKind.MAIN, BlockKind.SUPERSET}
        ]
        assert kinds == sorted(kinds)


def test_fallback_cards_degrade_when_difficulty_cap_leaves_nothing() -> None:
    inp = normalize_input(make_input(experience=Experience.BEGINNER), TABLES)
    hard = [c.model_copy(update={"difficulty": 3}) for c in catalog()]
    selector = Selector(hard, inp, TABLES)
    assert selector.fallback_cards()
    slot = build_days(inp, TABLES)[0].slots[0]
    assert not selector.candidates(slot, RULES.relaxation_order, UsageState())


# ---------------------------------------------------------------- cierre de B5 (0.2.1)
BAR_FREE_PRESETS = (EquipmentPreset.BODYWEIGHT, EquipmentPreset.HOME_BANDS)
FIXED_STRUCTURE_EQUIPMENT = {"cable", "machine", "smith", "barbell", "trap_bar", "ez_bar", "sled"}
FIXED_STRUCTURE_WORDS = ("pull-up", "chin", "ring", "bench", "cable", "dip", "hanging")


@pytest.mark.parametrize("preset", BAR_FREE_PRESETS)
def test_no_fixed_structure_exercise_is_selectable_without_bar_or_bench(
    preset: EquipmentPreset,
) -> None:
    inp = make_input(equipment=equipment_for(preset))
    selector = Selector(catalog(), inp, TABLES)
    offenders = []
    for cards in selector.available.values():
        for card in cards:
            name = card.display_name_en.lower()
            if card.equipment_code.value in FIXED_STRUCTURE_EQUIPMENT or any(
                word in name for word in FIXED_STRUCTURE_WORDS
            ):
                offenders.append((card.id, card.display_name_en))
    assert offenders == []
    ids = {c.id for cards in selector.available.values() for c in cards}
    assert not {"0720", "2400"} & ids


def test_band_assisted_pull_up_is_not_selectable_with_home_dumbbells() -> None:
    inp = make_input(equipment=equipment_for(EquipmentPreset.HOME_DUMBBELLS))
    selector = Selector(catalog(), inp, TABLES)
    ids = {c.id for cards in selector.usable.values() for c in cards}
    assert "0970" not in ids


def test_assisted_machine_is_never_main_for_advanced_strength() -> None:
    inp = make_input(goal=Goal.STRENGTH, experience=Experience.ADVANCED)
    selector = Selector(catalog(), inp, TABLES)
    slot = SlotRef(
        slot_index=0,
        pattern=MovementPattern.VERTICAL_PULL,
        role=ExerciseRole.MAIN,
        group=MuscleGroup.BACK,
        priority=1,
    )
    for relaxed in ((), tuple(RULES.relaxation_order)):
        assert "0017" not in {c.id for c in selector.candidates(slot, relaxed, UsageState())}
    for _, _, block, exercise, _ in _cards(generate(inp, catalog())):
        if block.kind is BlockKind.MAIN:
            assert exercise.exercise_id != "0017"


def _elbow_ext_slots(days: int, **kw: object) -> list[SlotRef]:
    inp = make_input(days_per_week=days, **kw)
    return [
        s
        for d in build_days(inp, TABLES)
        for s in d.slots
        if s.pattern is MovementPattern.ELBOW_EXTENSION
    ]


def test_arms_block_only_for_hypertrophy_or_toning_non_beginners() -> None:
    def extra(goal: Goal, level: Experience) -> int:
        kw = {"goal": goal, "experience": level}
        return len(_elbow_ext_slots(4, emphasis="arms", **kw)) - len(
            _elbow_ext_slots(4, emphasis="balanced", **kw)
        )

    assert extra(Goal.HYPERTROPHY, Experience.INTERMEDIATE) > 0
    assert extra(Goal.HYPERTROPHY, Experience.BEGINNER) == 0
    assert extra(Goal.GENERAL_FITNESS, Experience.INTERMEDIATE) == 0


def test_general_fitness_elbow_extension_low_priority_then_dropped() -> None:
    def extra(days: int) -> list[int]:
        kw = {"goal": Goal.GENERAL_FITNESS, "experience": Experience.INTERMEDIATE}
        base = [s.priority for s in _elbow_ext_slots(days, emphasis="balanced", **kw)]
        boosted = [s.priority for s in _elbow_ext_slots(days, emphasis="upper_body", **kw)]
        for priority in base:
            boosted.remove(priority)
        return boosted

    assert extra(4)
    assert set(extra(4)) == {3}
    assert extra(5) == []


def test_beginner_emphasis_rationale_mentions_exercise_choice() -> None:
    plan = generate(make_input(emphasis="arms", experience=Experience.BEGINNER), catalog())
    assert "elección de ejercicios, no con series extra" in " ".join(plan.rationale_es)

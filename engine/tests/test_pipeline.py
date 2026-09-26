"""Pasos del pipeline (§7.2) y caminos degradados: nunca excepción por falta de candidatos."""

import pytest
from pydantic import ValidationError

from forja_engine import generate
from forja_engine.allocate import allocate_sets, enforce_session_cap, pick_from_range
from forja_engine.compose import volume_ratio
from forja_engine.draft import DraftBlock, DraftDay
from forja_engine.generator import CreditCache, build_plan
from forja_engine.models import (
    BlockKind,
    Emphasis,
    EquipmentCode,
    EquipmentPreset,
    EquipmentSelection,
    ExerciseCard,
    ExerciseRole,
    Experience,
    Goal,
    LoadType,
    MovementPattern,
    MuscleGroup,
    PlanWarningCode,
    SlotRef,
    VolumeGroup,
    WeekPhase,
)
from forja_engine.normalize import normalize_input, rng_for
from forja_engine.periodize import periodize
from forja_engine.prescribe import load_hint, prescribe_working
from forja_engine.select import Choice, Selector, UsageState, relaxation_warning
from forja_engine.split import DaySpec, build_days, split_templates
from forja_engine.tables import Relaxation, default_tables
from forja_engine.timefit import fit_day
from forja_engine.volume import GroupTarget, weekly_targets
from tests.helpers import catalog, make_input

TABLES = default_tables()


def card(**overrides: object) -> ExerciseCard:
    base = next(c for c in catalog() if c.id == "0043")
    return base.model_copy(update=overrides)


def slot(
    pattern: MovementPattern, role: ExerciseRole, group: MuscleGroup, index: int = 0
) -> SlotRef:
    return SlotRef(slot_index=index, pattern=pattern, role=role, group=group, priority=1)


# ------------------------------------------------------------------------ paso 1-3
@pytest.mark.parametrize(
    ("days", "level", "expected"),
    [
        (1, Experience.BEGINNER, ["full_body_a"]),
        (2, Experience.ADVANCED, ["upper_a", "lower_a"]),
        (3, Experience.ADVANCED, ["push", "pull", "legs"]),
        (4, Experience.INTERMEDIATE, ["upper_a", "lower_a", "upper_b", "lower_b"]),
        (5, Experience.INTERMEDIATE, ["upper_a", "lower_a", "push", "pull", "legs"]),
        (6, Experience.BEGINNER, ["push", "pull", "legs"] * 2),
        (
            7,
            Experience.ADVANCED,
            ["push", "pull", "legs", "active_recovery", "push", "pull", "legs"],
        ),
    ],
)
def test_split_table_matches_section_7_3(days: int, level: Experience, expected: list[str]) -> None:
    assert split_templates(make_input(days_per_week=days, experience=level), TABLES) == expected


def test_lower_glutes_replaces_the_last_upper_or_push_day() -> None:
    inp = make_input(emphasis="lower_glutes")
    assert split_templates(inp, TABLES) == ["upper_a", "lower_a", "glutes_hams", "lower_b"]
    assert split_templates(make_input(emphasis="lower_glutes", days_per_week=3), TABLES)[0] == (
        "full_body_a"
    )


def test_replacement_is_skipped_when_no_day_matches() -> None:
    splits = TABLES.split_templates
    override = splits.emphasis_overrides[Emphasis.LOWER_GLUTES].model_copy(
        update={"replace_last_of": ("active_recovery",)}
    )
    tables = TABLES.model_copy(
        update={
            "split_templates": splits.model_copy(
                update={
                    "emphasis_overrides": {
                        **splits.emphasis_overrides,
                        Emphasis.LOWER_GLUTES: override,
                    }
                }
            )
        }
    )
    assert "glutes_hams" not in split_templates(make_input(emphasis="lower_glutes"), tables)


def test_emphasis_blocks_are_appended_to_matching_days() -> None:
    days = build_days(
        make_input(emphasis="arms", days_per_week=4, preferred_days=("mon", "tue", "thu", "fri")),
        TABLES,
    )
    with_arms = [d for d in days if d.slots[-1].pattern is MovementPattern.ELBOW_EXTENSION]
    assert [d.template for d in with_arms] == ["upper_a", "upper_b"]  # nunca días de pierna
    assert [d.weekday for d in days] == ["mon", "tue", "thu", "fri"]
    core_days = build_days(make_input(emphasis="core"), TABLES)
    assert core_days[0].slots[-1].role is ExerciseRole.CORE


def test_emphasis_raises_targets_but_keeps_maintenance_floor() -> None:
    balanced = weekly_targets(make_input(), TABLES)
    glutes = weekly_targets(make_input(emphasis="lower_glutes"), TABLES)
    assert glutes[VolumeGroup.GLUTES].target > balanced[VolumeGroup.GLUTES].target
    floor = TABLES.volume_targets.maintenance_floor_ratio
    assert glutes[VolumeGroup.CHEST].target >= balanced[VolumeGroup.CHEST].target_min * floor


def test_seed_is_derived_when_missing_and_stable() -> None:
    first = normalize_input(make_input(seed=None), TABLES)
    second = normalize_input(make_input(seed=None), TABLES)
    assert first.seed is not None
    assert first.seed == second.seed
    other = normalize_input(make_input(seed=None, days_per_week=3), TABLES)
    assert other.seed != first.seed


def test_normalization_resolves_presets_and_defaults() -> None:
    inp = normalize_input(
        make_input(
            goal=Goal.FAT_LOSS,
            equipment=EquipmentSelection(
                preset=EquipmentPreset.CUSTOM, items=(EquipmentCode.KETTLEBELL,)
            ),
            avoid_muscles=("quads", "chest"),
        ),
        TABLES,
    )
    assert inp.equipment.items == ("bodyweight", "kettlebell")
    assert inp.avoid_muscles == ("chest", "quads")
    assert inp.include_cardio_finisher is True
    assert normalize_input(make_input(include_warmup=False), TABLES).include_warmup is False


def test_safety_warnings_for_beginners_and_seven_days() -> None:
    plan = generate(make_input(days_per_week=7, experience=Experience.BEGINNER), catalog())
    codes = {w.code for w in plan.warnings}
    assert {PlanWarningCode.BEGINNER_HIGH_FREQUENCY, PlanWarningCode.RECOVERY_DAY_ENFORCED} <= codes
    recovery = plan.weeks[0].days[3]
    assert recovery.is_recovery
    assert {b.kind for b in recovery.blocks} == {BlockKind.MAIN, BlockKind.COOLDOWN}


# ------------------------------------------------------------------------ paso 4
def test_allocation_skips_non_strength_slots_and_respects_the_session_cap() -> None:
    chest = [
        slot(MovementPattern.HORIZONTAL_PUSH, ExerciseRole.MAIN, MuscleGroup.CHEST, i)
        for i in range(3)
    ]
    cardio = slot(MovementPattern.CARDIO, ExerciseRole.CARDIO, MuscleGroup.CARDIO, 3)
    day = DaySpec(0, "custom", "Custom", (*chest, cardio), is_recovery=False, weekday=None)
    targets = {g: GroupTarget(g, 30, 40, 35) for g in weekly_targets(make_input(), TABLES)}
    sets = allocate_sets(
        [day], targets, Goal.HYPERTROPHY, Experience.INTERMEDIATE, TABLES, circuit=False
    )
    assert (0, 3) not in sets
    assert sum(sets.values()) <= 10
    assert all(v >= 2 for v in sets.values())


def test_session_cap_trims_selected_exercises_and_circuits() -> None:
    bench = card(id="0025", target_muscle="chest", movement_pattern=MovementPattern.HORIZONTAL_PUSH)
    fly = card(
        id="0308",
        target_muscle="chest",
        movement_pattern=MovementPattern.CHEST_FLY,
        mechanic="isolation",
    )
    credits = CreditCache({c.id: c for c in (bench, fly)}, TABLES)
    inp = normalize_input(make_input(), TABLES)
    push = slot(MovementPattern.HORIZONTAL_PUSH, ExerciseRole.MAIN, MuscleGroup.CHEST)
    exercises = [
        prescribe_working(c, push, 6, inp, TABLES, week_rir=2, circuit=False) for c in (bench, fly)
    ]
    day = DraftDay(0, "t", "Día", "", is_recovery=False, weekday=None)
    day.blocks = [DraftBlock(kind=BlockKind.MAIN, exercises=[e]) for e in exercises]
    warnings = enforce_session_cap(day, credits, 10)
    assert [w.code for w in warnings] == [PlanWarningCode.SESSION_GROUP_CAP]
    assert sum(e.sets for e in exercises) == 10
    for exercise in exercises:
        exercise.sets = 6
    day.blocks = [DraftBlock(kind=BlockKind.CIRCUIT, exercises=exercises, rounds=6)]
    enforce_session_cap(day, credits, 10)
    assert day.blocks[0].rounds == 5
    assert all(e.sets == 5 for e in exercises)


def test_pick_from_range_rules() -> None:
    assert [pick_from_range((2, 5), r) for r in ("min", "mid", "max")] == [2, 3, 5]


# ------------------------------------------------------------------------ paso 5
def test_relaxation_chain_and_warnings() -> None:
    inp = normalize_input(
        make_input(
            equipment=EquipmentSelection(preset=EquipmentPreset.BODYWEIGHT),
            avoid_patterns=("squat",),
        ),
        TABLES,
    )
    selector = Selector(catalog(), inp, TABLES)
    squat = slot(MovementPattern.SQUAT, ExerciseRole.MAIN, MuscleGroup.QUADS)
    choice = selector.choose(squat, rng_for(1), UsageState())
    assert choice is not None
    assert "pattern_affinity" in choice.relaxed
    warning = relaxation_warning(selector, squat, choice, 0, "Pierna")
    assert warning is not None
    assert warning.code is PlanWarningCode.AVOIDED_MUSCLE_SUBSTITUTED


@pytest.mark.parametrize(
    ("relaxed", "fragment"),
    [
        (("difficulty",), "dificultad"),
        (("difficulty", "staple", "target_group"), "otro músculo"),
        ((), None),
    ],
)
def test_relaxation_messages(relaxed: tuple[Relaxation, ...], fragment: str | None) -> None:
    inp = normalize_input(make_input(), TABLES)
    selector = Selector(catalog(), inp, TABLES)
    squat = slot(MovementPattern.SQUAT, ExerciseRole.MAIN, MuscleGroup.QUADS)
    choice = Choice(card=card(), alternatives=(), relaxed=relaxed)
    warning = relaxation_warning(selector, squat, choice, 0, "Pierna")
    if fragment is None:
        assert warning is None
    else:
        assert warning is not None
        assert fragment in warning.message_es


def test_dropped_slots_explain_equipment_or_exclusions() -> None:
    lonely = card(
        id="0001",
        movement_pattern=MovementPattern.FOREARM,
        equipment_code="dumbbell",
        role=ExerciseRole.ACCESSORY,
    )
    only_barbell = card(id="0002", movement_pattern=MovementPattern.SQUAT, equipment_code="barbell")
    inp = make_input(
        equipment=EquipmentSelection(preset=EquipmentPreset.HOME_DUMBBELLS), days_per_week=1
    )
    plan = generate(inp, [lonely, only_barbell])
    codes = [w.code for w in plan.warnings]
    assert PlanWarningCode.EQUIPMENT_INSUFFICIENT in codes
    assert PlanWarningCode.SLOT_DROPPED in codes
    assert PlanWarningCode.EMPTY_DAY in codes
    assert plan.weeks[0].days[0].blocks[0].exercises[0].exercise_id == "0001"


def test_fallback_day_with_only_mobility_available() -> None:
    stretch = next(c for c in catalog() if c.role is ExerciseRole.MOBILITY)
    plan = generate(make_input(days_per_week=1), [stretch])
    day = plan.weeks[0].days[0]
    assert day.blocks[0].kind is BlockKind.COOLDOWN
    assert day.focus_es == "Sesión adaptada a tu equipamiento"


def test_empty_pool_is_an_invalid_input() -> None:
    with pytest.raises(ValidationError, match="ningún ejercicio disponible"):
        generate(make_input(excluded_exercise_ids=("0043",)), [card()])


def test_cooldown_fills_with_any_mobility_and_warmup_can_be_reduced() -> None:
    inp = normalize_input(make_input(), TABLES)
    selector = Selector(catalog(), inp, TABLES)
    picked = selector.cooldown([MuscleGroup.CARDIO], 3, rng_for(3), UsageState())
    assert len(picked) == 3
    rules = TABLES.engine_rules.model_copy(
        update={"warmup": TABLES.engine_rules.warmup.model_copy(update={"specific_items": 0})}
    )
    plan = build_plan(make_input(), catalog(), TABLES.model_copy(update={"engine_rules": rules}))
    assert len(plan.weeks[0].days[0].blocks[0].exercises) == 1


# ------------------------------------------------------------------------ paso 6
def test_load_hints_by_load_type() -> None:
    assert load_hint(card(load_type=LoadType.TIME), 2) == "Mantén la posición con técnica impecable"
    assert load_hint(card(), None) is None
    assert load_hint(card(load_type=LoadType.BODYWEIGHT), 1) == (
        "Con tu peso corporal, deja 1 repetición en reserva"
    )
    assert "asistencia" in (load_hint(card(load_type=LoadType.ASSISTED), 2) or "")


def test_endurance_uses_circuits_with_short_station_rest() -> None:
    plan = generate(make_input(goal=Goal.ENDURANCE, emphasis="core"), catalog())
    circuit = next(b for b in plan.weeks[0].days[0].blocks if b.kind is BlockKind.CIRCUIT)
    assert all(e.sets == circuit.rounds for e in circuit.exercises)


# ------------------------------------------------------------------------ paso 7
def test_tight_budget_trims_mains_and_warns() -> None:
    plan = generate(
        make_input(
            goal=Goal.STRENGTH, experience=Experience.ADVANCED, session_minutes=20, days_per_week=1
        ),
        catalog(),
    )
    codes = {w.code for w in plan.warnings}
    assert PlanWarningCode.MAIN_EXERCISE_TRIMMED in codes
    assert PlanWarningCode.SLOT_DROPPED in codes


def test_fit_day_reports_when_even_one_exercise_does_not_fit() -> None:
    inp = normalize_input(make_input(goal=Goal.STRENGTH), TABLES)
    main = slot(MovementPattern.SQUAT, ExerciseRole.MAIN, MuscleGroup.QUADS)
    exercise = prescribe_working(card(), main, 2, inp, TABLES, week_rir=2, circuit=False)
    exercise.duration_s, exercise.rep_min, exercise.rep_max = 900, None, None
    day = DraftDay(0, "t", "Día", "", is_recovery=False, weekday=None)
    day.blocks = [DraftBlock(kind=BlockKind.MAIN, exercises=[exercise])]
    credits = CreditCache({"0043": card()}, TABLES)
    warnings = fit_day(day, 20, TABLES, credits)
    assert PlanWarningCode.TIME_BUDGET_EXCEEDED in {w.code for w in warnings}


def test_superset_rests_shrink_when_accessory_rests_are_reduced() -> None:
    plan = generate(make_input(goal=Goal.TONING, session_minutes=45, days_per_week=4), catalog())
    kinds = {b.kind for w in plan.weeks for d in w.days for b in d.blocks}
    assert BlockKind.SUPERSET in kinds
    for week in plan.weeks:
        for day in week.days:
            for block in day.blocks:
                if block.kind is BlockKind.SUPERSET:
                    assert block.rest_between_rounds_s == max(e.rest_s for e in block.exercises)


# ------------------------------------------------------------------------ paso 8-9
def test_strength_undulation_and_intensification() -> None:
    plan = generate(
        make_input(goal=Goal.STRENGTH, experience=Experience.ADVANCED, weeks=6), catalog()
    )
    phases = [w.phase for w in plan.weeks]
    assert WeekPhase.INTENSIFICATION in phases
    assert phases[-1] is WeekPhase.DELOAD
    notes = {e.notes_es for d in plan.weeks[0].days for b in d.blocks for e in b.exercises}
    assert any(n and n.startswith("Día pesado") for n in notes)
    assert any(n and n.startswith("Día medio") for n in notes)


def test_undulation_keeps_timed_mains_untouched() -> None:
    inp = normalize_input(make_input(goal=Goal.STRENGTH, experience=Experience.ADVANCED), TABLES)
    plank = card(load_type=LoadType.TIME)
    main = slot(MovementPattern.SQUAT, ExerciseRole.MAIN, MuscleGroup.QUADS)
    exercise = prescribe_working(plank, main, 3, inp, TABLES, week_rir=3, circuit=False)
    day = DraftDay(0, "t", "Día", "", is_recovery=False, weekday=None)
    day.blocks = [DraftBlock(kind=BlockKind.MAIN, exercises=[exercise])]
    weeks = periodize([day], inp, TABLES, weekly_targets(inp, TABLES), CreditCache({}, TABLES))
    assert weeks[0].days[0].blocks[0].exercises[0].rep_min is None


def test_beginners_progress_linearly_without_extra_sets() -> None:
    plan = generate(make_input(experience=Experience.BEGINNER), catalog())
    assert plan.weeks[1].volume_ratio == plan.weeks[0].volume_ratio == 1.0
    advanced = generate(make_input(experience=Experience.ADVANCED, session_minutes=120), catalog())
    assert advanced.weeks[2].volume_ratio > 1.0


def test_volume_ratio_without_base_volume() -> None:
    assert volume_ratio([], []) == 1.0

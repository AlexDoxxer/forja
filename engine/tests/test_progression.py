"""§7.6: doble progresión, fallos repetidos, peso corporal, e1RM y aproximación con discos."""

from datetime import date

import pytest

from forja_engine.models import (
    BodyPart,
    EquipmentCode,
    ExerciseCard,
    ExerciseHistoryEntry,
    ExercisePrescription,
    LoadType,
    Mechanic,
    MovementPattern,
    PerformedSet,
    SuggestionKind,
)
from forja_engine.progression import (
    estimate_1rm,
    harder_variant,
    plates_per_side,
    round_load,
    suggest,
    warmup_ramp,
)
from forja_engine.tables import default_tables
from tests.helpers import catalog

TABLES = default_tables()
BY_ID = {c.id: c for c in catalog()}
SQUAT = BY_ID["0043"]
BENCH = next(
    c
    for c in catalog()
    if c.equipment_code is EquipmentCode.BARBELL
    and c.movement_pattern is MovementPattern.HORIZONTAL_PUSH
    and c.mechanic is Mechanic.COMPOUND
)
CURL = next(
    c
    for c in catalog()
    if c.equipment_code is EquipmentCode.DUMBBELL
    and c.movement_pattern is MovementPattern.ELBOW_FLEXION
)
CABLE_ISOLATION = next(
    c
    for c in catalog()
    if c.equipment_code is EquipmentCode.CABLE and c.mechanic is Mechanic.ISOLATION
)
PUSH_UP = next(
    c
    for c in catalog()
    if c.load_type is LoadType.BODYWEIGHT
    and c.movement_pattern is MovementPattern.HORIZONTAL_PUSH
    and harder_variant(c, catalog()) is not None
)
TIMED = next(c for c in catalog() if c.load_type is LoadType.TIME and harder_variant(c, catalog()))
ASSISTED = next(c for c in catalog() if c.load_type is LoadType.ASSISTED)


def rx(
    rep_min: int | None = 3, rep_max: int | None = 6, duration: int | None = None
) -> ExercisePrescription:
    return ExercisePrescription(
        exercise_id="0043",
        sets=3,
        rep_min=rep_min,
        rep_max=rep_max,
        duration_s=duration,
        per_side=False,
        target_rir=2,
        tempo=None,
        rest_s=120,
        load_hint=None,
        notes_es=None,
        alternatives=(),
    )


def session(day: int, *sets: tuple[float | None, int | None, int | None]) -> ExerciseHistoryEntry:
    return ExerciseHistoryEntry(
        session_date=date(2026, 9, day),
        sets=(
            PerformedSet(weight_kg=40, reps=10, is_warmup=True),
            *(PerformedSet(weight_kg=w, reps=r, rir=rir) for w, r, rir in sets),
        ),
    )


def test_estimate_1rm_epley() -> None:
    assert estimate_1rm(100, 5) == pytest.approx(116.67)
    assert estimate_1rm(100, 5, rir=2) == pytest.approx(123.33)
    assert estimate_1rm(100, 9, rir=2) is None
    assert estimate_1rm(0, 5) is None
    assert estimate_1rm(100, 0) is None


def test_plate_math_and_rounding() -> None:
    assert plates_per_side(100, TABLES) == (25, 15)
    assert round_load(101, EquipmentCode.BARBELL, TABLES) == (100.0, (25, 15))
    assert round_load(12, EquipmentCode.BARBELL, TABLES) == (20, ())
    assert round_load(13, EquipmentCode.DUMBBELL, TABLES) == (14.0, ())
    assert round_load(0.3, EquipmentCode.CABLE, TABLES) == (2.5, ())


def test_warmup_ramp() -> None:
    ramp = warmup_ramp(100, LoadType.EXTERNAL, EquipmentCode.BARBELL)
    assert [(s.percent, s.reps, s.weight_kg) for s in ramp] == [
        (0.4, 8, 40.0),
        (0.6, 5, 60.0),
        (0.8, 2, 80.0),
    ]
    assert ramp[0].plates_per_side_kg == (10.0,)
    assert warmup_ramp(100, LoadType.BODYWEIGHT, EquipmentCode.BODYWEIGHT) == ()
    assert warmup_ramp(0, LoadType.EXTERNAL, EquipmentCode.BARBELL) == ()


def test_first_time() -> None:
    assert suggest(rx(), SQUAT, [], catalog()).kind is SuggestionKind.FIRST_TIME
    warmup_only = ExerciseHistoryEntry(
        session_date=date(2026, 9, 1), sets=(PerformedSet(weight_kg=20, reps=10, is_warmup=True),)
    )
    no_rir = rx().model_copy(update={"target_rir": None})
    result = suggest(no_rir, SQUAT, [warmup_only], catalog())
    assert result.kind is SuggestionKind.FIRST_TIME
    assert "reserva" not in result.reason_es


@pytest.mark.parametrize(
    ("card", "increment"),
    [(SQUAT, 5.0), (BENCH, 2.5), (CURL, 2.0), (CABLE_ISOLATION, 1.25)],
)
def test_increase_load_by_exercise_type(card: ExerciseCard, increment: float) -> None:
    history = [session(1, (60, 6, 2), (60, 6, 3))]
    result = suggest(rx(), card, history, catalog())
    assert result.kind is SuggestionKind.INCREASE_LOAD
    expected, _ = round_load(60 + increment, card.equipment_code, TABLES)
    assert result.suggested_weight_kg == expected


def test_lower_body_barbell_gets_plates_and_warmups() -> None:
    result = suggest(rx(), SQUAT, [session(1, (100, 6, None))], catalog())
    assert SQUAT.body_part is BodyPart.UPPER_LEGS
    assert result.suggested_weight_kg == 105
    assert result.plates_per_side_kg == (25.0, 15.0, 2.5)
    assert len(result.warmup_sets) == 3


def test_hold_and_decrease_after_repeated_misses() -> None:
    hold = suggest(rx(), SQUAT, [session(1, (100, 5, 2))], catalog())
    assert hold.kind is SuggestionKind.HOLD
    assert hold.suggested_weight_kg == 100
    small = [session(1, (100, 2, 0)), session(2, (100, 2, 0))]
    assert suggest(rx(), SQUAT, small, catalog()).suggested_weight_kg == 95
    big = [session(1, (100, 1, 0)), session(2, (100, 1, 0))]
    result = suggest(rx(), SQUAT, big, catalog())
    assert result.kind is SuggestionKind.DECREASE_LOAD
    assert result.suggested_weight_kg == 90
    one_miss = suggest(rx(), SQUAT, [session(1, (100, 1, 0))], catalog())
    assert one_miss.kind is SuggestionKind.HOLD


def test_missing_weights_ask_to_log() -> None:
    result = suggest(rx(), SQUAT, [session(1, (None, 6, 2))], catalog())
    assert result.kind is SuggestionKind.HOLD
    assert result.suggested_weight_kg is None


def test_assisted_progression_reduces_assistance() -> None:
    up = suggest(rx(8, 12), ASSISTED, [session(1, (30, 12, 2))], catalog())
    assert up.kind is SuggestionKind.INCREASE_LOAD
    assert up.suggested_weight_kg is not None
    assert up.suggested_weight_kg < 30
    assert "asistencia" in up.reason_es
    down = suggest(rx(8, 12), ASSISTED, [session(1, (30, 6, 0)), session(2, (30, 6, 0))], catalog())
    assert down.suggested_weight_kg == pytest.approx(33.0)


def test_bodyweight_progression() -> None:
    top = [session(1, (None, 12, 2))]
    assert suggest(rx(8, 12), PUSH_UP, [session(1, (None, 9, 2))], catalog()).kind is (
        SuggestionKind.HOLD
    )
    more = suggest(rx(8, 12), PUSH_UP, top, catalog())
    assert more.kind is SuggestionKind.INCREASE_REPS
    assert (more.suggested_rep_min, more.suggested_rep_max) == (10, 14)
    harder = suggest(rx(15, 20), PUSH_UP, [session(1, (None, 20, 2))], catalog())
    assert harder.kind is SuggestionKind.HARDER_VARIANT
    assert harder.suggested_exercise_id is not None
    stuck = suggest(rx(15, 20), PUSH_UP, [session(1, (None, 20, 2))], [PUSH_UP])
    assert stuck.kind is SuggestionKind.HOLD


def test_timed_progression() -> None:
    timed = rx(None, None, 30)

    def hold(seconds: int) -> ExerciseHistoryEntry:
        return ExerciseHistoryEntry(
            session_date=date(2026, 9, 3), sets=(PerformedSet(duration_s=seconds),)
        )

    assert suggest(timed, TIMED, [hold(20)], catalog()).kind is SuggestionKind.HOLD
    assert suggest(timed, TIMED, [hold(30)], catalog()).kind is SuggestionKind.HARDER_VARIANT
    alone = suggest(timed, TIMED, [hold(35)], [TIMED])
    assert alone.kind is SuggestionKind.HOLD
    assert "5 s" in alone.reason_es


def test_harder_variant_ignores_same_group_and_deprecated() -> None:
    hardest = max(catalog(), key=lambda c: c.difficulty)
    assert harder_variant(hardest, catalog()) is None
    variant = harder_variant(PUSH_UP, catalog())
    assert variant is not None
    retired = variant.model_copy(update={"deprecated": True})
    others = [retired if c.id == variant.id else c for c in catalog()]
    assert harder_variant(PUSH_UP, others) != retired

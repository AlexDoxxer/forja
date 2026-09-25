"""Propiedades de §7.8 con hypothesis sobre entradas arbitrarias válidas."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from forja_engine import generate
from forja_engine.models import (
    Emphasis,
    EquipmentCode,
    EquipmentPreset,
    EquipmentSelection,
    Experience,
    GeneratorInput,
    Goal,
    MovementPattern,
    MuscleCode,
    Sex,
    Weekday,
)
from tests.helpers import assert_plan_invariants, catalog

IDS = sorted(card.id for card in catalog())
AVOIDABLE_PATTERNS = [
    p for p in MovementPattern if p not in {MovementPattern.CARDIO, MovementPattern.MOBILITY}
]


@st.composite
def generator_inputs(draw: st.DrawFn) -> GeneratorInput:
    days = draw(st.integers(1, 7))
    preset = draw(st.sampled_from(list(EquipmentPreset)))
    items: tuple[EquipmentCode, ...] = ()
    if preset is EquipmentPreset.CUSTOM:
        items = tuple(
            draw(
                st.lists(st.sampled_from(list(EquipmentCode)), min_size=1, max_size=6, unique=True)
            )
        )
    preferred = draw(
        st.one_of(
            st.just(()),
            st.lists(st.sampled_from(list(Weekday)), min_size=days, max_size=days, unique=True).map(
                tuple
            ),
        )
    )
    return GeneratorInput(
        goal=draw(st.sampled_from(list(Goal))),
        days_per_week=days,
        sex=draw(st.sampled_from(list(Sex))),
        experience=draw(st.sampled_from(list(Experience))),
        session_minutes=draw(st.integers(4, 24)) * 5,
        equipment=EquipmentSelection(preset=preset, items=items),
        emphasis=draw(st.sampled_from(list(Emphasis))),
        avoid_muscles=tuple(
            draw(st.lists(st.sampled_from(list(MuscleCode)), max_size=3, unique=True))
        ),
        avoid_patterns=tuple(
            draw(st.lists(st.sampled_from(AVOIDABLE_PATTERNS), max_size=3, unique=True))
        ),
        preferred_days=preferred,
        weeks=draw(st.integers(4, 8)),
        include_warmup=draw(st.one_of(st.none(), st.booleans())),
        include_cooldown=draw(st.one_of(st.none(), st.booleans())),
        include_cardio_finisher=draw(st.one_of(st.none(), st.booleans())),
        favorite_exercise_ids=tuple(draw(st.lists(st.sampled_from(IDS), max_size=10, unique=True))),
        excluded_exercise_ids=tuple(draw(st.lists(st.sampled_from(IDS), max_size=40, unique=True))),
        seed=draw(st.one_of(st.none(), st.integers(0, 2**53 - 1))),
    )


PROPERTY_SETTINGS = settings(
    max_examples=150,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


@PROPERTY_SETTINGS
@given(generator_inputs())
def test_generated_plans_satisfy_all_invariants(inp: GeneratorInput) -> None:
    """validate_plan, tiempo, exclusiones, evitados, equipamiento y volumen ±15 % o aviso."""
    assert_plan_invariants(generate(inp, catalog()))


@settings(max_examples=40, deadline=None, derandomize=True)
@given(generator_inputs())
def test_generation_is_deterministic_byte_for_byte(inp: GeneratorInput) -> None:
    first = generate(inp, catalog()).model_dump_json()
    second = generate(inp, catalog()).model_dump_json()
    assert first == second


@settings(max_examples=40, deadline=None, derandomize=True)
@given(generator_inputs())
def test_normalized_input_regenerates_the_same_plan(inp: GeneratorInput) -> None:
    plan = generate(inp, catalog())
    assert generate(plan.input, catalog()) == plan

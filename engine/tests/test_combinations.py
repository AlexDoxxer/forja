"""§7.8: las 1.890 combinaciones objetivo x días x nivel x sexo x preset generan planes válidos."""

import itertools

import pytest

from forja_engine import generate
from forja_engine.models import EquipmentPreset, Experience, GeneratorInput, Goal, Sex
from tests.helpers import assert_plan_invariants, catalog, equipment_for

SESSION_MINUTES = (30, 45, 60, 75, 90)
COMBINATIONS = list(itertools.product(Goal, range(1, 8), Experience, Sex, EquipmentPreset))


def test_matrix_has_1890_cases() -> None:
    assert len(COMBINATIONS) == 6 * 7 * 3 * 3 * 5 == 1890


@pytest.mark.parametrize(
    ("goal", "days", "level", "sex", "preset"),
    COMBINATIONS,
    ids=[f"{g.value}-{d}d-{lv.value}-{s.value}-{p.value}" for g, d, lv, s, p in COMBINATIONS],
)
def test_every_combination_generates_a_valid_plan(
    goal: Goal, days: int, level: Experience, sex: Sex, preset: EquipmentPreset
) -> None:
    index = COMBINATIONS.index((goal, days, level, sex, preset))
    inp = GeneratorInput(
        goal=goal,
        days_per_week=days,
        sex=sex,
        experience=level,
        session_minutes=SESSION_MINUTES[index % len(SESSION_MINUTES)],
        equipment=equipment_for(preset),
    )
    plan = generate(inp, catalog())
    assert_plan_invariants(plan)

"""F1-ENG-18: ``generate`` por debajo de 150 ms en el p95 con el catálogo completo (1.324)."""

import itertools
import time

from forja_engine import generate
from forja_engine.models import EquipmentPreset, Experience, Goal
from tests.helpers import catalog, equipment_for, make_input

P95_BUDGET_S = 0.150


def test_generate_p95_under_150_ms() -> None:
    cards = catalog()
    assert len(cards) == 1324
    durations: list[float] = []
    cases = itertools.product(
        [Goal.HYPERTROPHY, Goal.STRENGTH, Goal.FAT_LOSS, Goal.ENDURANCE],
        [3, 5, 7],
        [Experience.BEGINNER, Experience.ADVANCED],
        [EquipmentPreset.FULL_GYM, EquipmentPreset.HOME_DUMBBELLS],
    )
    for goal, days, level, preset in cases:
        inp = make_input(
            goal=goal, days_per_week=days, experience=level, equipment=equipment_for(preset)
        )
        start = time.perf_counter()
        generate(inp, cards)
        durations.append(time.perf_counter() - start)
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 < P95_BUDGET_S, f"p95 = {p95 * 1000:.1f} ms"

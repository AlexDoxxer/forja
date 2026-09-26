"""Barrido de 288 perfiles del informe F1b (`docs/reviews/f1b-experto-entrenamiento.md`, §7).

4 cuerpos x 4 dietas x 3 combinaciones de alérgenos x 3 objetivos x 2 números de comidas
(3 y 4) = 288 planes semanales (2.016 días). Devuelve métricas agregadas; los criterios de
re-verificación son:

- 0 días con grasa > 35 % de las kcal del día;
- `tolerance_not_met` en <= 25 % de los planes;
- 0 desayunos con legumbre, pescado o carne guisada;
- 0 ítems por encima de `max_portion_g` y 0 ítems < 30 % de la porción típica.

Uso: ``cd nutrition && uv run python -m scripts.sweep`` (imprime las métricas en JSON).
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

from forja_nutrition.foods import foods_by_id
from forja_nutrition.models import (
    ActivityLevel,
    Allergen,
    DietType,
    FoodCategory,
    MealPlan,
    MealSlot,
    NutritionGoal,
    NutritionInput,
    NutritionNoticeCode,
    NutritionPace,
    Sex,
)
from forja_nutrition.planner import plan_week
from forja_nutrition.tables import load_nutrition_tables

MONDAY = date(2026, 9, 28)
FAT_CEILING_FRACTION = 0.35
MIN_PORTION_FRACTION = 0.30
_FAT_KCAL_PER_GRAM = 9.0
_BREAKFAST_FORBIDDEN = frozenset(
    {FoodCategory.legumes, FoodCategory.fish_seafood, FoodCategory.meat}
)
# jamón y embutidos de desayuno tradicional no cuentan como «carne guisada»
_BREAKFAST_CURED_MEATS = frozenset({"jamon_cocido", "jamon_curado", "bacon", "salchicha_cerdo"})

_BODIES: tuple[tuple[Sex, int, float, float, ActivityLevel, int], ...] = (
    (Sex.male, 34, 178.0, 80.0, ActivityLevel.moderate, 4),
    (Sex.female, 45, 155.0, 52.0, ActivityLevel.sedentary, 0),
    (Sex.male, 24, 185.0, 95.0, ActivityLevel.high, 5),
    (Sex.female, 29, 166.0, 60.0, ActivityLevel.light, 3),
)
_ALLERGEN_SETS: tuple[tuple[Allergen, ...], ...] = (
    (),
    (Allergen.tree_nuts,),
    (Allergen.gluten, Allergen.soy),
)
_GOALS = (NutritionGoal.lose, NutritionGoal.maintain, NutritionGoal.gain)


@dataclass(frozen=True)
class SweepResult:
    plans: int
    days: int
    days_fat_above_ceiling: int
    plans_tolerance_not_met: int
    breakfasts_with_forbidden_food: int
    items_above_max_portion: int
    items_below_min_portion: int
    allergen_violations: int
    vegan_days_fat_over_allowed: int
    vegan_days: int
    max_fat_fraction: float

    @property
    def tolerance_not_met_rate(self) -> float:
        return self.plans_tolerance_not_met / self.plans

    def to_json(self) -> str:
        data = asdict(self)
        data["tolerance_not_met_rate"] = round(self.tolerance_not_met_rate, 4)
        return json.dumps(data, indent=2, sort_keys=True)


def sweep_inputs() -> list[NutritionInput]:
    """Los 288 perfiles válidos, con semilla derivada de su posición (reproducible)."""
    inputs: list[NutritionInput] = []
    combos = itertools.product(_BODIES, DietType, _ALLERGEN_SETS, _GOALS, (3, 4))
    for index, (body, diet, allergens, goal, meals) in enumerate(combos):
        sex, age, height, weight, activity, training = body
        inputs.append(
            NutritionInput(
                sex=sex,
                age_years=age,
                height_cm=height,
                weight_kg=weight,
                activity_level=activity,
                training_days_per_week=training,
                goal=goal,
                pace=NutritionPace.standard,
                diet_type=diet,
                meals_per_day=meals,
                allergens=allergens,
                seed=1000 + index,
            )
        )
    return inputs


def _count_plan(
    nutrition_input: NutritionInput, plan: MealPlan, counters: Counter[str], fat_over_allowed: float
) -> float:
    """Acumula las métricas de un plan; devuelve su mayor fracción de grasa diaria."""
    foods = foods_by_id()
    forbidden = set(nutrition_input.allergens)
    counters["plans"] += 1
    if any(n.code is NutritionNoticeCode.tolerance_not_met for n in plan.notices):
        counters["tnm"] += 1
    max_fraction = 0.0
    for day in plan.days:
        counters["days"] += 1
        fraction = day.totals.fat_g * _FAT_KCAL_PER_GRAM / day.totals.kcal
        max_fraction = max(max_fraction, fraction)
        counters["fat"] += fraction > FAT_CEILING_FRACTION + 1e-9
        if nutrition_input.diet_type is DietType.vegan:
            counters["vegan_days"] += 1
            counters["vegan_fat"] += day.deviation.fat > fat_over_allowed
        for meal in day.meals:
            for item in meal.items:
                food = foods[item.food_id]
                counters["above"] += item.grams > food.max_portion_g + 1e-9
                counters["below"] += (
                    item.grams < MIN_PORTION_FRACTION * food.typical_portion_g - 1e-9
                )
                counters["allergen"] += bool(forbidden & set(food.allergens))
                counters["breakfast"] += (
                    meal.slot is MealSlot.breakfast
                    and food.category in _BREAKFAST_FORBIDDEN
                    and food.id not in _BREAKFAST_CURED_MEATS
                )
    return max_fraction


def run_sweep(inputs: list[NutritionInput] | None = None) -> SweepResult:
    fat_over_allowed = load_nutrition_tables().tolerances.fat_over_allowed
    counters: Counter[str] = Counter()
    max_fraction = 0.0
    for nutrition_input in inputs if inputs is not None else sweep_inputs():
        plan = plan_week(nutrition_input, MONDAY).plan
        if plan is None:  # pragma: no cover (los perfiles del barrido son válidos)
            raise ValueError("perfil bloqueado en el barrido")
        max_fraction = max(
            max_fraction, _count_plan(nutrition_input, plan, counters, fat_over_allowed)
        )
    return SweepResult(
        plans=counters["plans"],
        days=counters["days"],
        days_fat_above_ceiling=counters["fat"],
        plans_tolerance_not_met=counters["tnm"],
        breakfasts_with_forbidden_food=counters["breakfast"],
        items_above_max_portion=counters["above"],
        items_below_min_portion=counters["below"],
        allergen_violations=counters["allergen"],
        vegan_days_fat_over_allowed=counters["vegan_fat"],
        vegan_days=counters["vegan_days"],
        max_fat_fraction=round(max_fraction, 4),
    )


if __name__ == "__main__":  # pragma: no cover
    sys.stdout.write(run_sweep().to_json() + "\n")

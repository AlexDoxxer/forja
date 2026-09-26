"""Carga y validación de las tablas de `specs/nutrition.yaml` (ADR 0005).

El motor no lee `specs/` del repositorio en tiempo de ejecución: empaqueta una copia en
`forja_nutrition/data/nutrition.yaml` (misma versión, mismo contenido) para no depender de
rutas externas al paquete. Cualquier YAML inválido o con referencias rotas falla al cargar
(``pydantic.ValidationError``), tal como exige ADR 0005.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from forja_nutrition.models import ActivityLevel, MealSlot, NutritionGoal, Sex

_REQUIRED_TRAINING_DAYS_BUCKETS = {"0", "1-2", "3-4", "5-7", "cap_factor"}
_REQUIRED_MEAL_SIZES = {3, 4, 5}
_KCAL_SPLIT_SUM_TOLERANCE = 1e-6


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GoalAdjustmentEntry(_Frozen):
    standard: float
    gentle: float
    max_deficit_kcal: float | None = None


class ProteinTable(_Frozen):
    default: float
    lose: float
    recomp: float
    gain: float
    min: float
    max: float


class FatTable(_Frozen):
    min_g_per_kg: float
    min_pct_kcal: float
    max_pct_kcal: float


class ProteinBasisTable(_Frozen):
    adjusted_if_bmi_ge: float
    reference_bmi: float


class SafetyTable(_Frozen):
    min_age: int
    kcal_floor: dict[Sex, float]
    kcal_floor_not_below_bmr: bool
    block_lose_if_bmi_below: float
    block_if: tuple[str, ...]
    min_meals_per_day: int


class TolerancesTable(_Frozen):
    kcal: float
    macros: float
    macro_sum_vs_kcal: float
    fat_over_allowed: float


class RoundingTable(_Frozen):
    grams_step: float
    unit_foods: tuple[str, ...]


class NutritionTables(_Frozen):
    version: int
    activity_factors: dict[ActivityLevel, float]
    training_days_adjustment: dict[str, float]
    goal_adjustment: dict[NutritionGoal, GoalAdjustmentEntry]
    protein_g_per_kg: ProteinTable
    protein_bodyweight_basis: ProteinBasisTable
    protein_max_g_per_day: float
    fat: FatTable
    fiber_g_per_1000_kcal: float
    safety: SafetyTable
    tolerances: TolerancesTable
    rounding: RoundingTable
    meal_templates: dict[int, tuple[MealSlot, ...]]
    meal_kcal_split: dict[int, dict[MealSlot, float]]

    @field_validator("training_days_adjustment")
    @classmethod
    def _check_training_days_buckets(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != _REQUIRED_TRAINING_DAYS_BUCKETS:
            raise ValueError(
                f"training_days_adjustment debe tener exactamente las claves "
                f"{sorted(_REQUIRED_TRAINING_DAYS_BUCKETS)}"
            )
        return value

    @field_validator("meal_templates")
    @classmethod
    def _check_meal_templates(
        cls, value: dict[int, tuple[MealSlot, ...]]
    ) -> dict[int, tuple[MealSlot, ...]]:
        if set(value) != _REQUIRED_MEAL_SIZES:
            raise ValueError("meal_templates debe definir exactamente 3, 4 y 5 comidas")
        for key, slots in value.items():
            if len(slots) != key:
                raise ValueError(f"meal_templates[{key}] debe tener {key} comidas")
            if len(set(slots)) != len(slots):
                raise ValueError(f"meal_templates[{key}] no debe repetir comidas")
        return value

    @field_validator("meal_kcal_split")
    @classmethod
    def _check_meal_kcal_split_sums_to_one(
        cls, value: dict[int, dict[MealSlot, float]]
    ) -> dict[int, dict[MealSlot, float]]:
        for key, fractions in value.items():
            total = sum(fractions.values())
            if abs(total - 1.0) > _KCAL_SPLIT_SUM_TOLERANCE:
                raise ValueError(f"meal_kcal_split[{key}] debe sumar 1.0 (suma={total})")
        return value

    @model_validator(mode="after")
    def _check_templates_match_split(self) -> NutritionTables:
        # Ambos campos ya están forzados a cubrir exactamente {3, 4, 5} por sus propios
        # field_validator; aquí solo queda comprobar que coinciden las comidas de cada tamaño.
        for key, slots in self.meal_templates.items():
            if set(slots) != set(self.meal_kcal_split[key]):
                raise ValueError(
                    f"meal_kcal_split[{key}] no coincide con las comidas de meal_templates[{key}]"
                )
        return self

    @model_validator(mode="after")
    def _check_goal_adjustment_covers_all_goals(self) -> NutritionTables:
        if set(self.goal_adjustment) != set(NutritionGoal):
            raise ValueError("goal_adjustment debe cubrir todos los NutritionGoal")
        return self

    @model_validator(mode="after")
    def _check_kcal_floor_covers_all_sexes(self) -> NutritionTables:
        if set(self.safety.kcal_floor) != set(Sex):
            raise ValueError("safety.kcal_floor debe cubrir los tres valores de Sex")
        return self

    @model_validator(mode="after")
    def _check_activity_factors_cover_all_levels(self) -> NutritionTables:
        if set(self.activity_factors) != set(ActivityLevel):
            raise ValueError("activity_factors debe cubrir todos los ActivityLevel")
        return self


@lru_cache(maxsize=1)
def load_nutrition_tables() -> NutritionTables:
    """Carga `forja_nutrition/data/nutrition.yaml` empaquetado (memoizado)."""
    raw = (
        resources.files("forja_nutrition.data")
        .joinpath("nutrition.yaml")
        .read_text(encoding="utf-8")
    )
    data = yaml.safe_load(raw)
    return NutritionTables.model_validate(data)

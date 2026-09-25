"""DTOs del motor de nutrición (`contracts/domain.md` §6).

Todos los modelos son Pydantic v2 ``frozen=True, extra="forbid"``; las secuencias son
``tuple[...]`` para que las salidas del motor sean inmutables y hashables. La forma JSON de
cada modelo coincide con ``contracts/openapi.yaml``.
"""

from __future__ import annotations

from datetime import date  # noqa: TC003 (pydantic necesita el tipo en tiempo de ejecución)
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

FoodId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=64)]
Seed = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Sex(StrEnum):
    male = "male"
    female = "female"
    unspecified = "unspecified"


class ActivityLevel(StrEnum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    high = "high"


class NutritionGoal(StrEnum):
    lose = "lose"
    maintain = "maintain"
    gain = "gain"
    recomp = "recomp"


class NutritionPace(StrEnum):
    gentle = "gentle"
    standard = "standard"


class DietType(StrEnum):
    omnivore = "omnivore"
    pescatarian = "pescatarian"
    vegetarian = "vegetarian"
    vegan = "vegan"


class Allergen(StrEnum):
    gluten = "gluten"
    lactose = "lactose"
    tree_nuts = "tree_nuts"
    egg = "egg"
    fish = "fish"
    shellfish = "shellfish"
    soy = "soy"


class MealSlot(StrEnum):
    breakfast = "breakfast"
    mid_morning = "mid_morning"
    lunch = "lunch"
    snack = "snack"
    dinner = "dinner"


class FoodCategory(StrEnum):
    fruits = "fruits"
    vegetables = "vegetables"
    legumes = "legumes"
    grains = "grains"
    bakery = "bakery"
    dairy = "dairy"
    eggs = "eggs"
    meat = "meat"
    fish_seafood = "fish_seafood"
    plant_protein = "plant_protein"
    nuts_seeds = "nuts_seeds"
    fats_oils = "fats_oils"
    condiments = "condiments"
    beverages = "beverages"


class FoodMacroRole(StrEnum):
    protein = "protein"
    carb = "carb"
    produce = "produce"
    fat = "fat"


class BmrMethod(StrEnum):
    mifflin_male = "mifflin_male"
    mifflin_female = "mifflin_female"
    mifflin_average = "mifflin_average"


class NutritionBlockReason(StrEnum):
    under_18 = "under_18"
    pregnant = "pregnant"
    breastfeeding = "breastfeeding"
    missing_profile_data = "missing_profile_data"


class NutritionNoticeCode(StrEnum):
    health_disclaimer = "health_disclaimer"
    kcal_floor_applied = "kcal_floor_applied"
    deficit_capped = "deficit_capped"
    lose_blocked_low_bmi = "lose_blocked_low_bmi"
    protein_clamped = "protein_clamped"
    fat_floor_applied = "fat_floor_applied"
    tolerance_not_met = "tolerance_not_met"
    swap_macros_adjusted = "swap_macros_adjusted"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NutritionInput(_Frozen):
    sex: Sex
    age_years: int = Field(ge=0, le=120)
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=20, le=400)
    activity_level: ActivityLevel
    training_days_per_week: int = Field(ge=0, le=7)
    goal: NutritionGoal
    pace: NutritionPace
    diet_type: DietType
    meals_per_day: int = Field(ge=3, le=5)
    allergens: tuple[Allergen, ...] = ()
    excluded_food_ids: tuple[FoodId, ...] = ()
    disliked_food_ids: tuple[FoodId, ...] = ()
    pregnant: bool = False
    breastfeeding: bool = False
    seed: Seed | None = None

    @model_validator(mode="after")
    def _check_no_duplicate_ids(self) -> NutritionInput:
        for name in ("allergens", "excluded_food_ids", "disliked_food_ids"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} no debe contener duplicados")
        return self


class MacroTotals(_Frozen):
    kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fiber_g: float = Field(ge=0)


class NutritionBlock(_Frozen):
    reason_code: NutritionBlockReason
    message_es: str


class NutritionNotice(_Frozen):
    code: NutritionNoticeCode
    message_es: str


class NutritionTarget(_Frozen):
    method: BmrMethod
    age_years: int
    bmr_kcal: float
    activity_factor: float
    tdee_kcal: float
    requested_goal: NutritionGoal
    effective_goal: NutritionGoal
    pace: NutritionPace
    target_kcal: float | None
    protein_g: float | None
    fat_g: float | None
    carbs_g: float | None
    fiber_g: float | None
    blocked: bool
    block: NutritionBlock | None
    notices: tuple[NutritionNotice, ...]

    @model_validator(mode="after")
    def _check_blocked_consistency(self) -> NutritionTarget:
        optional_fields = (
            self.target_kcal,
            self.protein_g,
            self.fat_g,
            self.carbs_g,
            self.fiber_g,
        )
        if self.blocked:
            if self.block is None:
                raise ValueError("un NutritionTarget bloqueado debe incluir block")
            if any(value is not None for value in optional_fields):
                raise ValueError("un NutritionTarget bloqueado no debe informar cifras objetivo")
        else:
            if self.block is not None:
                raise ValueError("un NutritionTarget no bloqueado no debe incluir block")
            if any(value is None for value in optional_fields):
                raise ValueError("un NutritionTarget no bloqueado debe informar todas las cifras")
        return self


class MealItem(_Frozen):
    food_id: FoodId
    name_es: str
    grams: float = Field(gt=0)
    units: int | None = Field(default=None, ge=1)
    nutrients: MacroTotals


class Meal(_Frozen):
    slot: MealSlot
    items: tuple[MealItem, ...] = Field(min_length=1)
    totals: MacroTotals


class MacroDeviation(_Frozen):
    kcal: float
    protein: float
    fat: float
    carbs: float


class MealPlanDay(_Frozen):
    day_index: int = Field(ge=0, le=6)
    date: date
    meals: tuple[Meal, ...] = Field(min_length=1)
    totals: MacroTotals
    deviation: MacroDeviation


class MealPlan(_Frozen):
    nutrition_version: str
    foods_hash: Sha256
    seed: Seed
    week_start: date
    diet_type: DietType
    meals_per_day: int = Field(ge=3, le=5)
    target: NutritionTarget
    days: tuple[MealPlanDay, ...] = Field(min_length=7, max_length=7)
    notices: tuple[NutritionNotice, ...]

    @model_validator(mode="after")
    def _check_week_start_is_monday(self) -> MealPlan:
        if self.week_start.weekday() != 0:
            raise ValueError("week_start debe ser lunes")
        return self

    @model_validator(mode="after")
    def _check_day_indexes(self) -> MealPlan:
        expected = tuple(range(7))
        actual = tuple(day.day_index for day in self.days)
        if actual != expected:
            raise ValueError("days debe tener day_index de 0 a 6 en orden")
        return self


class MealPlanOutcome(_Frozen):
    plan: MealPlan | None
    block: NutritionBlock | None

    @model_validator(mode="after")
    def _check_exactly_one(self) -> MealPlanOutcome:
        if (self.plan is None) == (self.block is None):
            raise ValueError("MealPlanOutcome debe informar exactamente uno de plan o block")
        return self


class ShoppingItem(_Frozen):
    food_id: FoodId
    name_es: str
    total_grams: float = Field(ge=0)
    units: int | None = Field(default=None, ge=1)


class ShoppingCategory(_Frozen):
    category: FoodCategory
    label_es: str
    items: tuple[ShoppingItem, ...] = Field(min_length=1)


class ShoppingList(_Frozen):
    week_start: date
    categories: tuple[ShoppingCategory, ...]


class Food(_Frozen):
    id: FoodId
    name_es: str
    category: FoodCategory
    fdc_id: int = Field(gt=0)
    per_100g: MacroTotals
    diet_types: tuple[DietType, ...] = Field(min_length=1)
    allergens: tuple[Allergen, ...] = ()
    macro_role: FoodMacroRole
    typical_portion_g: float = Field(gt=0)
    unit_grams: float | None = Field(default=None, gt=0)
    unit_name_es: str | None = None

    energy_note: str | None = None

    @model_validator(mode="after")
    def _check_unit_name_matches_grams(self) -> Food:
        if (self.unit_grams is None) != (self.unit_name_es is None):
            raise ValueError("unit_grams y unit_name_es deben informarse juntos")
        return self

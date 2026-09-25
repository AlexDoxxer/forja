"""`data/foods.json`: integridad y coherencia kcal↔macros de cada alimento (§8.4)."""

from __future__ import annotations

import pytest

from forja_nutrition.foods import _ensure_unique_ids, foods_by_id, foods_hash, load_foods
from forja_nutrition.models import DietType, Food, FoodCategory, FoodMacroRole, MacroTotals

_ENERGY_TOLERANCE = 0.12


def test_load_foods_returns_around_200_unique_foods() -> None:
    foods = load_foods()
    assert 150 <= len(foods) <= 250
    ids = [food.id for food in foods]
    assert len(ids) == len(set(ids))


def test_load_foods_is_memoized() -> None:
    assert load_foods() is load_foods()


def test_foods_hash_is_stable_sha256() -> None:
    digest = foods_hash()
    assert len(digest) == 64
    int(digest, 16)  # no lanza si es hexadecimal válido
    assert foods_hash() == digest


def test_foods_by_id_matches_load_foods() -> None:
    catalog = foods_by_id()
    foods = load_foods()
    assert len(catalog) == len(foods)
    for food in foods:
        assert catalog[food.id] is food


def test_every_food_has_at_least_one_diet_type_and_valid_portion() -> None:
    for food in load_foods():
        assert len(food.diet_types) >= 1
        assert food.typical_portion_g > 0
        assert food.fdc_id > 0


def test_every_food_passes_energy_consistency_or_has_a_note() -> None:
    """`|kcal - (4P + 4C + 9G)| <= 12%` o `energy_note` documentado (§8.4)."""
    unjustified: list[str] = []
    for food in load_foods():
        p = food.per_100g
        computed = 4 * p.protein_g + 4 * p.carbs_g + 9 * p.fat_g
        denominator = p.kcal if p.kcal > 0 else 1.0
        relative_diff = abs(p.kcal - computed) / denominator
        if relative_diff > _ENERGY_TOLERANCE and food.energy_note is None:
            unjustified.append(f"{food.id}: kcal={p.kcal} computed={computed:.1f}")
    assert not unjustified, unjustified


def test_energy_notes_are_non_empty_when_present() -> None:
    for food in load_foods():
        if food.energy_note is not None:
            assert len(food.energy_note) > 10


def test_all_diet_types_are_represented() -> None:
    seen = {diet for food in load_foods() for diet in food.diet_types}
    assert seen == set(DietType)


def test_all_food_categories_are_represented() -> None:
    seen = {food.category for food in load_foods()}
    assert seen == set(FoodCategory)


def _make_food(food_id: str) -> Food:
    return Food(
        id=food_id,
        name_es="Duplicado de prueba",
        category=FoodCategory.fruits,
        fdc_id=1,
        per_100g=MacroTotals(kcal=50, protein_g=1, fat_g=1, carbs_g=10, fiber_g=1),
        diet_types=(DietType.omnivore,),
        macro_role=FoodMacroRole.produce,
        typical_portion_g=100,
    )


def test_ensure_unique_ids_raises_on_duplicates() -> None:
    foods = (_make_food("dup"), _make_food("dup"))
    with pytest.raises(ValueError, match="duplicados"):
        _ensure_unique_ids(foods)


def test_ensure_unique_ids_accepts_unique() -> None:
    foods = (_make_food("a"), _make_food("b"))
    _ensure_unique_ids(foods)  # no debe lanzar

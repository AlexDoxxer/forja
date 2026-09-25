"""Lista de la compra semanal agregada por categoría (MASTER_PROMPT §8.3)."""

from __future__ import annotations

from forja_nutrition.foods import foods_by_id
from forja_nutrition.models import (
    FoodCategory,
    MealPlan,
    ShoppingCategory,
    ShoppingItem,
    ShoppingList,
)

CATEGORY_LABELS_ES: dict[FoodCategory, str] = {
    FoodCategory.fruits: "Frutas",
    FoodCategory.vegetables: "Verduras y hortalizas",
    FoodCategory.legumes: "Legumbres",
    FoodCategory.grains: "Cereales y granos",
    FoodCategory.bakery: "Panadería",
    FoodCategory.dairy: "Lácteos",
    FoodCategory.eggs: "Huevos",
    FoodCategory.meat: "Carnes",
    FoodCategory.fish_seafood: "Pescados y mariscos",
    FoodCategory.plant_protein: "Proteína vegetal",
    FoodCategory.nuts_seeds: "Frutos secos y semillas",
    FoodCategory.fats_oils: "Aceites y grasas",
    FoodCategory.condiments: "Condimentos y salsas",
    FoodCategory.beverages: "Bebidas",
}


def shopping_list(plan: MealPlan) -> ShoppingList:
    """API pública del motor (`contracts/domain.md` §6.3)."""
    catalog = foods_by_id()
    grams_by_food: dict[str, float] = {}
    units_by_food: dict[str, int] = {}
    name_by_food: dict[str, str] = {}

    for day in plan.days:
        for meal in day.meals:
            for meal_item in meal.items:
                grams_by_food[meal_item.food_id] = (
                    grams_by_food.get(meal_item.food_id, 0.0) + meal_item.grams
                )
                if meal_item.units is not None:
                    units_by_food[meal_item.food_id] = (
                        units_by_food.get(meal_item.food_id, 0) + meal_item.units
                    )
                name_by_food[meal_item.food_id] = meal_item.name_es

    items_by_category: dict[FoodCategory, list[ShoppingItem]] = {}
    for food_id, total_grams in grams_by_food.items():
        food = catalog.get(food_id)
        if food is None:
            continue
        shopping_item = ShoppingItem(
            food_id=food_id,
            name_es=name_by_food[food_id],
            total_grams=round(total_grams, 1),
            units=units_by_food.get(food_id),
        )
        items_by_category.setdefault(food.category, []).append(shopping_item)

    categories = tuple(
        ShoppingCategory(
            category=category,
            label_es=CATEGORY_LABELS_ES[category],
            items=tuple(sorted(items_by_category[category], key=lambda i: i.name_es)),
        )
        for category in FoodCategory
        if category in items_by_category
    )
    return ShoppingList(week_start=plan.week_start, categories=categories)

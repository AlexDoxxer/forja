"""Reparto de macronutrientes (proteína, grasa, carbohidratos, fibra) de MASTER_PROMPT §8.2.

Las funciones son puras y reciben las sub-tablas ya cargadas (`tables.py`) para poder
probarlas de forma aislada, incluidos los suelos de seguridad en casos límite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forja_nutrition.models import NutritionGoal

if TYPE_CHECKING:
    from forja_nutrition.tables import FatTable, ProteinTable

_FAT_KCAL_PER_GRAM = 9.0
_PROTEIN_KCAL_PER_GRAM = 4.0
_CARBS_KCAL_PER_GRAM = 4.0
_ENERGY_FLOOR_ITERATIONS = 20


def protein_g_per_kg_for_goal(goal: NutritionGoal, table: ProteinTable) -> float:
    """`protein_g_per_kg` de la tabla según objetivo; `maintain` usa el valor `default`."""
    per_goal = {
        NutritionGoal.lose: table.lose,
        NutritionGoal.recomp: table.recomp,
        NutritionGoal.gain: table.gain,
    }
    return per_goal.get(goal, table.default)


def clamp_protein_g_per_kg(value: float, table: ProteinTable) -> tuple[float, bool]:
    """Recorta `value` a [min, max]. Devuelve (valor, si se ha recortado)."""
    if value < table.min:
        return table.min, True
    if value > table.max:
        return table.max, True
    return value, False


def resolve_energy_and_fat(
    *,
    weight_kg: float,
    protein_g: float,
    preliminary_kcal: float,
    fat_table: FatTable,
) -> tuple[float, float]:
    """Calorías objetivo finales y gramos de grasa, asegurando que las kcal cubren siempre
    los suelos de proteína y grasa (nunca deja carbohidratos negativos).

    ``fat_g`` es el máximo entre el suelo por kg de peso y el suelo por porcentaje de kcal;
    como ese segundo suelo depende de las propias kcal objetivo, se resuelve por iteración de
    punto fijo (contrae porque el coeficiente de kcal en el suelo porcentual es < 1).
    """
    kcal = preliminary_kcal
    fat_g = fat_table.min_g_per_kg * weight_kg
    for _ in range(_ENERGY_FLOOR_ITERATIONS):
        fat_g = max(fat_table.min_g_per_kg * weight_kg, fat_table.min_pct_kcal * kcal / 9)
        needed_kcal = protein_g * _PROTEIN_KCAL_PER_GRAM + fat_g * _FAT_KCAL_PER_GRAM
        kcal = max(preliminary_kcal, needed_kcal)
    return kcal, fat_g


def fat_floor_governed_by_percentage(
    *, weight_kg: float, target_kcal: float, fat_table: FatTable
) -> bool:
    """True si el suelo de grasa activo es el de % de kcal, no el de g/kg."""
    return (fat_table.min_pct_kcal * target_kcal / 9) > (fat_table.min_g_per_kg * weight_kg)


def carbs_g_from_remainder(*, target_kcal: float, protein_g: float, fat_g: float) -> float:
    """Carbohidratos = resto de las kcal tras proteína y grasa (§8.2)."""
    carbs_kcal = target_kcal - protein_g * _PROTEIN_KCAL_PER_GRAM - fat_g * _FAT_KCAL_PER_GRAM
    return max(carbs_kcal, 0.0) / _CARBS_KCAL_PER_GRAM


def fiber_g_for(*, target_kcal: float, fiber_g_per_1000_kcal: float) -> float:
    return target_kcal / 1000 * fiber_g_per_1000_kcal

"""Bloqueos y suelos de seguridad de MASTER_PROMPT.md §8.5.

Los bloqueos se devuelven como resultado tipado (`NutritionBlock`), nunca como excepción: el
tono de los mensajes es neutro y deriva a un profesional sin alarmismo ni juicios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forja_nutrition.models import NutritionBlock, NutritionBlockReason, NutritionGoal, Sex

if TYPE_CHECKING:
    from forja_nutrition.tables import NutritionTables

BLOCK_MESSAGES_ES: dict[NutritionBlockReason, str] = {
    NutritionBlockReason.under_18: (
        "Los planes de nutrición de Forja no están disponibles para menores de 18 años. "
        "Te recomendamos consultar con un pediatra o un dietista-nutricionista."
    ),
    NutritionBlockReason.pregnant: (
        "Durante el embarazo las necesidades nutricionales cambian de forma individual. "
        "Te recomendamos consultar con un profesional de la salud para un plan adecuado."
    ),
    NutritionBlockReason.breastfeeding: (
        "Durante la lactancia las necesidades nutricionales cambian de forma individual. "
        "Te recomendamos consultar con un profesional de la salud para un plan adecuado."
    ),
    NutritionBlockReason.missing_profile_data: (
        "Nos faltan datos de tu perfil (fecha de nacimiento, altura o peso) para calcular "
        "un objetivo nutricional seguro. Complétalos en tu perfil para continuar."
    ),
}


def check_block(
    *,
    age_years: int,
    pregnant: bool,
    breastfeeding: bool,
    tables: NutritionTables,
) -> NutritionBlock | None:
    """Bloqueo total: menor de edad, embarazo o lactancia (§8.5). Orden de `block_if`."""
    for reason in tables.safety.block_if:
        if reason == NutritionBlockReason.under_18 and age_years < tables.safety.min_age:
            return NutritionBlock(
                reason_code=NutritionBlockReason.under_18,
                message_es=BLOCK_MESSAGES_ES[NutritionBlockReason.under_18],
            )
        if reason == NutritionBlockReason.pregnant and pregnant:
            return NutritionBlock(
                reason_code=NutritionBlockReason.pregnant,
                message_es=BLOCK_MESSAGES_ES[NutritionBlockReason.pregnant],
            )
        if reason == NutritionBlockReason.breastfeeding and breastfeeding:
            return NutritionBlock(
                reason_code=NutritionBlockReason.breastfeeding,
                message_es=BLOCK_MESSAGES_ES[NutritionBlockReason.breastfeeding],
            )
    return None


def bmi(*, weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return weight_kg / (height_m * height_m)


def effective_goal_for_bmi(
    *,
    goal: NutritionGoal,
    weight_kg: float,
    height_cm: float,
    tables: NutritionTables,
) -> tuple[NutritionGoal, bool]:
    """`lose` con IMC bajo suelo ⇒ se ofrece `maintain` (§8.5). Devuelve (objetivo, bloqueado)."""
    if (
        goal is NutritionGoal.lose
        and bmi(weight_kg=weight_kg, height_cm=height_cm) < tables.safety.block_lose_if_bmi_below
    ):
        return NutritionGoal.maintain, True
    return goal, False


def kcal_floor(*, sex: Sex, bmr_kcal: float, tables: NutritionTables) -> float:
    """Suelo de kcal por sexo, nunca por debajo de la TMB si la tabla lo exige (§8.5)."""
    floor = tables.safety.kcal_floor[sex]
    if tables.safety.kcal_floor_not_below_bmr:
        return max(floor, bmr_kcal)
    return floor

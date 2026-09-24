"""TMB Mifflin-St Jeor, GET y objetivo calórico/macros diario (MASTER_PROMPT §8.2).

`calculate_target` es la función pública del contrato (`contracts/domain.md` §6.3): compone
TMB + GET + ajuste por objetivo + suelos de seguridad + macros en un único `NutritionTarget`.
"""

from __future__ import annotations

from forja_nutrition import macros, safety
from forja_nutrition.models import (
    ActivityLevel,
    BmrMethod,
    NutritionGoal,
    NutritionInput,
    NutritionNotice,
    NutritionNoticeCode,
    NutritionPace,
    NutritionTarget,
    Sex,
)
from forja_nutrition.tables import NutritionTables, load_nutrition_tables

_MALE_FEMALE_BMR_GAP = 166.0  # (10w+6.25h-5a+5) - (10w+6.25h-5a-161)
_TRAINING_DAYS_LOW_BUCKET_MAX = 2
_TRAINING_DAYS_MID_BUCKET_MAX = 4

NOTICE_MESSAGES_ES: dict[NutritionNoticeCode, str] = {
    NutritionNoticeCode.health_disclaimer: (
        "Esta herramienta no sustituye a un profesional sanitario. Consulta a un médico o "
        "dietista-nutricionista antes de hacer cambios importantes en tu alimentación."
    ),
    NutritionNoticeCode.kcal_floor_applied: (
        "Hemos ajustado tus calorías objetivo al mínimo seguro para tu perfil."
    ),
    NutritionNoticeCode.deficit_capped: (
        "El déficit calórico se ha limitado a un máximo saludable de 500 kcal/día."
    ),
    NutritionNoticeCode.lose_blocked_low_bmi: (
        "Con tu índice de masa corporal actual no recomendamos un objetivo de pérdida de "
        "peso; te proponemos mantener el peso. Consulta con un profesional si quieres "
        "perder peso de forma segura."
    ),
    NutritionNoticeCode.protein_clamped: (
        "Hemos ajustado la proteína objetivo dentro de un rango seguro para tu peso."
    ),
    NutritionNoticeCode.fat_floor_applied: (
        "Hemos asegurado un mínimo de grasa saludable en tu objetivo diario."
    ),
    NutritionNoticeCode.tolerance_not_met: (
        "Algún día del plan se aleja algo más de lo habitual del objetivo calórico o de "
        "macros; sigue siendo un plan equilibrado en conjunto."
    ),
    NutritionNoticeCode.swap_macros_adjusted: (
        "Al intercambiar el alimento hemos ajustado la cantidad para mantener los "
        "macronutrientes de la comida."
    ),
}


def notice(code: NutritionNoticeCode) -> NutritionNotice:
    return NutritionNotice(code=code, message_es=NOTICE_MESSAGES_ES[code])


def mifflin_bmr(
    *, sex: Sex, age_years: int, height_cm: float, weight_kg: float
) -> tuple[float, BmrMethod]:
    """TMB Mifflin-St Jeor; `unspecified` usa la media de ambas fórmulas (§8.2)."""
    male_bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age_years + 5
    female_bmr = male_bmr - _MALE_FEMALE_BMR_GAP
    if sex is Sex.male:
        return male_bmr, BmrMethod.mifflin_male
    if sex is Sex.female:
        return female_bmr, BmrMethod.mifflin_female
    return (male_bmr + female_bmr) / 2, BmrMethod.mifflin_average


def training_days_bucket(training_days_per_week: int) -> str:
    if training_days_per_week <= 0:
        return "0"
    if training_days_per_week <= _TRAINING_DAYS_LOW_BUCKET_MAX:
        return "1-2"
    if training_days_per_week <= _TRAINING_DAYS_MID_BUCKET_MAX:
        return "3-4"
    return "5-7"


def compute_activity_factor(
    *,
    activity_level: ActivityLevel,
    training_days_per_week: int,
    tables: NutritionTables,
) -> float:
    """GET = TMB por factor de actividad + ajuste por días de entreno, acotado (§8.2)."""
    base = tables.activity_factors[activity_level]
    bucket = training_days_bucket(training_days_per_week)
    adjustment = tables.training_days_adjustment[bucket]
    cap = tables.training_days_adjustment["cap_factor"]
    return min(base + adjustment, cap)


def apply_goal_adjustment(
    *,
    tdee_kcal: float,
    goal: NutritionGoal,
    pace: NutritionPace,
    tables: NutritionTables,
) -> tuple[float, bool]:
    """Ajusta el GET por objetivo/ritmo, capando el déficit de `lose` (§8.2). Devuelve
    (kcal ajustadas, si el déficit se ha capado)."""
    entry = tables.goal_adjustment[goal]
    fraction = entry.standard if pace is NutritionPace.standard else entry.gentle
    adjusted = tdee_kcal * (1 + fraction)
    if entry.max_deficit_kcal is not None:
        deficit = tdee_kcal - adjusted
        if deficit > entry.max_deficit_kcal:
            return tdee_kcal - entry.max_deficit_kcal, True
    return adjusted, False


def calculate_target(nutrition_input: NutritionInput) -> NutritionTarget:
    """API pública del motor (`contracts/domain.md` §6.3)."""
    tables = load_nutrition_tables()

    bmr_kcal, method = mifflin_bmr(
        sex=nutrition_input.sex,
        age_years=nutrition_input.age_years,
        height_cm=nutrition_input.height_cm,
        weight_kg=nutrition_input.weight_kg,
    )
    factor = compute_activity_factor(
        activity_level=nutrition_input.activity_level,
        training_days_per_week=nutrition_input.training_days_per_week,
        tables=tables,
    )
    tdee_kcal = bmr_kcal * factor

    block = safety.check_block(
        age_years=nutrition_input.age_years,
        pregnant=nutrition_input.pregnant,
        breastfeeding=nutrition_input.breastfeeding,
        tables=tables,
    )
    if block is not None:
        return NutritionTarget(
            method=method,
            age_years=nutrition_input.age_years,
            bmr_kcal=bmr_kcal,
            activity_factor=factor,
            tdee_kcal=tdee_kcal,
            requested_goal=nutrition_input.goal,
            effective_goal=nutrition_input.goal,
            pace=nutrition_input.pace,
            target_kcal=None,
            protein_g=None,
            fat_g=None,
            carbs_g=None,
            fiber_g=None,
            blocked=True,
            block=block,
            notices=(notice(NutritionNoticeCode.health_disclaimer),),
        )

    notices = [notice(NutritionNoticeCode.health_disclaimer)]

    effective_goal, bmi_blocked = safety.effective_goal_for_bmi(
        goal=nutrition_input.goal,
        weight_kg=nutrition_input.weight_kg,
        height_cm=nutrition_input.height_cm,
        tables=tables,
    )
    if bmi_blocked:
        notices.append(notice(NutritionNoticeCode.lose_blocked_low_bmi))

    adjusted_kcal, deficit_capped = apply_goal_adjustment(
        tdee_kcal=tdee_kcal, goal=effective_goal, pace=nutrition_input.pace, tables=tables
    )
    if deficit_capped:
        notices.append(notice(NutritionNoticeCode.deficit_capped))

    floor = safety.kcal_floor(sex=nutrition_input.sex, bmr_kcal=bmr_kcal, tables=tables)
    preliminary_kcal = max(adjusted_kcal, floor)

    protein_per_kg = macros.protein_g_per_kg_for_goal(effective_goal, tables.protein_g_per_kg)
    clamped_per_kg, protein_clamped = macros.clamp_protein_g_per_kg(
        protein_per_kg, tables.protein_g_per_kg
    )
    if protein_clamped:
        notices.append(notice(NutritionNoticeCode.protein_clamped))
    protein_g = clamped_per_kg * nutrition_input.weight_kg

    target_kcal, fat_g = macros.resolve_energy_and_fat(
        weight_kg=nutrition_input.weight_kg,
        protein_g=protein_g,
        preliminary_kcal=preliminary_kcal,
        fat_table=tables.fat,
    )
    if target_kcal > preliminary_kcal or preliminary_kcal > adjusted_kcal:
        notices.append(notice(NutritionNoticeCode.kcal_floor_applied))
    if macros.fat_floor_governed_by_percentage(
        weight_kg=nutrition_input.weight_kg, target_kcal=target_kcal, fat_table=tables.fat
    ):
        notices.append(notice(NutritionNoticeCode.fat_floor_applied))

    carbs_g = macros.carbs_g_from_remainder(
        target_kcal=target_kcal, protein_g=protein_g, fat_g=fat_g
    )
    fiber_g = macros.fiber_g_for(
        target_kcal=target_kcal, fiber_g_per_1000_kcal=tables.fiber_g_per_1000_kcal
    )

    return NutritionTarget(
        method=method,
        age_years=nutrition_input.age_years,
        bmr_kcal=bmr_kcal,
        activity_factor=factor,
        tdee_kcal=tdee_kcal,
        requested_goal=nutrition_input.goal,
        effective_goal=effective_goal,
        pace=nutrition_input.pace,
        target_kcal=target_kcal,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        fiber_g=fiber_g,
        blocked=False,
        block=None,
        notices=tuple(notices),
    )

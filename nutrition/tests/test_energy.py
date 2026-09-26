"""`forja_nutrition/energy.py`: TMB, GET, ajuste por objetivo y `calculate_target` (§8.2/§8.5).

Cubre explícitamente los bloqueos de seguridad exigidos como criterio de aceptación de la
fase: menor de edad, embarazo, lactancia, IMC < 18,5 con `lose`, y el suelo de kcal.
"""

from __future__ import annotations

import pytest

from forja_nutrition import energy
from forja_nutrition.energy import (
    apply_goal_adjustment,
    calculate_target,
    compute_activity_factor,
    mifflin_bmr,
    training_days_bucket,
)
from forja_nutrition.models import (
    ActivityLevel,
    BmrMethod,
    NutritionGoal,
    NutritionNoticeCode,
    NutritionPace,
    Sex,
)
from forja_nutrition.tables import load_nutrition_tables
from tests.conftest import make_input

TABLES = load_nutrition_tables()


def test_mifflin_bmr_male() -> None:
    bmr, method = mifflin_bmr(sex=Sex.male, age_years=30, height_cm=180.0, weight_kg=80.0)
    assert bmr == pytest.approx(10 * 80 + 6.25 * 180 - 5 * 30 + 5)
    assert method == BmrMethod.mifflin_male


def test_mifflin_bmr_female() -> None:
    bmr, method = mifflin_bmr(sex=Sex.female, age_years=30, height_cm=165.0, weight_kg=60.0)
    assert bmr == pytest.approx(10 * 60 + 6.25 * 165 - 5 * 30 - 161)
    assert method == BmrMethod.mifflin_female


def test_mifflin_bmr_unspecified_is_average_of_both_formulas() -> None:
    male_bmr, _ = mifflin_bmr(sex=Sex.male, age_years=40, height_cm=170.0, weight_kg=70.0)
    female_bmr, _ = mifflin_bmr(sex=Sex.female, age_years=40, height_cm=170.0, weight_kg=70.0)
    avg_bmr, method = mifflin_bmr(
        sex=Sex.unspecified, age_years=40, height_cm=170.0, weight_kg=70.0
    )
    assert avg_bmr == pytest.approx((male_bmr + female_bmr) / 2)
    assert method == BmrMethod.mifflin_average


@pytest.mark.parametrize(
    ("days", "bucket"),
    [(0, "0"), (1, "1-2"), (2, "1-2"), (3, "3-4"), (4, "3-4"), (5, "5-7"), (6, "5-7"), (7, "5-7")],
)
def test_training_days_bucket(days: int, bucket: str) -> None:
    assert training_days_bucket(days) == bucket


def test_compute_activity_factor_matches_table_sum() -> None:
    factor = compute_activity_factor(
        activity_level=ActivityLevel.moderate, training_days_per_week=3, tables=TABLES
    )
    expected = (
        TABLES.activity_factors[ActivityLevel.moderate] + TABLES.training_days_adjustment["3-4"]
    )
    assert factor == pytest.approx(expected)


def test_compute_activity_factor_is_capped() -> None:
    inflated = TABLES.model_copy(
        update={
            "training_days_adjustment": {**TABLES.training_days_adjustment, "5-7": 5.0},
        }
    )
    factor = compute_activity_factor(
        activity_level=ActivityLevel.high, training_days_per_week=6, tables=inflated
    )
    assert factor == TABLES.training_days_adjustment["cap_factor"]


def test_apply_goal_adjustment_lose_standard_not_capped() -> None:
    adjusted, capped = apply_goal_adjustment(
        tdee_kcal=2000.0, goal=NutritionGoal.lose, pace=NutritionPace.standard, tables=TABLES
    )
    assert adjusted == pytest.approx(2000.0 * 0.85)
    assert capped is False


def test_apply_goal_adjustment_lose_capped_for_high_tdee() -> None:
    adjusted, capped = apply_goal_adjustment(
        tdee_kcal=6000.0, goal=NutritionGoal.lose, pace=NutritionPace.standard, tables=TABLES
    )
    assert adjusted == pytest.approx(6000.0 - 500.0)
    assert capped is True


def test_apply_goal_adjustment_gain_gentle() -> None:
    adjusted, capped = apply_goal_adjustment(
        tdee_kcal=2500.0, goal=NutritionGoal.gain, pace=NutritionPace.gentle, tables=TABLES
    )
    assert adjusted == pytest.approx(2500.0 * 1.05)
    assert capped is False


def test_apply_goal_adjustment_maintain_is_unchanged() -> None:
    adjusted, capped = apply_goal_adjustment(
        tdee_kcal=2500.0, goal=NutritionGoal.maintain, pace=NutritionPace.standard, tables=TABLES
    )
    assert adjusted == pytest.approx(2500.0)
    assert capped is False


def test_notice_uses_registered_message() -> None:
    n = energy.notice(NutritionNoticeCode.health_disclaimer)
    assert n.code == NutritionNoticeCode.health_disclaimer
    assert len(n.message_es) > 10


def test_calculate_target_normal_case_macros_match_kcal_exactly() -> None:
    # Peso alto y actividad sedentaria: domina el suelo de grasa en g/kg (no el de % de
    # kcal) y ni el suelo de kcal ni el tope de déficit entran en juego (único aviso
    # esperado: el descargo de salud, que siempre está presente).
    target = calculate_target(
        make_input(
            weight_kg=100.0,
            activity_level=ActivityLevel.sedentary,
            training_days_per_week=0,
        )
    )
    assert not target.blocked
    assert target.block is None
    assert target.target_kcal is not None
    assert target.protein_g is not None
    assert target.fat_g is not None
    assert target.carbs_g is not None
    total = 4 * target.protein_g + 4 * target.carbs_g + 9 * target.fat_g
    assert total == pytest.approx(target.target_kcal, abs=0.01)
    assert target.target_kcal >= max(target.bmr_kcal, TABLES.safety.kcal_floor[Sex.male])
    codes = {n.code for n in target.notices}
    assert codes == {NutritionNoticeCode.health_disclaimer}


def test_calculate_target_blocked_under_18() -> None:
    target = calculate_target(make_input(age_years=15))
    assert target.blocked
    assert target.block is not None
    assert target.block.reason_code.value == "under_18"
    assert target.target_kcal is None
    assert target.protein_g is None


def test_calculate_target_blocked_pregnant() -> None:
    target = calculate_target(make_input(pregnant=True))
    assert target.blocked
    assert target.block is not None
    assert target.block.reason_code.value == "pregnant"


def test_calculate_target_blocked_breastfeeding() -> None:
    target = calculate_target(make_input(breastfeeding=True))
    assert target.blocked
    assert target.block is not None
    assert target.block.reason_code.value == "breastfeeding"


def test_calculate_target_low_bmi_blocks_lose() -> None:
    target = calculate_target(make_input(goal=NutritionGoal.lose, height_cm=190.0, weight_kg=55.0))
    assert not target.blocked
    assert target.requested_goal == NutritionGoal.lose
    assert target.effective_goal == NutritionGoal.maintain
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.lose_blocked_low_bmi in codes


def test_calculate_target_kcal_never_below_floor_even_for_extreme_lose() -> None:
    target = calculate_target(
        make_input(
            sex=Sex.female,
            weight_kg=45.0,
            height_cm=150.0,
            age_years=55,
            activity_level=ActivityLevel.sedentary,
            training_days_per_week=0,
            goal=NutritionGoal.lose,
        )
    )
    assert target.target_kcal == pytest.approx(TABLES.safety.kcal_floor[Sex.female])
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.kcal_floor_applied in codes


def test_calculate_target_deficit_is_capped_for_very_high_tdee() -> None:
    target = calculate_target(
        make_input(
            weight_kg=400.0,
            height_cm=250.0,
            age_years=20,
            activity_level=ActivityLevel.sedentary,
            training_days_per_week=0,
            goal=NutritionGoal.lose,
        )
    )
    assert target.tdee_kcal - (target.target_kcal or 0.0) <= 500.0 + 1e-6
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.deficit_capped in codes


def test_calculate_target_fat_floor_applied_for_light_high_kcal_profile() -> None:
    target = calculate_target(
        make_input(
            sex=Sex.female,
            weight_kg=48.0,
            height_cm=170.0,
            age_years=22,
            activity_level=ActivityLevel.high,
            training_days_per_week=6,
            goal=NutritionGoal.gain,
            pace=NutritionPace.standard,
        )
    )
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.fat_floor_applied in codes


def test_calculate_target_unspecified_sex_uses_average_method() -> None:
    target = calculate_target(make_input(sex=Sex.unspecified))
    assert target.method == BmrMethod.mifflin_average


def test_calculate_target_protein_clamped_notice_with_monkeypatched_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El `protein_g_per_kg` real siempre respeta [min, max]; se fuerza un valor fuera de
    rango con una tabla sintética para probar la rama de aviso `protein_clamped`."""
    out_of_range_protein = TABLES.protein_g_per_kg.model_copy(update={"gain": 9.0})
    custom_tables = TABLES.model_copy(update={"protein_g_per_kg": out_of_range_protein})
    monkeypatch.setattr(energy, "load_nutrition_tables", lambda: custom_tables)

    target = calculate_target(make_input(goal=NutritionGoal.gain))
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.protein_clamped in codes
    assert target.protein_g == pytest.approx(TABLES.protein_g_per_kg.max * 80.0)


def test_protein_in_obesity_uses_adjusted_bodyweight() -> None:
    target = calculate_target(make_input(weight_kg=130.0, height_cm=175.0, goal=NutritionGoal.lose))
    assert target.protein_g == pytest.approx(TABLES.protein_g_per_kg.lose * 27 * 1.75**2)
    assert target.protein_g is not None
    assert target.protein_g < 220.0


def test_protein_is_capped_at_the_absolute_daily_maximum(monkeypatch: pytest.MonkeyPatch) -> None:
    custom_tables = TABLES.model_copy(update={"protein_max_g_per_day": 120.0})
    monkeypatch.setattr(energy, "load_nutrition_tables", lambda: custom_tables)
    target = calculate_target(make_input(goal=NutritionGoal.gain))  # 1,8 g/kg * 80 = 144 g
    assert target.protein_g == pytest.approx(120.0)
    codes = [n.code for n in target.notices]
    assert codes.count(NutritionNoticeCode.protein_clamped) == 1


def test_protein_cap_does_not_duplicate_the_clamped_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_of_range = TABLES.protein_g_per_kg.model_copy(update={"gain": 9.0})
    custom_tables = TABLES.model_copy(
        update={"protein_g_per_kg": out_of_range, "protein_max_g_per_day": 150.0}
    )
    monkeypatch.setattr(energy, "load_nutrition_tables", lambda: custom_tables)
    target = calculate_target(make_input(goal=NutritionGoal.gain))
    assert target.protein_g == pytest.approx(150.0)
    codes = [n.code for n in target.notices]
    assert codes.count(NutritionNoticeCode.protein_clamped) == 1

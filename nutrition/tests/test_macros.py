"""`forja_nutrition/macros.py`: reparto de proteína, grasa, carbohidratos y fibra (§8.2)."""

from __future__ import annotations

from forja_nutrition.macros import (
    carbs_g_from_remainder,
    clamp_protein_g_per_kg,
    fat_floor_governed_by_percentage,
    fiber_g_for,
    protein_g_per_kg_for_goal,
    resolve_energy_and_fat,
)
from forja_nutrition.models import NutritionGoal
from forja_nutrition.tables import FatTable, ProteinTable, load_nutrition_tables

TABLE = load_nutrition_tables().protein_g_per_kg
FAT_TABLE = load_nutrition_tables().fat


def test_protein_g_per_kg_for_goal_matches_table() -> None:
    assert protein_g_per_kg_for_goal(NutritionGoal.lose, TABLE) == TABLE.lose
    assert protein_g_per_kg_for_goal(NutritionGoal.recomp, TABLE) == TABLE.recomp
    assert protein_g_per_kg_for_goal(NutritionGoal.gain, TABLE) == TABLE.gain
    assert protein_g_per_kg_for_goal(NutritionGoal.maintain, TABLE) == TABLE.default


def test_clamp_protein_g_per_kg_within_range_is_unchanged() -> None:
    value, clamped = clamp_protein_g_per_kg(1.8, TABLE)
    assert value == 1.8
    assert clamped is False


def test_clamp_protein_g_per_kg_below_min() -> None:
    value, clamped = clamp_protein_g_per_kg(0.5, TABLE)
    assert value == TABLE.min
    assert clamped is True


def test_clamp_protein_g_per_kg_above_max() -> None:
    value, clamped = clamp_protein_g_per_kg(5.0, TABLE)
    assert value == TABLE.max
    assert clamped is True


def test_resolve_energy_and_fat_normal_case_keeps_preliminary_kcal() -> None:
    # proteína y grasa mínimas muy por debajo de una preliminary_kcal generosa
    kcal, fat_g = resolve_energy_and_fat(
        weight_kg=80.0, protein_g=140.0, preliminary_kcal=2500.0, fat_table=FAT_TABLE
    )
    assert kcal == 2500.0
    assert fat_g >= FAT_TABLE.min_g_per_kg * 80.0


def test_resolve_energy_and_fat_raises_kcal_when_floors_exceed_preliminary() -> None:
    # persona muy pesada con una preliminary_kcal deliberadamente baja: los suelos de
    # proteína+grasa exigen más kcal de las que había
    kcal, fat_g = resolve_energy_and_fat(
        weight_kg=400.0, protein_g=840.0, preliminary_kcal=1500.0, fat_table=FAT_TABLE
    )
    needed = 840.0 * 4 + fat_g * 9
    assert kcal >= needed - 1e-6
    assert kcal > 1500.0


def test_fat_floor_governed_by_percentage_true_case() -> None:
    # kcal alto y peso bajo: el 20 % de kcal supera al suelo de g/kg
    assert fat_floor_governed_by_percentage(weight_kg=50.0, target_kcal=3000.0, fat_table=FAT_TABLE)


def test_fat_floor_governed_by_percentage_false_case() -> None:
    # kcal bajo y peso alto: domina el suelo de g/kg
    assert not fat_floor_governed_by_percentage(
        weight_kg=120.0, target_kcal=1200.0, fat_table=FAT_TABLE
    )


def test_carbs_g_from_remainder_normal() -> None:
    carbs = carbs_g_from_remainder(target_kcal=2000.0, protein_g=150.0, fat_g=60.0)
    # 2000 - 600 - 540 = 860 -> /4 = 215
    assert carbs == 215.0


def test_carbs_g_from_remainder_never_negative() -> None:
    carbs = carbs_g_from_remainder(target_kcal=1000.0, protein_g=300.0, fat_g=100.0)
    assert carbs == 0.0


def test_fiber_g_for() -> None:
    assert fiber_g_for(target_kcal=2000.0, fiber_g_per_1000_kcal=14.0) == 28.0


def test_resolve_energy_and_fat_with_synthetic_table_hits_pct_branch_early() -> None:
    custom_fat_table = FatTable(min_g_per_kg=0.1, min_pct_kcal=0.5)
    kcal, fat_g = resolve_energy_and_fat(
        weight_kg=60.0, protein_g=90.0, preliminary_kcal=1800.0, fat_table=custom_fat_table
    )
    assert kcal >= 1800.0
    assert fat_g > 0


def test_protein_table_is_a_pydantic_model() -> None:
    table = ProteinTable(default=1.8, lose=2.1, recomp=2.0, gain=1.8, min=1.6, max=2.2)
    assert table.default == 1.8

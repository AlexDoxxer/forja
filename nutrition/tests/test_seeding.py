"""`forja_nutrition/seeding.py`: derivación determinista de semilla (§8.3, §8.6)."""

from __future__ import annotations

from forja_nutrition.seeding import derive_seed, effective_seed
from tests.conftest import make_input


def test_derive_seed_is_deterministic() -> None:
    nutrition_input = make_input()
    assert derive_seed(nutrition_input) == derive_seed(nutrition_input)


def test_derive_seed_differs_for_different_inputs() -> None:
    a = make_input(weight_kg=80.0)
    b = make_input(weight_kg=81.0)
    assert derive_seed(a) != derive_seed(b)


def test_derive_seed_is_within_valid_seed_range() -> None:
    seed = derive_seed(make_input())
    assert 0 <= seed <= 2**53 - 1


def test_effective_seed_uses_explicit_seed_when_given() -> None:
    nutrition_input = make_input(seed=12345)
    assert effective_seed(nutrition_input) == 12345


def test_effective_seed_derives_when_seed_is_none() -> None:
    nutrition_input = make_input(seed=None)
    assert effective_seed(nutrition_input) == derive_seed(nutrition_input)

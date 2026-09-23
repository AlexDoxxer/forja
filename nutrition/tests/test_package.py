"""Comprobaciones del paquete: versión semver coherente con los metadatos instalados."""

import re
from importlib.metadata import version

import forja_nutrition

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def test_nutrition_version_is_semver() -> None:
    assert SEMVER.fullmatch(forja_nutrition.NUTRITION_VERSION)


def test_nutrition_version_matches_distribution_metadata() -> None:
    assert version("forja-nutrition") == forja_nutrition.NUTRITION_VERSION
    assert forja_nutrition.__version__ == forja_nutrition.NUTRITION_VERSION

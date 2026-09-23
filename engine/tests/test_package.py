"""Comprobaciones del paquete: versión semver coherente con los metadatos instalados."""

import re
from importlib.metadata import version

import forja_engine

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def test_engine_version_is_semver() -> None:
    assert SEMVER.fullmatch(forja_engine.ENGINE_VERSION)


def test_engine_version_matches_distribution_metadata() -> None:
    assert version("forja-engine") == forja_engine.ENGINE_VERSION
    assert forja_engine.__version__ == forja_engine.ENGINE_VERSION

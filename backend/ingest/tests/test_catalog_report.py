"""Catálogo, ``ExerciseCard`` contra el contrato OpenAPI e informe reproducible."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from ingest.catalog import Catalog, build_catalog, write_cards
from ingest.enrich import EnrichmentError
from ingest.names import NamesError
from ingest.report import quality_problems, render_report, staple_matrix
from ingest.source import RawExercise
from ingest.specs import IngestSpecs
from ingest.tests.conftest import DATASET_COMMIT, REPO_ROOT


def card_validator() -> Draft202012Validator:
    """Valida contra ``#/components/schemas/ExerciseCard`` resolviendo las ``$ref``."""
    openapi: dict[str, Any] = yaml.safe_load(
        (REPO_ROOT / "contracts" / "openapi.yaml").read_text("utf-8")
    )
    schema = {
        "$ref": "#/components/schemas/ExerciseCard",
        "components": openapi["components"],
    }
    return Draft202012Validator(schema)


def test_cards_match_openapi_contract(full_catalog: Catalog, tmp_path: Path) -> None:
    output = tmp_path / "cards" / "catalog.json"
    write_cards(full_catalog.cards(), output)
    cards = json.loads(output.read_text("utf-8"))
    assert len(cards) == 1324
    assert [card["id"] for card in cards] == sorted(card["id"] for card in cards)
    validator = card_validator()
    for card in cards:
        errors = list(validator.iter_errors(card))
        assert not errors, (card["id"], errors[0].message)
    assert all(card["deprecated"] is False for card in cards)
    assert sum(card["is_staple"] for card in cards) == 144


def test_fixture_catalog_builds_without_full_dataset(fixture_catalog: Catalog) -> None:
    assert len(fixture_catalog.entries) == 60
    card = fixture_catalog.by_id()["0043"].card(deprecated=True)
    assert card.deprecated
    assert card.name_es == "sentadilla profunda con barra"


def test_full_dataset_rejects_unknown_references(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    with pytest.raises((EnrichmentError, NamesError), match="ids inexistentes"):
        build_catalog(fixture_records, specs)


def test_missing_spanish_name_aborts(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    names = {key: value for key, value in specs.names_es.items() if key != "0043"}
    with pytest.raises(NamesError, match="0043"):
        build_catalog(fixture_records, replace(specs, names_es=names), full_dataset=False)


def test_report_is_reproducible_and_committed(full_catalog: Catalog, specs: IngestSpecs) -> None:
    rendered = render_report(full_catalog, specs, DATASET_COMMIT)
    assert rendered == render_report(full_catalog, specs, DATASET_COMMIT)
    committed = (REPO_ROOT / "docs" / "enrichment-report.md").read_text("utf-8")
    assert committed == rendered, "Regenera el informe con `forja-ingest report`"
    assert "❌" not in rendered


def test_quality_problems_detect_missing_staples_and_other(
    full_catalog: Catalog, specs: IngestSpecs
) -> None:
    stripped = Catalog(
        entries=tuple(
            replace(entry, enrichment=replace(entry.enrichment, is_staple=False))
            for entry in full_catalog.entries
        ),
        alternatives=full_catalog.alternatives,
    )
    problems = quality_problems(stripped, specs)
    assert len(problems) == len(staple_matrix(stripped))
    orphan = replace(
        full_catalog.entries[0],
        enrichment=replace(full_catalog.entries[0].enrichment, movement_pattern="other"),
    )
    with_other = Catalog(entries=(orphan,), alternatives={})
    assert any("other sin justificar" in problem for problem in quality_problems(with_other, specs))


def test_full_dataset_rejects_references_to_missing_exercises(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    records = [record for record in all_records if record.id != "0043"]
    names = {key: value for key, value in specs.names_es.items() if key != "0043"}
    with pytest.raises(EnrichmentError, match="0043"):
        build_catalog(records, replace(specs, names_es=names))

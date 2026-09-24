"""Carga de tablas de ``specs/`` y lectura/validación del dataset de origen."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from ingest.source import SourceError, load_dataset, parse_records, validate_against_schema
from ingest.specs import SPECS_DIR_ENV, SpecError, default_specs_dir, load_names_es, load_specs
from ingest.tests.conftest import FIXTURES, REPO_ROOT, fixture_data


def _copy_specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    shutil.copytree(REPO_ROOT / "specs", target)
    return target


def test_default_specs_dir_is_repository_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SPECS_DIR_ENV, raising=False)
    assert default_specs_dir() == REPO_ROOT / "specs"


def test_specs_dir_can_come_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs_dir = _copy_specs(tmp_path)
    monkeypatch.setenv(SPECS_DIR_ENV, str(specs_dir))
    assert default_specs_dir() == specs_dir
    assert load_specs().rules.version == 1


def test_load_specs_reads_every_table() -> None:
    specs = load_specs()
    assert "pectorals" in specs.muscles.map
    assert specs.equipment.map["body weight"].code == "bodyweight"
    assert len(specs.names_es) == 1324
    assert 120 <= len(specs.staple_ids()) <= 160


def test_missing_file_is_a_spec_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    (specs_dir / "enrichment-rules.yaml").unlink()
    with pytest.raises(SpecError, match="No se puede leer"):
        load_specs(specs_dir)


def test_invalid_yaml_is_a_spec_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    (specs_dir / "overrides" / "staples.yaml").write_text("staples: [unclosed", encoding="utf-8")
    with pytest.raises(SpecError, match="YAML inválido"):
        load_specs(specs_dir)


def test_schema_violation_is_a_spec_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    path = specs_dir / "overrides" / "enrichment-overrides.yaml"
    path.write_text("version: 2\nby_id:\n  '0001': {movement_pattern: flying}\n", encoding="utf-8")
    with pytest.raises(SpecError, match="no cumple su esquema"):
        load_specs(specs_dir)


def test_muscle_map_must_target_canonical_codes(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    path = specs_dir / "muscle-normalization.yaml"
    path.write_text(path.read_text("utf-8").replace("groin: adductors", "groin: groin"), "utf-8")
    with pytest.raises(SpecError):
        load_specs(specs_dir)


def test_staple_listed_twice_is_rejected(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    path = specs_dir / "overrides" / "staples.yaml"
    path.write_text(
        "version: 1\nstaples:\n  squat: ['0043']\n  lunge: ['0043']\n", encoding="utf-8"
    )
    with pytest.raises(SpecError, match="más de un patrón"):
        load_specs(specs_dir)


@pytest.mark.parametrize("content", ["[]", '{"0001": 3}', "{not json"])
def test_names_es_must_be_an_object_of_strings(tmp_path: Path, content: str) -> None:
    path = tmp_path / "names_es.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SpecError):
        load_names_es(path)


# ------------------------------------------------------------------------ dataset
def test_fixture_dataset_validates_and_is_sorted(fixture_records: tuple[Any, ...]) -> None:
    ids = [record.id for record in fixture_records]
    assert len(ids) == 60
    assert ids == sorted(ids)


def test_schema_violation_fails(tmp_path: Path) -> None:
    data = fixture_data()
    data[0]["body_part"] = "tail"
    schema = json.loads((FIXTURES / "exercises.schema.json").read_text("utf-8"))
    with pytest.raises(SourceError, match="no cumple exercises.schema.json"):
        validate_against_schema(data, schema)


def test_missing_or_broken_dataset_files(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="No se puede leer"):
        load_dataset(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "exercises.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(SourceError, match="no es JSON válido"):
        load_dataset(tmp_path, validate_schema=False)


def test_parse_records_rejects_non_list_and_invalid_items() -> None:
    with pytest.raises(SourceError, match="lista"):
        parse_records({"id": "0001"})
    with pytest.raises(SourceError, match="inválido"):
        parse_records([{"id": "1"}])


def test_parse_records_rejects_duplicate_ids_and_missing_languages() -> None:
    first = fixture_data()[0]
    with pytest.raises(SourceError, match="duplicado"):
        parse_records([first, first])
    broken = json.loads(json.dumps(first))
    del broken["instruction_steps"]["ko"]
    with pytest.raises(SourceError, match="ko"):
        parse_records([broken])

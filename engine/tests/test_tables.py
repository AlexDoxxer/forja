"""F1-ENG-01: carga y validación de las tablas YAML, referencias rotas y ``tables_hash``."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from forja_engine.models import EquipmentCode, ExerciseRole, MuscleCode, MuscleGroup, VolumeGroup
from forja_engine.tables import (
    DEFAULT_SPECS_DIR,
    FILES,
    TablesError,
    default_tables,
    load_tables,
)

Mutation = Callable[[dict[str, Any]], None]


def copy_specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    target.mkdir()
    for name in FILES.values():
        shutil.copy(DEFAULT_SPECS_DIR / name, target / name)
    return target


def mutate(specs: Path, name: str, change: Mutation) -> None:
    path = specs / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_default_tables_load_and_hash_is_stable(tmp_path: Path) -> None:
    tables = default_tables()
    assert len(tables.tables_hash) == 64
    assert load_tables(copy_specs(tmp_path)).tables_hash == tables.tables_hash
    assert default_tables() is tables


def test_hash_changes_when_a_table_changes(tmp_path: Path) -> None:
    specs = copy_specs(tmp_path)
    mutate(specs, "prescription.yaml", lambda d: d["min_rest_s"].update(main=100))
    assert load_tables(specs).tables_hash != default_tables().tables_hash


def test_missing_file_fails_fast(tmp_path: Path) -> None:
    specs = copy_specs(tmp_path)
    (specs / "engine-rules.yaml").unlink()
    with pytest.raises(TablesError, match=r"engine-rules\.yaml: no existe"):
        load_tables(specs)


def test_malformed_yaml_fails_fast(tmp_path: Path) -> None:
    specs = copy_specs(tmp_path)
    (specs / "split-templates.yaml").write_text("splits: [unclosed", encoding="utf-8")
    with pytest.raises(TablesError, match="YAML mal formado"):
        load_tables(specs)


def _set(path: list[str | int], value: object) -> Mutation:
    def change(data: dict[str, Any]) -> None:
        node: Any = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return change


def _delete(path: list[str | int]) -> Mutation:
    def change(data: dict[str, Any]) -> None:
        node: Any = data
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]

    return change


BROKEN: list[tuple[str, Mutation, str]] = [
    ("split-templates.yaml", _delete(["splits", "3"]), "splits\\[3\\]"),
    ("split-templates.yaml", _set(["splits", "3", "advanced"], ["push", "pull"]), "3 días"),
    (
        "split-templates.yaml",
        _set(["splits", "1", "advanced"], ["nope"]),
        "plantillas inexistentes",
    ),
    ("split-templates.yaml", _delete(["emphasis_overrides", "core"]), "todos los énfasis"),
    (
        "split-templates.yaml",
        _set(["emphasis_overrides", "arms", "append_block", "to"], ["ghost"]),
        "plantillas inexistentes",
    ),
    (
        "split-templates.yaml",
        _delete(["emphasis_overrides", "lower_glutes", "with"]),
        "replace_last_of y with",
    ),
    ("volume-targets.yaml", _set(["groups"], ["chest"]), "groups debe coincidir"),
    ("volume-targets.yaml", _delete(["targets", "toning"]), "targets\\[toning\\]"),
    (
        "volume-targets.yaml",
        _delete(["targets", "toning", "beginner", "default"]),
        "necesita default",
    ),
    (
        "volume-targets.yaml",
        _set(["targets", "toning", "beginner", "legs"], [1, 2]),
        "necesita default",
    ),
    ("volume-targets.yaml", _set(["targets", "toning", "beginner", "arms"], [9, 2]), "supera"),
    ("volume-targets.yaml", _delete(["emphasis_multipliers", "core"]), "todos los énfasis"),
    ("volume-targets.yaml", _set(["emphasis_multipliers", "core", "neck"], 2), "inválidos"),
    ("prescription.yaml", _delete(["table", "toning"]), "main y accessory"),
    ("prescription.yaml", _delete(["experience_adjustments", "advanced"]), "tres niveles"),
    ("prescription.yaml", _set(["table", "toning", "main", "reps"], [12, 8]), "supera"),
    ("periodization.yaml", _set(["default_weeks"], 9), "allowed_weeks"),
    ("sex-modifiers.yaml", _delete(["explanation_es", "male"]), "tres valores de sexo"),
    ("equipment-normalization.yaml", _delete(["presets", "custom"]), "todos los presets"),
    ("muscle-normalization.yaml", _delete(["canonical", "neck"]), "todos los MuscleCode"),
    ("engine-rules.yaml", _delete(["goal_defaults", "toning"]), "todos los objetivos"),
    ("engine-rules.yaml", _delete(["pattern_groups", "neck"]), "todos los patrones"),
    ("engine-rules.yaml", _delete(["group_names_es", "cardio"]), "todos los grupos"),
    (
        "engine-rules.yaml",
        _set(["relaxation_order"], ["difficulty", "difficulty", "staple", "target_group"]),
        "cada relajación",
    ),
    ("engine-rules.yaml", _delete(["difficulty", "cap", "advanced"]), "tres niveles"),
    ("engine-rules.yaml", _delete(["allocation", "bounds_by_role", "core"]), "bounds_by_role"),
    ("engine-rules.yaml", _set(["allocation", "bounds_by_role", "core"], [5, 1]), "supera"),
    ("engine-rules.yaml", _delete(["progression_loads", "step_kg", "default"]), "step_kg"),
    ("engine-rules.yaml", _set(["progression_loads", "step_kg", "dumbbell"], 0), "step_kg"),
]


@pytest.mark.parametrize(("name", "change", "message"), BROKEN)
def test_broken_tables_fail_fast(tmp_path: Path, name: str, change: Mutation, message: str) -> None:
    specs = copy_specs(tmp_path)
    mutate(specs, name, change)
    with pytest.raises(TablesError, match=message):
        load_tables(specs)


def test_table_helpers() -> None:
    tables = default_tables()
    assert tables.prescription.min_rest_s.for_role(ExerciseRole.CARDIO) is None
    assert tables.prescription.min_rest_s.for_role(ExerciseRole.CORE) == 30
    assert tables.engine_rules.progression_loads.step_for(EquipmentCode.CABLE) == 2.5
    assert tables.engine_rules.progression_loads.step_for(EquipmentCode.DUMBBELL) == 2.0
    assert tables.volume_group(MuscleCode.ADDUCTORS) is None
    assert tables.volume_group(MuscleCode.LATS) is VolumeGroup.BACK
    assert tables.muscle_group(MuscleCode.NECK) is MuscleGroup.OTHER

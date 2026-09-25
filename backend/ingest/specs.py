"""Carga y validación (fallo rápido) de las tablas de ``specs/`` que usa la ingesta.

Ficheros leídos (solo lectura salvo ``specs/overrides/``, propiedad de ``ingesta-datos``):

- ``muscle-normalization.yaml`` y ``equipment-normalization.yaml`` (vocabularios).
- ``enrichment-rules.yaml`` (reglas base) y ``overrides/enrichment-overrides.yaml``
  (reglas prioritarias, excepciones ``other`` justificadas y overrides por id).
- ``overrides/name-fixes.yaml``, ``overrides/staples.yaml``, ``overrides/names_es.json``,
  ``overrides/names-es-exceptions.yaml`` y ``glossary-es.yaml``.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Final

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from ingest.domain import (
    EquipmentCode,
    EquipmentGroup,
    ExerciseRole,
    Laterality,
    LoadType,
    Mechanic,
    MovementPattern,
    MuscleCode,
    MuscleGroup,
    MuscleRegion,
)

SPECS_DIR_ENV: Final = "FORJA_SPECS_DIR"
ExerciseId = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}$")]
Keyword = Annotated[str, StringConstraints(min_length=1)]


class SpecError(ValueError):
    """Una tabla de ``specs/`` no existe, no es válida o tiene referencias rotas."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ------------------------------------------------------------------------ vocabularios
class CanonicalMuscle(_Frozen):
    es: str
    en: str
    region: MuscleRegion
    group: MuscleGroup


class MuscleSpec(_Frozen):
    version: int
    canonical: dict[MuscleCode, CanonicalMuscle]
    map: dict[str, MuscleCode]

    @field_validator("map")
    @classmethod
    def _lowercase_keys(cls, value: dict[str, MuscleCode]) -> dict[str, MuscleCode]:
        return {key.strip().lower(): code for key, code in value.items()}


class EquipmentEntry(_Frozen):
    code: EquipmentCode
    es: str
    group: EquipmentGroup


class EquipmentSpec(_Frozen):
    version: int
    map: dict[str, EquipmentEntry]
    presets: dict[str, Any]

    @field_validator("map")
    @classmethod
    def _lowercase_keys(cls, value: dict[str, EquipmentEntry]) -> dict[str, EquipmentEntry]:
        return {key.strip().lower(): entry for key, entry in value.items()}


# ------------------------------------------------------------------------- nombres EN
class NameFixes(_Frozen):
    version: int
    replace_substrings: dict[str, str]
    by_id: dict[ExerciseId, str] = Field(default_factory=dict)


# ------------------------------------------------------------------------ enriquecimiento
def _as_tuple(value: Any) -> Any:
    """Admite un escalar en YAML (``body_part: cardio``) como lista de un elemento."""
    if isinstance(value, str):
        return (value,)
    return value


class PatternRule(_Frozen):
    """Regla de patrón: todas las condiciones presentes deben cumplirse (AND); en cada lista
    basta con un elemento (OR). ``name_any``/``name_none`` buscan subcadenas en el nombre
    visible en minúsculas rodeado de un espacio a cada lado (un espacio en la palabra clave
    actúa como límite de palabra)."""

    pattern: MovementPattern
    name_any: tuple[Keyword, ...] | None = None
    name_none: tuple[Keyword, ...] | None = None
    target: tuple[str, ...] | None = None
    body_part: tuple[str, ...] | None = None
    equipment: tuple[str, ...] | None = None

    @field_validator("name_any", "name_none", "target", "body_part", "equipment", mode="before")
    @classmethod
    def _scalar_to_tuple(cls, value: Any) -> Any:
        return _as_tuple(value)


class DifficultyRules(_Frozen):
    level_1_any: tuple[Keyword, ...]
    level_3_any: tuple[Keyword, ...]
    default: Annotated[int, Field(ge=1, le=3)]


class LoadTypeRules(_Frozen):
    time_any: tuple[Keyword, ...]
    assisted_any: tuple[Keyword, ...]


class EnrichmentRules(_Frozen):
    version: int
    pattern_rules: tuple[PatternRule, ...]
    compound_patterns: tuple[MovementPattern, ...]
    isolation_name_hints: tuple[Keyword, ...]
    difficulty: DifficultyRules
    laterality_unilateral_any: tuple[Keyword, ...]
    load_type: LoadTypeRules


class ExerciseOverride(_Frozen):
    movement_pattern: MovementPattern | None = None
    mechanic: Mechanic | None = None
    role: ExerciseRole | None = None
    difficulty: Annotated[int, Field(ge=1, le=3)] | None = None
    laterality: Laterality | None = None
    load_type: LoadType | None = None
    is_staple: bool | None = None


class KeywordAdjustments(_Frozen):
    """Ajustes de palabras clave que complementan las listas de ``enrichment-rules.yaml``."""

    difficulty_level_1_any: tuple[Keyword, ...] = ()
    difficulty_level_3_any: tuple[Keyword, ...] = ()
    difficulty_level_1_equipment: tuple[str, ...] = ()
    laterality_unilateral_any: tuple[Keyword, ...] = ()
    laterality_bilateral_any: tuple[Keyword, ...] = ()
    time_any: tuple[Keyword, ...] = ()
    time_none: tuple[Keyword, ...] = ()
    isolation_name_any: tuple[Keyword, ...] = ()
    isolation_name_none: tuple[Keyword, ...] = ()
    warmup_name_any: tuple[Keyword, ...] = ()


class EnrichmentOverrides(_Frozen):
    version: int
    pattern_rules: tuple[PatternRule, ...] = ()
    keywords: KeywordAdjustments = KeywordAdjustments()
    other_justified: dict[ExerciseId, str] = Field(default_factory=dict)
    by_id: dict[ExerciseId, ExerciseOverride] = Field(default_factory=dict)


class Staples(_Frozen):
    version: int
    staples: dict[MovementPattern, tuple[ExerciseId, ...]]


# ----------------------------------------------------------------------- nombres ES
class Glossary(_Frozen):
    version: int
    style: tuple[str, ...]
    terms: dict[str, str]


class IntentionalDuplicate(_Frozen):
    """Ejercicios de grupos de variantes distintos que comparten nombre ES a propósito."""

    ids: tuple[ExerciseId, ...] = Field(min_length=2)
    reason: str = Field(min_length=1)


class NamesExceptions(_Frozen):
    """Excepciones justificadas a las comprobaciones de nombres ES.

    ``glossary``: ``{id: {término: motivo}}`` cuando un término no se aplica literalmente.
    """

    version: int
    glossary: dict[ExerciseId, dict[str, str]] = Field(default_factory=dict)
    intentional_duplicates: tuple[IntentionalDuplicate, ...] = ()


# ------------------------------------------------------------------------------ carga
def default_specs_dir() -> Path:
    """``$FORJA_SPECS_DIR`` o, si no está definida, el ``specs/`` del repositorio."""
    configured = os.environ.get(SPECS_DIR_ENV)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "specs"


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except OSError as exc:
        msg = f"No se puede leer {path}: {exc}"
        raise SpecError(msg) from exc
    except yaml.YAMLError as exc:
        msg = f"YAML inválido en {path}: {exc}"
        raise SpecError(msg) from exc


def _parse[M: BaseModel](model: type[M], path: Path) -> M:
    try:
        return model.model_validate(_read_yaml(path))
    except ValueError as exc:
        msg = f"{path} no cumple su esquema: {exc}"
        raise SpecError(msg) from exc


def load_names_es(path: Path) -> dict[str, str]:
    """Lee ``names_es.json`` (objeto ``{id: nombre}``)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"No se puede leer {path}: {exc}"
        raise SpecError(msg) from exc
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        msg = f"{path} debe ser un objeto JSON {{id: nombre}} de cadenas"
        raise SpecError(msg)
    return dict(data)


@dataclass(frozen=True, slots=True)
class IngestSpecs:
    """Todas las tablas que necesita la ingesta, ya validadas."""

    muscles: MuscleSpec
    equipment: EquipmentSpec
    name_fixes: NameFixes
    rules: EnrichmentRules
    overrides: EnrichmentOverrides
    staples: Staples
    names_es: dict[str, str]
    glossary: Glossary
    names_exceptions: NamesExceptions

    def staple_ids(self) -> dict[str, MovementPattern]:
        """``{id: patrón}`` de todos los staples (un id solo puede figurar una vez)."""
        result: dict[str, MovementPattern] = {}
        for pattern, ids in self.staples.staples.items():
            for exercise_id in ids:
                if exercise_id in result:
                    msg = f"El staple {exercise_id} aparece en más de un patrón"
                    raise SpecError(msg)
                result[exercise_id] = pattern
        return result


def load_specs(specs_dir: Path | None = None) -> IngestSpecs:
    """Carga y valida todas las tablas; cualquier fallo lanza :class:`SpecError`."""
    base = specs_dir or default_specs_dir()
    overrides_dir = base / "overrides"
    specs = IngestSpecs(
        muscles=_parse(MuscleSpec, base / "muscle-normalization.yaml"),
        equipment=_parse(EquipmentSpec, base / "equipment-normalization.yaml"),
        name_fixes=_parse(NameFixes, overrides_dir / "name-fixes.yaml"),
        rules=_parse(EnrichmentRules, base / "enrichment-rules.yaml"),
        overrides=_parse(EnrichmentOverrides, overrides_dir / "enrichment-overrides.yaml"),
        staples=_parse(Staples, overrides_dir / "staples.yaml"),
        names_es=load_names_es(overrides_dir / "names_es.json"),
        glossary=_parse(Glossary, base / "glossary-es.yaml"),
        names_exceptions=_parse(NamesExceptions, overrides_dir / "names-es-exceptions.yaml"),
    )
    specs.staple_ids()
    return specs

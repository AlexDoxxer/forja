"""Motor de reglas de enriquecimiento (MASTER_PROMPT §6.3).

Prioridad de cada atributo: override por id (``enrichment-overrides.yaml#by_id``) ⇒ reglas
prioritarias de los overrides ⇒ reglas base de ``specs/enrichment-rules.yaml``. Las palabras
clave se buscan como subcadenas en el nombre visible (erratas corregidas, sin sufijos de
variante) en minúsculas y rodeado de un espacio, de modo que un espacio en la palabra clave
actúa como límite de palabra.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from ingest.domain import (
    CORE_PATTERNS,
    ExerciseRole,
    Laterality,
    LoadType,
    Mechanic,
    MovementPattern,
)
from ingest.normalize import NormalizedExercise
from ingest.specs import IngestSpecs, PatternRule

STRETCH_KEYWORD: Final = " stretch"


class EnrichmentError(ValueError):
    """Incoherencia entre overrides, staples y el resultado de las reglas."""


@dataclass(frozen=True, slots=True)
class Enrichment:
    movement_pattern: MovementPattern
    mechanic: Mechanic
    role: ExerciseRole
    difficulty: int
    is_staple: bool
    laterality: Laterality
    load_type: LoadType
    pattern_source: str


def match_name(name: str) -> str:
    """Forma normalizada del nombre sobre la que se buscan las palabras clave."""
    return f" {' '.join(name.lower().split())} "


def _contains_any(name: str, keywords: Iterable[str] | None) -> bool:
    return keywords is not None and any(keyword in name for keyword in keywords)


def rule_matches(rule: PatternRule, exercise: NormalizedExercise) -> bool:
    """Todas las condiciones presentes de la regla se cumplen (AND; OR dentro de cada lista)."""
    name = match_name(exercise.display_name_en)
    checks = (
        rule.name_any is None or _contains_any(name, rule.name_any),
        rule.name_none is None or not _contains_any(name, rule.name_none),
        rule.target is None or exercise.raw_target in rule.target,
        rule.body_part is None or exercise.raw_body_part in rule.body_part,
        rule.equipment is None or exercise.raw_equipment in rule.equipment,
    )
    return all(checks)


def classify_pattern(
    exercise: NormalizedExercise, specs: IngestSpecs
) -> tuple[MovementPattern, str]:
    """Patrón de movimiento y origen de la decisión (``override``, ``rule:N``, ``default``)."""
    override = specs.overrides.by_id.get(exercise.id)
    if override is not None and override.movement_pattern is not None:
        return override.movement_pattern, "override"
    for index, rule in enumerate(specs.overrides.pattern_rules):
        if rule_matches(rule, exercise):
            return rule.pattern, f"override_rule:{index}"
    for index, rule in enumerate(specs.rules.pattern_rules):
        if rule_matches(rule, exercise):
            return rule.pattern, f"rule:{index}"
    return "other", "default"


def _mechanic(pattern: MovementPattern, name: str, specs: IngestSpecs) -> Mechanic:
    rules = specs.rules
    keywords = specs.overrides.keywords
    isolation_hint = (
        _contains_any(name, rules.isolation_name_hints)
        or _contains_any(name, keywords.isolation_name_any)
    ) and not _contains_any(name, keywords.isolation_name_none)
    if pattern in rules.compound_patterns and not isolation_hint:
        return "compound"
    return "isolation"


def _difficulty(exercise: NormalizedExercise, name: str, specs: IngestSpecs) -> int:
    rules = specs.rules.difficulty
    keywords = specs.overrides.keywords
    if _contains_any(name, rules.level_3_any) or _contains_any(
        name, keywords.difficulty_level_3_any
    ):
        return 3
    if (
        _contains_any(name, rules.level_1_any)
        or _contains_any(name, keywords.difficulty_level_1_any)
        or exercise.raw_equipment in keywords.difficulty_level_1_equipment
    ):
        return 1
    return rules.default


def _laterality(name: str, specs: IngestSpecs) -> Laterality:
    keywords = specs.overrides.keywords
    unilateral = _contains_any(name, specs.rules.laterality_unilateral_any) or _contains_any(
        name, keywords.laterality_unilateral_any
    )
    if unilateral and not _contains_any(name, keywords.laterality_bilateral_any):
        return "unilateral"
    return "bilateral"


def _load_type(
    exercise: NormalizedExercise, pattern: MovementPattern, name: str, specs: IngestSpecs
) -> LoadType:
    rules = specs.rules.load_type
    keywords = specs.overrides.keywords
    timed_by_name = (
        _contains_any(name, rules.time_any) or _contains_any(name, keywords.time_any)
    ) and not _contains_any(name, keywords.time_none)
    if timed_by_name or pattern in {"cardio", "mobility"}:
        return "time"
    if _contains_any(name, rules.assisted_any) or exercise.equipment_code == "assisted":
        return "assisted"
    if exercise.equipment_code == "bodyweight":
        return "bodyweight"
    return "external"


def _role(
    exercise: NormalizedExercise,
    pattern: MovementPattern,
    mechanic: Mechanic,
    *,
    is_staple: bool,
    name: str,
    warmup_keywords: Iterable[str],
) -> ExerciseRole:
    if _contains_any(name, warmup_keywords) and not is_staple:
        return "warmup"
    if pattern == "mobility" or STRETCH_KEYWORD in name:
        return "mobility"
    if exercise.raw_body_part == "cardio" or pattern == "cardio":
        return "cardio"
    if pattern in CORE_PATTERNS:
        return "core"
    if mechanic == "compound" and is_staple:
        return "main"
    return "accessory"


def enrich_exercise(exercise: NormalizedExercise, specs: IngestSpecs) -> Enrichment:
    """Calcula todos los atributos de §6.3 para un ejercicio normalizado."""
    name = match_name(exercise.display_name_en)
    override = specs.overrides.by_id.get(exercise.id)
    pattern, source = classify_pattern(exercise, specs)
    staple_ids = specs.staple_ids()
    is_staple = exercise.id in staple_ids
    mechanic = _mechanic(pattern, name, specs)
    difficulty = _difficulty(exercise, name, specs)
    laterality = _laterality(name, specs)
    load_type = _load_type(exercise, pattern, name, specs)
    if override is not None:
        mechanic = override.mechanic or mechanic
        difficulty = override.difficulty or difficulty
        laterality = override.laterality or laterality
        load_type = override.load_type or load_type
        is_staple = is_staple if override.is_staple is None else override.is_staple
    role = _role(
        exercise,
        pattern,
        mechanic,
        is_staple=is_staple,
        name=name,
        warmup_keywords=specs.overrides.keywords.warmup_name_any,
    )
    if override is not None and override.role is not None:
        role = override.role
    return Enrichment(
        movement_pattern=pattern,
        mechanic=mechanic,
        role=role,
        difficulty=difficulty,
        is_staple=is_staple,
        laterality=laterality,
        load_type=load_type,
        pattern_source=source,
    )


def enrich_all(
    exercises: Sequence[NormalizedExercise], specs: IngestSpecs
) -> dict[str, Enrichment]:
    """Enriquece el catálogo y comprueba la coherencia de overrides y staples con él."""
    result = {exercise.id: enrich_exercise(exercise, specs) for exercise in exercises}
    problems: list[str] = []
    for exercise_id, pattern in specs.staple_ids().items():
        enrichment = result.get(exercise_id)
        if enrichment is not None and enrichment.movement_pattern != pattern:
            problems.append(
                f"staple {exercise_id} listado en {pattern} pero su patrón es "
                f"{enrichment.movement_pattern}"
            )
    for exercise_id in specs.overrides.other_justified:
        enrichment = result.get(exercise_id)
        if enrichment is not None and enrichment.movement_pattern != "other":
            problems.append(f"{exercise_id} figura en other_justified pero su patrón no es other")
    if problems:
        raise EnrichmentError("; ".join(problems))
    return result


def unknown_reference_ids(ids: Iterable[str], specs: IngestSpecs) -> tuple[str, ...]:
    """Ids citados en overrides, staples o ``other_justified`` que no existen en el catálogo."""
    known = set(ids)
    referenced = (
        set(specs.overrides.by_id)
        | set(specs.overrides.other_justified)
        | set(specs.staple_ids())
        | set(specs.name_fixes.by_id)
    )
    return tuple(sorted(referenced - known))


def unjustified_other(
    exercises: Sequence[NormalizedExercise],
    enrichments: dict[str, Enrichment],
    specs: IngestSpecs,
) -> tuple[str, ...]:
    """Ids con patrón ``other`` que no figuran en ``other_justified``."""
    return tuple(
        exercise.id
        for exercise in exercises
        if enrichments[exercise.id].movement_pattern == "other"
        and exercise.id not in specs.overrides.other_justified
    )

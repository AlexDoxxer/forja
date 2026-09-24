"""Enriquecimiento (§6.3): reglas, overrides, staples y requisitos sobre el dataset completo."""

from dataclasses import replace

import pytest

from ingest.catalog import Catalog
from ingest.domain import MAIN_PATTERNS, MIN_STAPLES_PER_CELL, STAPLE_EQUIPMENT_GROUPS
from ingest.enrich import (
    EnrichmentError,
    classify_pattern,
    enrich_all,
    enrich_exercise,
    rule_matches,
    unjustified_other,
    unknown_reference_ids,
)
from ingest.normalize import NormalizedExercise, normalize_all
from ingest.report import quality_problems, staple_matrix
from ingest.source import RawExercise
from ingest.specs import (
    EnrichmentOverrides,
    ExerciseOverride,
    IngestSpecs,
    PatternRule,
    Staples,
)


@pytest.fixture(scope="module")
def normalized(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> dict[str, NormalizedExercise]:
    return {exercise.id: exercise for exercise in normalize_all(all_records, specs)}


def test_no_unjustified_other_pattern(full_catalog: Catalog, specs: IngestSpecs) -> None:
    exercises = [entry.exercise for entry in full_catalog.entries]
    enrichments = {entry.exercise.id: entry.enrichment for entry in full_catalog.entries}
    assert unjustified_other(exercises, enrichments, specs) == ()
    others = {
        e.exercise.id for e in full_catalog.entries if e.enrichment.movement_pattern == "other"
    }
    assert others == set(specs.overrides.other_justified)


def test_every_main_pattern_and_equipment_group_has_two_staples(full_catalog: Catalog) -> None:
    cells = staple_matrix(full_catalog)
    assert len(cells) == len(MAIN_PATTERNS) * len(STAPLE_EQUIPMENT_GROUPS)
    for cell in cells:
        assert cell.applicable, cell
        assert len(cell.staple_ids) >= MIN_STAPLES_PER_CELL, cell


def test_full_catalog_has_no_quality_problems(full_catalog: Catalog, specs: IngestSpecs) -> None:
    assert quality_problems(full_catalog, specs) == []


def test_staples_have_their_listed_pattern(full_catalog: Catalog, specs: IngestSpecs) -> None:
    by_id = full_catalog.by_id()
    staples = specs.staple_ids()
    assert 120 <= len(staples) <= 160
    for exercise_id, pattern in staples.items():
        assert by_id[exercise_id].enrichment.movement_pattern == pattern
        assert by_id[exercise_id].enrichment.is_staple


def test_specs_reference_only_existing_ids(full_catalog: Catalog, specs: IngestSpecs) -> None:
    ids = [entry.exercise.id for entry in full_catalog.entries]
    assert unknown_reference_ids(ids, specs) == ()
    without_staple = [exercise_id for exercise_id in ids if exercise_id != "0043"]
    assert unknown_reference_ids(without_staple, specs) == ("0043",)


@pytest.mark.parametrize(
    ("exercise_id", "pattern"),
    [
        ("0043", "squat"),
        ("0032", "hinge"),
        ("0025", "horizontal_push"),
        ("0027", "horizontal_pull"),
        ("0652", "vertical_pull"),
        ("0405", "vertical_push"),
        ("0336", "lunge"),
        ("0119", "shoulder_raise"),  # remo al mentón
        ("0010", "core_flexion"),  # «throw down» no es un remo
        ("0003", "core_rotation"),  # air bike = crunch bicicleta
        ("0669", "mobility"),  # estiramiento de deltoides posterior
        ("3645", "glute_isolation"),  # «outstretched» no es un estiramiento
        ("0859", "forearm"),  # wrist roller
        ("3168", "horizontal_pull"),  # remo en sentadilla
        ("0788", "vertical_push"),  # press tras nuca
        ("0648", "hinge"),  # power clean
        ("0786", "vertical_push"),  # squat jerk
        ("1385", "calf"),  # elevación de talones en prensa
        ("0216", "other"),
    ],
)
def test_pattern_examples(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs, exercise_id: str, pattern: str
) -> None:
    assert classify_pattern(normalized[exercise_id], specs)[0] == pattern


def test_role_mechanic_and_attributes(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs
) -> None:
    squat = enrich_exercise(normalized["0043"], specs)
    assert (squat.mechanic, squat.role, squat.is_staple) == ("compound", "main", True)
    assert enrich_exercise(normalized["1512"], specs).role == "mobility"
    assert enrich_exercise(normalized["1512"], specs).load_type == "time"
    assert enrich_exercise(normalized["2612"], specs).role == "cardio"
    assert enrich_exercise(normalized["0472"], specs).role == "core"
    assert enrich_exercise(normalized["3212"], specs).role == "warmup"
    assert enrich_exercise(normalized["0294"], specs).mechanic == "isolation"
    assert enrich_exercise(normalized["0294"], specs).role == "accessory"
    assert enrich_exercise(normalized["0073"], specs).mechanic == "isolation"  # pullover
    assert enrich_exercise(normalized["0585"], specs).difficulty == 1  # máquina
    assert enrich_exercise(normalized["0631"], specs).difficulty == 3  # muscle up
    assert enrich_exercise(normalized["0662"], specs).difficulty == 2
    assert enrich_exercise(normalized["0336"], specs).laterality == "unilateral"
    assert enrich_exercise(normalized["0025"], specs).laterality == "bilateral"
    assert enrich_exercise(normalized["0017"], specs).load_type == "assisted"
    assert enrich_exercise(normalized["0662"], specs).load_type == "bodyweight"
    assert enrich_exercise(normalized["0025"], specs).load_type == "external"
    assert enrich_exercise(normalized["2135"], specs).load_type == "time"  # plancha
    assert enrich_exercise(normalized["0472"], specs).load_type == "bodyweight"  # hanging
    assert enrich_exercise(normalized["1460"], specs).load_type == "bodyweight"  # walking lunge
    assert enrich_exercise(normalized["2133"], specs).load_type == "time"  # override


def test_rule_conditions_are_anded(normalized: dict[str, NormalizedExercise]) -> None:
    exercise = normalized["0025"]
    assert rule_matches(PatternRule(pattern="squat", name_any=(" bench",)), exercise)
    assert not rule_matches(
        PatternRule(pattern="squat", name_any=(" bench",), target=("quads",)), exercise
    )
    assert not rule_matches(
        PatternRule(pattern="squat", name_any=(" bench",), name_none=("press",)), exercise
    )
    assert rule_matches(
        PatternRule.model_validate({"pattern": "squat", "equipment": "barbell"}), exercise
    )
    assert not rule_matches(
        PatternRule.model_validate({"pattern": "squat", "body_part": "waist"}), exercise
    )


def test_unmatched_exercise_defaults_to_other(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs
) -> None:
    bare = replace(
        specs,
        rules=specs.rules.model_copy(update={"pattern_rules": ()}),
        overrides=EnrichmentOverrides(version=1),
    )
    assert classify_pattern(normalized["0025"], bare) == ("other", "default")


def test_by_id_override_prevails(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs
) -> None:
    overrides = specs.overrides.model_copy(
        update={
            "by_id": {
                "0025": ExerciseOverride(
                    mechanic="isolation",
                    role="warmup",
                    difficulty=3,
                    laterality="unilateral",
                    load_type="time",
                    is_staple=False,
                )
            }
        }
    )
    result = enrich_exercise(normalized["0025"], replace(specs, overrides=overrides))
    assert (result.mechanic, result.role, result.difficulty) == ("isolation", "warmup", 3)
    assert (result.laterality, result.load_type, result.is_staple) == ("unilateral", "time", False)


def test_inconsistent_staple_fails(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs
) -> None:
    wrong = replace(specs, staples=Staples(version=1, staples={"lunge": ("0043",)}))
    with pytest.raises(EnrichmentError, match="staple 0043"):
        enrich_all([normalized["0043"]], wrong)


def test_other_justified_must_really_be_other(
    normalized: dict[str, NormalizedExercise], specs: IngestSpecs
) -> None:
    overrides = specs.overrides.model_copy(update={"other_justified": {"0043": "no"}})
    with pytest.raises(EnrichmentError, match="other_justified"):
        enrich_all([normalized["0043"]], replace(specs, overrides=overrides))

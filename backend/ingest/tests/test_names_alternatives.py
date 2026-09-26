"""Nombres ES (§6.4) y alternativas precalculadas (§6.5)."""

from dataclasses import replace
from decimal import Decimal

import pytest

from ingest.alternatives import TOP_N, compute_alternatives, jaccard, score_pair
from ingest.catalog import Catalog
from ingest.names import (
    NamesError,
    fold,
    glossary_violations,
    required_terms,
    spanish_name,
    validate_names,
)
from ingest.normalize import normalize_all
from ingest.source import RawExercise
from ingest.specs import IngestSpecs, NamesExceptions


def test_spanish_names_cover_all_exercises_and_follow_glossary(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    report = validate_names(normalize_all(all_records, specs), specs)
    assert report.ok, report.summary()


def test_names_are_lowercase_and_without_variant_suffixes(specs: IngestSpecs) -> None:
    for exercise_id, name in specs.names_es.items():
        assert name, exercise_id
        assert name == name.strip(), exercise_id
        assert not name[0].isupper(), exercise_id
        for suffix in ("(male)", "(female)", "pov)", " v. "):
            assert suffix not in name, exercise_id


def test_variants_share_spanish_name(full_catalog: Catalog) -> None:
    names: dict[str, set[str]] = {}
    for entry in full_catalog.entries:
        names.setdefault(entry.exercise.variant_group, set()).add(entry.name_es)
    assert all(len(group) == 1 for group in names.values())


@pytest.mark.parametrize(
    ("english", "spanish", "missing"),
    [
        ("dumbbell bench press", "press de banca con mancuernas", ()),
        ("dumbbell bench press", "press de pecho con mancuerna", ("bench press",)),
        ("barbell incline bench press", "press de banca inclinada con barra", ()),
        ("lever lying leg curl", "curl femoral tumbado en máquina", ()),
        ("dumbbell reverse fly", "pájaros con mancuernas", ()),
        ("cable one arm curl", "curl en polea", ("one arm",)),
        ("split squats", "sentadilla búlgara", ()),
        ("push up on bosu ball", "flexión sobre bosu", ()),
    ],
)
def test_glossary_violations(
    specs: IngestSpecs, english: str, spanish: str, missing: tuple[str, ...]
) -> None:
    assert glossary_violations(english, spanish, specs.glossary) == missing


def test_longer_terms_consume_shorter_ones(specs: IngestSpecs) -> None:
    terms = [term.english for term in required_terms("dumbbell reverse fly", specs.glossary)]
    assert terms == ["reverse fly", "dumbbell"]


def test_fold_removes_accents() -> None:
    assert fold("Elevación de Talones ÑU") == "elevacion de talones nu"


def test_validate_names_reports_every_problem(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    exercises = normalize_all(fixture_records, specs)
    names = {exercise.id: specs.names_es[exercise.id] for exercise in exercises}
    names.pop("0001")
    names["0002"] = "Mayúscula inicial"
    names["0003"] = "crunch v. 2"
    names["0020"] = " "
    names["0025"] = "press con barra"
    names["0027"] = names["0032"]
    names["9999"] = "sobrante"
    broken = replace(specs, names_es=names, names_exceptions=NamesExceptions(version=1))
    report = validate_names(exercises, broken)
    assert not report.ok
    assert report.missing == ("0001",)
    assert report.unknown == ("9999",)
    assert set(report.invalid) == {"0002", "0003", "0020"}
    assert ("0027", "0032") in report.duplicates
    assert report.glossary_violations["0025"] == ("bench press",)
    summary = report.summary()
    for fragment in ("sin nombre ES", "ids inexistentes", "duplicado", "falta traducción"):
        assert fragment in summary


def test_mojibake_in_spanish_name_is_invalid(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    exercises = normalize_all(fixture_records, specs)
    names = {**specs.names_es, "0739": "prensa de piernas a 45в°"}
    report = validate_names(exercises, replace(specs, names_es=names))
    assert report.invalid["0739"] == "contiene mojibake"


def test_spanish_name_lookup(specs: IngestSpecs) -> None:
    assert spanish_name("0043", specs) == "sentadilla trasera con barra"
    with pytest.raises(NamesError, match="9999"):
        spanish_name("9999", specs)


# ------------------------------------------------------------------ alternativas
def test_jaccard() -> None:
    assert jaccard([], []) == 0
    assert jaccard(["a", "b"], ["b", "c"]) == Decimal(1) / Decimal(3)


def test_score_weights(full_catalog: Catalog) -> None:
    by_id = full_catalog.by_id()
    base, same = by_id["0043"], by_id["0042"]
    score = score_pair(base.exercise, base.enrichment, same.exercise, same.enrichment)
    expected = (
        Decimal("0.5")
        + Decimal("0.3")
        + Decimal("0.1") * jaccard(base.exercise.secondary_muscles, same.exercise.secondary_muscles)
        + Decimal("0.1")
    )
    assert score == expected.quantize(Decimal("0.001"))
    curl = by_id["0294"]
    assert score_pair(base.exercise, base.enrichment, curl.exercise, curl.enrichment) <= Decimal(
        "0.2"
    )


def test_alternatives_rules(full_catalog: Catalog) -> None:
    by_id = full_catalog.by_id()
    for exercise_id, alternatives in full_catalog.alternatives.items():
        entry = by_id[exercise_id]
        assert len(alternatives) <= TOP_N
        assert [alt.rank for alt in alternatives] == list(range(1, len(alternatives) + 1))
        scores = [alt.score for alt in alternatives]
        assert scores == sorted(scores, reverse=True)
        for alt in alternatives:
            other = by_id[alt.alt_id]
            assert alt.alt_id != exercise_id
            assert other.exercise.variant_group != entry.exercise.variant_group
            assert (other.enrichment.role == "mobility") == (entry.enrichment.role == "mobility")
            assert Decimal(0) < alt.score <= Decimal(1)
    assert all(full_catalog.alternatives.values())


def test_alternatives_are_deterministic(full_catalog: Catalog) -> None:
    exercises = [entry.exercise for entry in full_catalog.entries[:200]]
    enrichments = {entry.exercise.id: entry.enrichment for entry in full_catalog.entries[:200]}
    assert compute_alternatives(exercises, enrichments) == compute_alternatives(
        exercises, enrichments
    )

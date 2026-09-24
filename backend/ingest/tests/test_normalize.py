"""Normalización (§6.2): vocabulario 100 % mapeado, nombres, sufijos y variantes."""

from collections import Counter
from dataclasses import replace

import pytest

from ingest.normalize import (
    DisplayNameError,
    UnmappedValueError,
    fix_display_name,
    map_body_part,
    normalize_all,
    normalize_record,
    slugify,
    split_variant_suffixes,
    unmapped_values,
)
from ingest.source import RawExercise
from ingest.specs import IngestSpecs, NameFixes


def test_full_dataset_vocabulary_is_fully_mapped(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    assert unmapped_values(all_records, specs) == {}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target", "gluteus maximus", "target"),
        ("muscle_group", "pecs", "muscle_group"),
        ("equipment", "sandbag", "Equipamiento"),
        ("body_part", "tail", "Zona corporal"),
    ],
)
def test_unmapped_value_fails_ingest(
    fixture_records: tuple[RawExercise, ...],
    specs: IngestSpecs,
    field: str,
    value: str,
    message: str,
) -> None:
    broken = fixture_records[0].model_copy(update={field: value})
    assert unmapped_values([broken], specs)
    with pytest.raises(UnmappedValueError, match=message):
        normalize_record(broken, specs)


def test_unmapped_secondary_muscle_fails(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    broken = fixture_records[0].model_copy(update={"secondary_muscles": ("spleen",)})
    assert unmapped_values([broken], specs) == {"secondary_muscles": {"spleen"}}
    with pytest.raises(UnmappedValueError, match="secondary_muscles"):
        normalize_record(broken, specs)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("forward lunge (male)", ("forward lunge", "male", None, None)),
        ("barbell upright row v. 3", ("barbell upright row", None, 3, None)),
        ("swimmer kicks v. 2 (male)", ("swimmer kicks", "male", 2, None)),
        ("barbell full squat (back pov)", ("barbell full squat", None, None, "back")),
        ("twisted leg raise (female)", ("twisted leg raise", "female", None, None)),
        ("push-up", ("push-up", None, None, None)),
    ],
)
def test_split_variant_suffixes(
    name: str, expected: tuple[str, str | None, int | None, str | None]
) -> None:
    parsed = split_variant_suffixes(name)
    assert (parsed.base_name, parsed.demo_sex, parsed.version, parsed.camera) == expected


def test_display_name_fixes_typos_and_mojibake(specs: IngestSpecs) -> None:
    assert fix_display_name("0739", "sled 45в° leg press", specs) == "sled 45° leg press"
    assert fix_display_name("0079", "barbell revers wrist curl", specs) == (
        "barbell reverse wrist curl"
    )
    assert fix_display_name("2799", "barbell sitted alternate leg raise", specs) == (
        "barbell seated alternate leg raise"
    )
    assert fix_display_name("0096", "barbell side bent", specs) == "barbell side bend"
    assert fix_display_name("1759", "anything", specs) == "single leg squat (pistol) (male)"


def test_residual_mojibake_is_an_error(specs: IngestSpecs) -> None:
    no_fixes = replace(specs, name_fixes=NameFixes(version=1, replace_substrings={}))
    with pytest.raises(DisplayNameError, match="mojibake"):
        fix_display_name("0739", "sled 45в° leg press", no_fixes)


def test_no_display_name_keeps_mojibake(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    normalized = normalize_all(all_records, specs)
    assert not [e.id for e in normalized if "в" in e.display_name_en]
    originals = {e.id: e.name_en for e in normalized}
    assert sum("в" in name for name in originals.values()) == 4


def test_slugify() -> None:
    assert slugify("Sled 45° leg press") == "sled-45-leg-press"
    assert slugify("(((") == "exercise"


def test_map_body_part() -> None:
    assert map_body_part("upper arms", "0001") == "upper_arms"


def test_variant_counts_match_dataset_analysis(
    all_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    normalized = normalize_all(all_records, specs)
    raw_names = [e.name_en for e in normalized]
    assert sum(name.endswith(("(male)", "(female)")) for name in raw_names) == 33
    assert sum(" v. " in name for name in raw_names) == 40
    assert sum("pov)" in name for name in raw_names) == 5
    # 33 sufijos + «single leg squat (pistol) male» (corregido en name-fixes.yaml)
    assert sum(e.demo_sex is not None for e in normalized) == 34
    kinds = Counter(e.variant_kind for e in normalized)
    assert kinds["camera_angle"] == 5
    assert kinds["version"] == 40
    duplicated_names = [
        name for name, count in Counter(n.strip() for n in raw_names).items() if count > 1
    ]
    assert len(duplicated_names) == 6
    by_name = Counter(e.display_name_en for e in normalized if e.variant_kind == "duplicate")
    assert {"lever chest press", "barbell seated calf raise"} <= set(by_name)
    assert len({e.slug for e in normalized}) == len(normalized)


def test_fixture_variant_groups(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    by_id = {e.id: e for e in normalize_all(fixture_records, specs)}
    squat_group = {by_id[i].variant_group for i in ("0043", "1461", "1462")}
    assert squat_group == {"barbell-full-squat"}
    assert by_id["0043"].variant_kind is None
    assert {by_id["1461"].variant_label_es, by_id["1462"].variant_label_es} == {
        "vista trasera",
        "vista lateral",
    }
    assert by_id["0577"].variant_kind == "duplicate"
    assert by_id["0577"].variant_label_es == "(variante B)"
    assert by_id["0576"].variant_kind is None
    upright = {by_id[i].variant_label_es for i in ("0119", "0120", "0121")}
    assert upright == {None, "variante 2", "variante 3"}
    assert by_id["3470"].demo_sex == "male"
    assert by_id["3470"].variant_kind == "demonstrator"
    assert by_id["3470"].variant_label_es == "demostración masculina"
    assert by_id["3236"].demo_sex == "female"
    assert by_id["0739"].display_name_en == "sled 45° leg press"
    assert by_id["0043"].thumb_path.startswith("thumbs/0043-")
    assert by_id["0043"].gif_path.endswith(".gif")


def test_duplicate_slugs_are_rejected(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    clone = fixture_records[0].model_copy()
    with pytest.raises(DisplayNameError, match="slugs"):
        normalize_all([fixture_records[0], clone], specs)


def test_secondary_muscles_are_deduplicated_in_order(
    fixture_records: tuple[RawExercise, ...], specs: IngestSpecs
) -> None:
    record = fixture_records[0].model_copy(
        update={"secondary_muscles": ("traps", "trapezius", "abs", "core")}
    )
    assert normalize_record(record, specs).secondary_muscles == ("traps", "abs")

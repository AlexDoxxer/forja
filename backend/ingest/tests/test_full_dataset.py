"""Integración con el dataset completo @ DATASET_COMMIT (``slow``: descarga ~140 MB).

Verifica las cifras de ``docs/dataset-analysis.md``, los 2.648 medios (SHA-256 y 180x180),
que ``fixtures/dataset-index.json`` coincide con el dataset real y la carga completa en
PostgreSQL. ``DATASET_REPO`` permite apuntar a un espejo local (``file://…``).
"""

import json
import os
from collections import Counter
from pathlib import Path

import pytest

from ingest.catalog import build_catalog
from ingest.load import load_catalog
from ingest.media import SOURCE_DIR, fetch, read_manifest, verify_media
from ingest.report import quality_problems
from ingest.source import DATA_FILE, load_dataset
from ingest.specs import IngestSpecs
from ingest.tests.conftest import DATASET_COMMIT, FIXTURES

pytestmark = [pytest.mark.slow, pytest.mark.integration]

DEFAULT_REPO = "https://github.com/hasaneyldrm/exercises-dataset"
BODY_PARTS = {
    "upper arms": 292, "upper legs": 227, "back": 203, "waist": 169, "chest": 163,
    "shoulders": 143, "lower legs": 59, "lower arms": 37, "cardio": 29, "neck": 2,
}  # fmt: skip
EQUIPMENT = {
    "body weight": 325, "dumbbell": 294, "cable": 157, "barbell": 154, "leverage machine": 81,
    "band": 54, "smith machine": 48, "kettlebell": 41, "weighted": 36, "stability ball": 28,
    "ez barbell": 23, "assisted": 15, "sled machine": 15, "medicine ball": 13, "rope": 10,
    "roller": 8, "resistance band": 7, "bosu ball": 3, "olympic barbell": 2, "wheel roller": 2,
    "upper body ergometer": 1, "skierg machine": 1, "hammer": 1, "stationary bike": 1,
    "tire": 1, "trap bar": 1, "elliptical machine": 1, "stepmill machine": 1,
}  # fmt: skip
TARGETS = {
    "abs": 169, "pectorals": 158, "biceps": 151, "glutes": 144, "delts": 143, "triceps": 141,
    "upper back": 88, "lats": 81, "calves": 59, "quads": 44, "forearms": 37,
    "cardiovascular system": 29, "hamstrings": 28, "spine": 19, "traps": 15, "adductors": 6,
    "serratus anterior": 5, "abductors": 5, "levator scapulae": 2,
}  # fmt: skip
STEPS_ES = {4: 82, 5: 503, 6: 426, 7: 221, 8: 72, 9: 15, 10: 2, 11: 3}


@pytest.fixture(scope="module")
def media_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("full-media")
    repo = os.environ.get("DATASET_REPO", DEFAULT_REPO)
    result = fetch(repo, DATASET_COMMIT, root)
    assert result.status == "updated"
    return root


def test_dataset_figures_match_analysis(media_root: Path) -> None:
    records = load_dataset(media_root / SOURCE_DIR)
    assert len(records) == 1324
    assert Counter(r.body_part for r in records) == BODY_PARTS
    assert all(r.category == r.body_part for r in records)
    assert Counter(r.equipment for r in records) == EQUIPMENT
    assert Counter(r.target for r in records) == TARGETS
    assert len({r.muscle_group for r in records}) == 29
    assert len({m for r in records for m in r.secondary_muscles}) == 40
    assert Counter(len(r.instruction_steps["es"]) for r in records) == STEPS_ES
    names = [r.name for r in records]
    assert sum(n.endswith(("(male)", "(female)")) for n in names) == 33
    assert sum(" v. " in n for n in names) == 40
    assert sum("pov)" in n for n in names) == 5
    assert sum("в°" in n for n in names) == 4
    assert sum("stretch" in n for n in names) == 57
    assert len([n for n, c in Counter(names).items() if c > 1]) == 6


def test_all_media_verified(media_root: Path) -> None:
    manifest = read_manifest(media_root)
    assert manifest is not None
    assert manifest.commit == DATASET_COMMIT
    assert Counter(item.kind for item in manifest.files) == {"thumb": 1324, "gif": 1324}
    result = verify_media(media_root, manifest)
    assert result.ok, result.errors[:5]
    assert result.verified == 2648
    assert fetch("file:///unused", DATASET_COMMIT, media_root).status == "unchanged"


def test_fixtures_match_real_dataset(media_root: Path) -> None:
    real = json.loads((media_root / SOURCE_DIR / DATA_FILE).read_text("utf-8"))
    index = json.loads((FIXTURES / "dataset-index.json").read_text("utf-8"))
    by_id = {item["id"]: item for item in real}
    assert len(index) == len(real)
    for item in index:
        assert {key: by_id[item["id"]][key] for key in item} == item
    for item in json.loads((FIXTURES / "exercises.json").read_text("utf-8")):
        assert by_id[item["id"]] == item


async def test_full_catalog_loads(media_root: Path, specs: IngestSpecs, postgres_url: str) -> None:
    catalog = build_catalog(load_dataset(media_root / SOURCE_DIR), specs)
    assert quality_problems(catalog, specs) == []
    manifest = read_manifest(media_root)
    assert manifest is not None
    result = await load_catalog(
        postgres_url, catalog, manifest, specs, media_verified=2648, create_schema=True
    )
    assert result.counts["exercises_total"] == 1324
    assert result.counts["media_verified"] == 2648

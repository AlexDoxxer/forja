"""`specs/nutrition.yaml` es la fuente; la copia empaquetada debe ser idéntica (ADR 0011)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_packaged_nutrition_tables_match_spec() -> None:
    spec = ROOT / "specs" / "nutrition.yaml"
    packaged = ROOT / "nutrition" / "forja_nutrition" / "data" / "nutrition.yaml"
    assert spec.read_bytes() == packaged.read_bytes(), (
        "copia empaquetada desincronizada: cp specs/nutrition.yaml "
        "nutrition/forja_nutrition/data/nutrition.yaml"
    )

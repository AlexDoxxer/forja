"""Construye ``catalog.json`` (fixture congelada de ``ExerciseCard``) desde el dataset real.

Mientras ``forja-ingest export-cards`` (tarea F1-ING-12) no exista, este script aplica una
versión simplificada y determinista del enriquecimiento de MASTER_PROMPT §6.2 y §6.3 sobre los
1.324 registros de ``hasaneyldrm/exercises-dataset`` en el commit fijado, usando las tablas
reales de ``specs/`` (normalización, reglas de patrón, overrides y staples). ``name_es`` toma
provisionalmente ``display_name_en``: los nombres en español llegan con la ingesta.

Uso (desde ``engine/``)::

    uv run python -m tests.fixtures.build_catalog                  # descarga el commit fijado
    uv run python -m tests.fixtures.build_catalog --source ruta/exercises.json

Cuando exista la ingesta, la fixture se regenera con::

    uv run --project backend forja-ingest export-cards --output engine/tests/fixtures/catalog.json
"""

import argparse
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from forja_engine.models import ExerciseCard

DATASET_COMMIT = "7455efae41b330c265e7cd4b78dfa848e7ce5ebd"
DATASET_URL = (
    "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/"
    f"{DATASET_COMMIT}/data/exercises.json"
)
ROOT = Path(__file__).resolve().parents[3]
SPECS = ROOT / "specs"
OUTPUT = Path(__file__).resolve().parent / "catalog.json"

CORE_PATTERNS = {"core_flexion", "core_anti_extension", "core_rotation", "core_lateral"}
VARIANT_SUFFIX = re.compile(r"\s*(v\. \d+|\((back|side) pov\))\s*")
DEMO_SUFFIX = re.compile(r"\s*\((male|female)\)\s*$")


def _yaml(name: str) -> Any:
    with (SPECS / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _rule_matches(rule: dict[str, Any], record: dict[str, Any], name: str) -> bool:
    if "name_any" in rule and not any(token in name for token in rule["name_any"]):
        return False
    if "target" in rule and record["target"] not in rule["target"]:
        return False
    return not ("body_part" in rule and record["body_part"] != rule["body_part"])


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _role(
    name: str, pattern: str, record: dict[str, Any], *, compound: bool, is_staple: bool
) -> str:
    if "stretch" in name or pattern == "mobility":
        return "mobility"
    if record["body_part"] == "cardio":
        return "cardio"
    if pattern in CORE_PATTERNS:
        return "core"
    return "main" if compound and is_staple else "accessory"


def _difficulty(name: str, rules: dict[str, Any]) -> int:
    if any(t in name for t in rules["level_3_any"]):
        return 3
    if any(t in name for t in rules["level_1_any"]):
        return 1
    return int(rules["default"])


def _load_type(name: str, record: dict[str, Any], rules: dict[str, Any]) -> str:
    if any(t in name for t in rules["time_any"]) or record["body_part"] == "cardio":
        return "time"
    if any(t in name for t in rules["assisted_any"]):
        return "assisted"
    return "bodyweight" if record["equipment"] == "body weight" else "external"


def build_cards(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enriquecimiento determinista simplificado de cada registro del dataset."""
    rules = _yaml("enrichment-rules.yaml")
    overrides = _yaml("overrides/enrichment-overrides.yaml")["by_id"]
    fixes = _yaml("overrides/name-fixes.yaml")["replace_substrings"]
    staples = _yaml("overrides/staples.yaml")["staples"]
    muscles = _yaml("muscle-normalization.yaml")["map"]
    equipment = _yaml("equipment-normalization.yaml")["map"]
    staple_pattern = {ex_id: pattern for pattern, ids in staples.items() for ex_id in ids}

    cards: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda r: str(r["id"])):
        name = str(record["name"]).lower()
        pattern = next(
            (r["pattern"] for r in rules["pattern_rules"] if _rule_matches(r, record, name)),
            "other",
        )
        is_staple = record["id"] in staple_pattern
        if is_staple:
            pattern = staple_pattern[record["id"]]
        isolation_hint = any(h in name for h in rules["isolation_name_hints"])
        compound = pattern in rules["compound_patterns"] and not isolation_hint
        mechanic = "compound" if compound else "isolation"
        role = _role(name, pattern, record, compound=compound, is_staple=is_staple)
        difficulty = _difficulty(name, rules["difficulty"])
        unilateral = any(t in name for t in rules["laterality_unilateral_any"])
        load_type = _load_type(name, record, rules["load_type"])
        card: dict[str, Any] = {
            "movement_pattern": pattern,
            "mechanic": mechanic,
            "role": role,
            "difficulty": difficulty,
            "is_staple": is_staple,
            "laterality": "unilateral" if unilateral else "bilateral",
            "load_type": load_type,
        }
        card.update(overrides.get(record["id"], {}))
        demo = DEMO_SUFFIX.search(str(record["name"]))
        display = DEMO_SUFFIX.sub("", str(record["name"])).strip()
        for wrong, right in fixes.items():
            display = display.replace(wrong, right)
        secondaries: list[str] = []
        for raw in record["secondary_muscles"]:
            code = muscles[raw]
            if code not in secondaries:
                secondaries.append(code)
        entry = equipment[record["equipment"]]
        cards.append(
            {
                "id": record["id"],
                "name_es": display,
                "display_name_en": display,
                "variant_group": _slug(VARIANT_SUFFIX.sub(" ", display)),
                "body_part": str(record["body_part"]).replace(" ", "_"),
                "equipment_code": entry["code"],
                "equipment_group": entry["group"],
                "target_muscle": muscles[record["target"]],
                "primary_group_muscle": muscles[record["muscle_group"]],
                "secondary_muscles": secondaries,
                **card,
                "demo_sex": demo.group(1) if demo else None,
                "deprecated": False,
            }
        )
    for raw_card in cards:
        ExerciseCard.model_validate(raw_card)
    return cards


def write_catalog(cards: list[dict[str, Any]], output: Path) -> None:
    """Una tarjeta por línea (JSON compacto) para diffs legibles."""
    lines = [json.dumps(card, ensure_ascii=False, separators=(",", ":")) for card in cards]
    output.write_text("[\n" + ",\n".join(lines) + "\n]\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="exercises.json local (si no, se descarga)")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    if args.source is not None:
        raw = args.source.read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(DATASET_URL, timeout=60) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    write_catalog(build_cards(json.loads(raw)), args.output)


if __name__ == "__main__":
    main()

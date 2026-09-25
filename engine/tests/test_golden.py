"""§7.8: 12 snapshots golden de perfiles representativos (revisión del experto, F1b-EXP-05).

Regenerar tras un cambio intencionado de salida (con subida de ``ENGINE_VERSION``)::

    FORJA_UPDATE_GOLDEN=1 uv run pytest tests/test_golden.py
"""

import json
import os
from pathlib import Path

import pytest

from forja_engine import generate
from tests.golden_profiles import PROFILES, render_markdown
from tests.helpers import assert_plan_invariants, catalog

GOLDEN = Path(__file__).resolve().parent / "golden"
UPDATE = os.environ.get("FORJA_UPDATE_GOLDEN") == "1"


def _serialize(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def test_there_are_twelve_profiles() -> None:
    assert len(PROFILES) == 12


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_golden_snapshot(name: str) -> None:
    description, inp = PROFILES[name]
    plan = generate(inp, catalog())
    assert_plan_invariants(plan)
    rendered_json = _serialize(plan.model_dump(mode="json"))
    rendered_md = render_markdown(name, description, plan)
    json_path = GOLDEN / f"{name}.json"
    md_path = GOLDEN / f"{name}.md"
    if UPDATE:
        GOLDEN.mkdir(exist_ok=True)
        json_path.write_text(rendered_json, encoding="utf-8")
        md_path.write_text(rendered_md, encoding="utf-8")
    assert json_path.read_text(encoding="utf-8") == rendered_json
    assert md_path.read_text(encoding="utf-8") == rendered_md

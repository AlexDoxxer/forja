"""Umbral de cobertura separado para líneas y ramas (MASTER_PROMPT §2.2).

coverage.py solo admite un umbral combinado (``fail_under``); este script lee el
``coverage.json`` generado por pytest-cov y exige por separado el porcentaje de líneas y el
de ramas. Uso::

    python scripts/coverage_gate.py <coverage.json> --lines 100 --branches 95
"""

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict


class Totals(TypedDict):
    covered_lines: int
    num_statements: int
    covered_branches: int
    num_branches: int


def percent(covered: int, total: int) -> float:
    """Porcentaje cubierto; un total de cero elementos cuenta como cobertura completa."""
    return 100.0 if total == 0 else 100.0 * covered / total


def evaluate(totals: Totals, min_lines: float, min_branches: float) -> list[str]:
    """Devuelve la lista de incumplimientos (vacía si se alcanzan ambos umbrales)."""
    lines = percent(totals["covered_lines"], totals["num_statements"])
    branches = percent(totals["covered_branches"], totals["num_branches"])
    failures: list[str] = []
    if lines < min_lines:
        failures.append(f"líneas {lines:.2f} % < {min_lines:.2f} %")
    if branches < min_branches:
        failures.append(f"ramas {branches:.2f} % < {min_branches:.2f} %")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="ruta a coverage.json")
    parser.add_argument("--lines", type=float, required=True, help="mínimo de líneas (%)")
    parser.add_argument("--branches", type=float, required=True, help="mínimo de ramas (%)")
    args = parser.parse_args(argv)

    data = json.loads(args.report.read_text(encoding="utf-8"))
    totals: Totals = data["totals"]
    failures = evaluate(totals, args.lines, args.branches)
    lines = percent(totals["covered_lines"], totals["num_statements"])
    branches = percent(totals["covered_branches"], totals["num_branches"])
    status = "FALLA" if failures else "OK"
    sys.stdout.write(
        f"[coverage-gate] {args.report}: líneas {lines:.2f} % (mín. {args.lines:.0f} %), "
        f"ramas {branches:.2f} % (mín. {args.branches:.0f} %) -> {status}\n"
    )
    for failure in failures:
        sys.stderr.write(f"[coverage-gate] {failure}\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

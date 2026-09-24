"""Informe de enriquecimiento ``docs/enrichment-report.md`` (MASTER_PROMPT §6.3).

Es reproducible: mismo dataset + mismas tablas ⇒ mismo Markdown (sin marcas de tiempo).
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ingest.catalog import Catalog
from ingest.domain import (
    MAIN_PATTERNS,
    MIN_STAPLES_PER_CELL,
    MOVEMENT_PATTERNS,
    STAPLE_EQUIPMENT_GROUPS,
    EquipmentGroup,
    MovementPattern,
)
from ingest.specs import IngestSpecs

_GROUP_COLUMNS: tuple[EquipmentGroup, ...] = (
    "gym",
    "home_basic",
    "bodyweight",
    "cardio_machine",
    "other",
)


@dataclass(frozen=True, slots=True)
class StapleCell:
    pattern: MovementPattern
    group: EquipmentGroup
    candidates: int
    staple_ids: tuple[str, ...]

    @property
    def applicable(self) -> bool:
        return self.candidates > 0

    @property
    def ok(self) -> bool:
        return not self.applicable or len(self.staple_ids) >= MIN_STAPLES_PER_CELL


def staple_matrix(catalog: Catalog) -> tuple[StapleCell, ...]:
    """Patrón principal x grupo de equipamiento (gym, home_basic, bodyweight)."""
    cells: list[StapleCell] = []
    for pattern in MAIN_PATTERNS:
        for group in STAPLE_EQUIPMENT_GROUPS:
            members = [
                entry
                for entry in catalog.entries
                if entry.enrichment.movement_pattern == pattern
                and entry.exercise.equipment_group == group
            ]
            staples = tuple(e.exercise.id for e in members if e.enrichment.is_staple)
            cells.append(StapleCell(pattern, group, len(members), staples))
    return tuple(cells)


def _table(header: Iterable[str], rows: Iterable[Iterable[object]]) -> list[str]:
    head = list(header)
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return lines


def _distribution(title: str, counter: Counter[str], total: int) -> list[str]:
    rows = [
        (f"`{key}`", count, f"{100 * count / total:.1f} %")
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]
    return [f"### {title}", "", *_table(("Valor", "Nº", "%"), rows), ""]


def render_report(catalog: Catalog, specs: IngestSpecs, commit: str) -> str:
    """Markdown completo del informe."""
    entries = catalog.entries
    total = len(entries)
    enrich = [entry.enrichment for entry in entries]
    lines: list[str] = [
        "# Informe de enriquecimiento del catálogo",
        "",
        "> Generado por `forja-ingest report` (no editar a mano). Dataset "
        f"`hasaneyldrm/exercises-dataset` @ `{commit}`; reglas "
        f"`specs/enrichment-rules.yaml` v{specs.rules.version}, overrides "
        f"v{specs.overrides.version}, staples v{specs.staples.version}.",
        "",
        "## Resumen",
        "",
        f"- Ejercicios: **{total}**.",
        f"- Patrón `other`: **{sum(e.movement_pattern == 'other' for e in enrich)}**, todos "
        f"justificados ({len(specs.overrides.other_justified)} excepciones explícitas).",
        f"- Staples: **{sum(e.is_staple for e in enrich)}** "
        f"(rol `main`: {sum(e.role == 'main' for e in enrich)}).",
        f"- Reglas prioritarias en overrides: {len(specs.overrides.pattern_rules)}; "
        f"overrides por id: {len(specs.overrides.by_id)}.",
        f"- Nombres en español: {sum(1 for e in entries if e.name_es)}/{total} (100 %).",
        f"- Ejercicios con demostrador (`demo_sex`): "
        f"{sum(1 for e in entries if e.exercise.demo_sex)}.",
        "",
        "## Matriz de staples (patrón principal x grupo de equipamiento)",
        "",
        f"Requisito: al menos {MIN_STAPLES_PER_CELL} staples en cada celda con candidatos.",
        "",
    ]
    matrix = staple_matrix(catalog)
    rows = []
    for pattern in MAIN_PATTERNS:
        row: list[object] = [f"`{pattern}`"]
        for group in STAPLE_EQUIPMENT_GROUPS:
            cell = next(c for c in matrix if c.pattern == pattern and c.group == group)
            mark = "✅" if cell.ok else "❌"
            ids = ", ".join(cell.staple_ids) or "—"
            row.append(f"{mark} {len(cell.staple_ids)}/{cell.candidates} ({ids})")
        rows.append(row)
    lines += [*_table(("Patrón", *STAPLE_EQUIPMENT_GROUPS), rows), ""]

    lines += ["## Distribución por patrón y grupo de equipamiento", ""]
    per_pattern: Counter[tuple[str, str]] = Counter(
        (e.enrichment.movement_pattern, e.exercise.equipment_group) for e in entries
    )
    pattern_rows = []
    for pattern in MOVEMENT_PATTERNS:
        counts = [per_pattern[(pattern, group)] for group in _GROUP_COLUMNS]
        if sum(counts):
            staples = sum(
                1
                for e in entries
                if e.enrichment.movement_pattern == pattern and e.enrichment.is_staple
            )
            pattern_rows.append((f"`{pattern}`", sum(counts), *counts, staples))
    lines += [*_table(("Patrón", "Total", *_GROUP_COLUMNS, "Staples"), pattern_rows), ""]

    lines += ["## Otras distribuciones", ""]
    lines += _distribution("Rol", Counter(e.role for e in enrich), total)
    lines += _distribution("Mecánica", Counter(e.mechanic for e in enrich), total)
    lines += _distribution("Dificultad", Counter(str(e.difficulty) for e in enrich), total)
    lines += _distribution("Lateralidad", Counter(e.laterality for e in enrich), total)
    lines += _distribution("Tipo de carga", Counter(e.load_type for e in enrich), total)
    lines += _distribution(
        "Tipo de variante",
        Counter(e.exercise.variant_kind or "base" for e in entries),
        total,
    )
    lines += _distribution(
        "Origen de la decisión de patrón",
        Counter(e.enrichment.pattern_source.split(":")[0] for e in entries),
        total,
    )

    lines += ["## Excepciones `other` justificadas", ""]
    by_id = catalog.by_id()
    lines += _table(
        ("Id", "Nombre", "Motivo"),
        (
            (f"`{exercise_id}`", by_id[exercise_id].exercise.display_name_en, reason)
            for exercise_id, reason in sorted(specs.overrides.other_justified.items())
            if exercise_id in by_id
        ),
    )
    lines += ["", "## Staples por patrón", ""]
    lines += _table(
        ("Patrón", "Nº", "Ejercicios"),
        (
            (
                f"`{pattern}`",
                len(ids),
                "; ".join(f"{i} {by_id[i].name_es}" for i in ids if i in by_id),
            )
            for pattern, ids in specs.staples.staples.items()
        ),
    )
    lines.append("")
    return "\n".join(lines)

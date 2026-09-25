"""Catálogo enriquecido: normalización + enriquecimiento + nombres ES + alternativas.

Es la única vía para construir el catálogo que consumen ``load``, ``report`` y
``export-cards``; cualquier incoherencia aborta la ingesta.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ingest.alternatives import Alternative, compute_alternatives
from ingest.domain import (
    BodyPart,
    DemoSex,
    EquipmentCode,
    EquipmentGroup,
    ExerciseRole,
    Laterality,
    LoadType,
    Mechanic,
    MovementPattern,
    MuscleCode,
)
from ingest.enrich import Enrichment, EnrichmentError, enrich_all, unknown_reference_ids
from ingest.names import NamesError, validate_names
from ingest.normalize import NormalizedExercise, normalize_all
from ingest.source import RawExercise
from ingest.specs import IngestSpecs


class ExerciseCard(BaseModel):
    """DTO ``ExerciseCard`` de ``contracts/domain.md`` §5.1 (forma JSON del contrato)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[0-9]{4}$")
    name_es: str
    display_name_en: str
    variant_group: str
    body_part: BodyPart
    equipment_code: EquipmentCode
    equipment_group: EquipmentGroup
    target_muscle: MuscleCode
    primary_group_muscle: MuscleCode
    secondary_muscles: tuple[MuscleCode, ...]
    movement_pattern: MovementPattern
    mechanic: Mechanic
    role: ExerciseRole
    difficulty: int = Field(ge=1, le=3)
    is_staple: bool
    laterality: Laterality
    load_type: LoadType
    demo_sex: DemoSex | None
    deprecated: bool


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    exercise: NormalizedExercise
    enrichment: Enrichment
    name_es: str

    def card(self, *, deprecated: bool = False) -> ExerciseCard:
        exercise, enrichment = self.exercise, self.enrichment
        return ExerciseCard(
            id=exercise.id,
            name_es=self.name_es,
            display_name_en=exercise.display_name_en,
            variant_group=exercise.variant_group,
            body_part=exercise.body_part,
            equipment_code=exercise.equipment_code,
            equipment_group=exercise.equipment_group,
            target_muscle=exercise.target_muscle,
            primary_group_muscle=exercise.primary_group_muscle,
            secondary_muscles=exercise.secondary_muscles,
            movement_pattern=enrichment.movement_pattern,
            mechanic=enrichment.mechanic,
            role=enrichment.role,
            difficulty=enrichment.difficulty,
            is_staple=enrichment.is_staple,
            laterality=enrichment.laterality,
            load_type=enrichment.load_type,
            demo_sex=exercise.demo_sex,
            deprecated=deprecated,
        )


@dataclass(frozen=True, slots=True)
class Catalog:
    entries: tuple[CatalogEntry, ...]
    alternatives: dict[str, tuple[Alternative, ...]]

    def cards(self) -> tuple[ExerciseCard, ...]:
        return tuple(entry.card() for entry in self.entries)

    def by_id(self) -> dict[str, CatalogEntry]:
        return {entry.exercise.id: entry for entry in self.entries}


def build_catalog(
    records: Sequence[RawExercise], specs: IngestSpecs, *, full_dataset: bool = True
) -> Catalog:
    """Construye y valida el catálogo.

    Con ``full_dataset`` exige además que los overrides, staples y ``names_es.json`` no
    citen ids inexistentes (con un subconjunto, como la fixture, solo se validan sus ids).
    """
    exercises = normalize_all(records, specs)
    enrichments = enrich_all(exercises, specs)
    report = validate_names(exercises, specs)
    if not full_dataset:
        # Con un subconjunto es normal que names_es.json tenga ids de más.
        report = replace(report, unknown=())
    if not report.ok:
        raise NamesError(report.summary())
    if full_dataset:
        unknown = unknown_reference_ids((exercise.id for exercise in exercises), specs)
        if unknown:
            msg = f"specs/overrides cita ids inexistentes: {', '.join(unknown)}"
            raise EnrichmentError(msg)
    entries = tuple(
        CatalogEntry(exercise, enrichments[exercise.id], specs.names_es[exercise.id])
        for exercise in exercises
    )
    return Catalog(entries, compute_alternatives(exercises, enrichments))


def write_cards(cards: Sequence[ExerciseCard], path: Path) -> None:
    """Escribe el catálogo como lista JSON de ``ExerciseCard`` ordenada por id."""
    payload = [card.model_dump(mode="json") for card in sorted(cards, key=lambda card: card.id)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

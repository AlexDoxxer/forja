"""Alternativas precalculadas (MASTER_PROMPT §6.5).

Puntuación = 0,5·[mismo patrón] + 0,3·[mismo músculo objetivo] + 0,1·Jaccard(secundarios)
+ 0,1·[|Δ dificultad| ≤ 1]. Se excluyen el propio ejercicio y su ``variant_group``; los
estiramientos (rol ``mobility``) solo alternan entre sí. Desempate por id ascendente.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from ingest.enrich import Enrichment
from ingest.normalize import NormalizedExercise

TOP_N: Final = 8
WEIGHT_PATTERN: Final = Decimal("0.5")
WEIGHT_TARGET: Final = Decimal("0.3")
WEIGHT_SECONDARY: Final = Decimal("0.1")
WEIGHT_DIFFICULTY: Final = Decimal("0.1")
_QUANTUM: Final = Decimal("0.001")


@dataclass(frozen=True, slots=True)
class Alternative:
    exercise_id: str
    alt_id: str
    score: Decimal
    rank: int


def jaccard(first: Sequence[str], second: Sequence[str]) -> Decimal:
    """Índice de Jaccard; dos conjuntos vacíos no comparten nada (0)."""
    left, right = set(first), set(second)
    union = left | right
    if not union:
        return Decimal(0)
    return Decimal(len(left & right)) / Decimal(len(union))


def score_pair(
    base: NormalizedExercise,
    base_enrichment: Enrichment,
    candidate: NormalizedExercise,
    candidate_enrichment: Enrichment,
) -> Decimal:
    """Puntuación §6.5 (redondeada a 3 decimales, como ``numeric(4,3)``)."""
    score = Decimal(0)
    if base_enrichment.movement_pattern == candidate_enrichment.movement_pattern:
        score += WEIGHT_PATTERN
    if base.target_muscle == candidate.target_muscle:
        score += WEIGHT_TARGET
    score += WEIGHT_SECONDARY * jaccard(base.secondary_muscles, candidate.secondary_muscles)
    if abs(base_enrichment.difficulty - candidate_enrichment.difficulty) <= 1:
        score += WEIGHT_DIFFICULTY
    return score.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def _compatible(first: Enrichment, second: Enrichment) -> bool:
    return (first.role == "mobility") == (second.role == "mobility")


def compute_alternatives(
    exercises: Sequence[NormalizedExercise], enrichments: dict[str, Enrichment]
) -> dict[str, tuple[Alternative, ...]]:
    """Top 8 alternativas por ejercicio (solo puntuaciones > 0 por patrón o músculo)."""
    result: dict[str, tuple[Alternative, ...]] = {}
    for base in exercises:
        base_enrichment = enrichments[base.id]
        scored: list[tuple[Decimal, str]] = []
        for candidate in exercises:
            if candidate.variant_group == base.variant_group:
                continue
            candidate_enrichment = enrichments[candidate.id]
            if not _compatible(base_enrichment, candidate_enrichment):
                continue
            if (
                base_enrichment.movement_pattern != candidate_enrichment.movement_pattern
                and base.target_muscle != candidate.target_muscle
            ):
                continue
            scored.append(
                (score_pair(base, base_enrichment, candidate, candidate_enrichment), candidate.id)
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        result[base.id] = tuple(
            Alternative(base.id, alt_id, score, rank)
            for rank, (score, alt_id) in enumerate(scored[:TOP_N], start=1)
        )
    return result

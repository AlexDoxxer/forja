"""Derivación determinista de semilla a partir de la entrada normalizada (§8.3, §8.6)."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forja_nutrition.models import NutritionInput

_SEED_MODULUS = 2**53


def derive_seed(nutrition_input: NutritionInput) -> int:
    """SHA-256 del JSON canónico de la entrada (sin `seed`), reducido al rango de `Seed`."""
    payload = nutrition_input.model_dump(mode="json", exclude={"seed"})
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return int(digest, 16) % _SEED_MODULUS


def effective_seed(nutrition_input: NutritionInput) -> int:
    if nutrition_input.seed is not None:
        return nutrition_input.seed
    return derive_seed(nutrition_input)

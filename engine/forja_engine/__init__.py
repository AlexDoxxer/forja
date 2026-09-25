"""Motor de rutinas de Forja (paquete puro, determinista y sin E/S).

API pública (``contracts/domain.md`` §5.5): ``generate``, ``regenerate_day``,
``swap_exercise``, ``rebalance_after_edit``, ``validate_plan``, ``load_tables`` y el módulo
``forja_engine.progression``.
"""

from typing import Final

from forja_engine.generator import generate
from forja_engine.ops import (
    PlanOperationError,
    rebalance_after_edit,
    regenerate_day,
    swap_exercise,
    validate_plan,
)
from forja_engine.tables import Tables, TablesError, default_tables, load_tables
from forja_engine.version import ENGINE_VERSION

__version__: Final[str] = ENGINE_VERSION

__all__ = [
    "ENGINE_VERSION",
    "PlanOperationError",
    "Tables",
    "TablesError",
    "__version__",
    "default_tables",
    "generate",
    "load_tables",
    "rebalance_after_edit",
    "regenerate_day",
    "swap_exercise",
    "validate_plan",
]

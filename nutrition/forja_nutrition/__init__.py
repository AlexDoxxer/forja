"""Motor de nutrición de Forja (opcional, puro y determinista).

La versión del motor (semver) se guarda en cada plan de comidas como
``nutrition_version``; cualquier cambio que altere la salida para una misma entrada y
semilla DEBE incrementar ``NUTRITION_VERSION``.

API pública (`contracts/domain.md` §6.3): :func:`calculate_target`, :func:`plan_week`,
:func:`swap_food`, :func:`shopping_list`, :func:`load_foods`.
"""

from typing import Final

NUTRITION_VERSION: Final[str] = "0.1.1"
__version__: Final[str] = NUTRITION_VERSION

# Los submódulos se importan después de fijar __version__: planner.py lo usa como
# `nutrition_version` de cada MealPlan (import circular intencional y válido en Python, ya
# que __version__ ya existe en el módulo cuando se evalúan esos imports).
from forja_nutrition.energy import calculate_target  # noqa: E402
from forja_nutrition.foods import load_foods  # noqa: E402
from forja_nutrition.planner import plan_week  # noqa: E402
from forja_nutrition.shopping import shopping_list  # noqa: E402
from forja_nutrition.swap import swap_food  # noqa: E402

__all__ = [
    "NUTRITION_VERSION",
    "__version__",
    "calculate_target",
    "load_foods",
    "plan_week",
    "shopping_list",
    "swap_food",
]

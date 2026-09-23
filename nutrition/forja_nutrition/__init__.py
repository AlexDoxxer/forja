"""Motor de nutrición de Forja (opcional, puro y determinista).

La versión del motor (semver) se guarda en cada plan de comidas como
``nutrition_version``; cualquier cambio que altere la salida para una misma entrada y
semilla DEBE incrementar ``NUTRITION_VERSION``.
"""

from typing import Final

NUTRITION_VERSION: Final[str] = "0.1.0"
__version__: Final[str] = NUTRITION_VERSION

__all__ = ["NUTRITION_VERSION", "__version__"]

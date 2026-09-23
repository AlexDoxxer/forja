"""Motor de rutinas de Forja (paquete puro, determinista y sin E/S).

La versión del motor (semver) se persiste en cada programa generado como
``generator_version``; cualquier cambio que altere la salida para una misma entrada y
semilla DEBE incrementar ``ENGINE_VERSION``.
"""

from typing import Final

ENGINE_VERSION: Final[str] = "0.1.0"
__version__: Final[str] = ENGINE_VERSION

__all__ = ["ENGINE_VERSION", "__version__"]

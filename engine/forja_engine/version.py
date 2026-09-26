"""Versión semver del motor, persistida en cada programa como ``generator_version``.

Cualquier cambio que altere la salida para una misma entrada y semilla DEBE incrementarla
(ADR 0005) y regenerar los snapshots golden.
"""

from typing import Final

ENGINE_VERSION: Final[str] = "0.2.0"

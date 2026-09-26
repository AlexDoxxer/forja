"""Limitación de tasa en memoria por proceso (ventana deslizante)."""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Final

from app.core.errors import ProblemError

DEFAULT_LIMITS: Final[dict[str, tuple[int, int]]] = {
    # bucket: (peticiones, ventana en segundos)
    "login": (10, 60),
    "register": (5, 60),
    "password": (5, 60),
    "delete_account": (5, 60),
    "generator": (30, 60),
}


class RateLimiter:
    """Cuenta peticiones por (bucket, clave). ``scale`` multiplica los límites (tests)."""

    def __init__(
        self,
        limits: dict[str, tuple[int, int]] | None = None,
        *,
        scale: int = 1,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limits = dict(limits or DEFAULT_LIMITS)
        self._scale = scale
        self._clock = clock
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, bucket: str, key: str) -> None:
        """Registra una petición; lanza 429 con ``Retry-After`` si se supera el límite."""
        limit, window = self._limits[bucket]
        limit *= self._scale
        now = self._clock()
        hits = self._hits[(bucket, key)]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            retry = max(1, math.ceil(hits[0] + window - now))
            raise ProblemError(
                429,
                "rate_limited",
                "Demasiados intentos. Espera un momento y vuelve a probar.",
                headers={"Retry-After": str(retry)},
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()

"""Limitación de tasa en memoria por proceso (ventana deslizante).

S-01 (``docs/reviews/f3-security.md``): la clave del bucket ``login``/``register`` es el correo
enviado por el cliente, sin autenticar y sin validar que exista. Sin más control, un atacante que
mande cada petición con un correo distinto crearía una entrada nueva por intento que nunca se
libera, agotando la memoria del proceso. Para evitarlo, cada bucket mantiene como mucho
``max_keys_per_bucket`` claves vivas con expulsión LRU (la clave usada hace más tiempo se
descarta primero) y una clave sin marcas de tiempo vigentes se borra del todo en vez de dejarse
vacía en el diccionario.
"""

import math
import time
from collections import deque
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

# Cota superior de claves vivas por bucket. Con la ventana más amplia (60 s) y como mucho estas
# claves por bucket, la memoria del proceso queda acotada aunque el bucket sea explotable sin
# autenticar (``login``/``register``): suficiente para v1 sin depender de Redis.
DEFAULT_MAX_KEYS_PER_BUCKET: Final = 10_000


class RateLimiter:
    """Cuenta peticiones por (bucket, clave). ``scale`` multiplica los límites (tests)."""

    def __init__(
        self,
        limits: dict[str, tuple[int, int]] | None = None,
        *,
        scale: int = 1,
        clock: Callable[[], float] = time.monotonic,
        max_keys_per_bucket: int = DEFAULT_MAX_KEYS_PER_BUCKET,
    ) -> None:
        self._limits = dict(limits or DEFAULT_LIMITS)
        self._scale = scale
        self._clock = clock
        self._max_keys_per_bucket = max_keys_per_bucket
        # dict por bucket (nombres fijos, no controlados por el atacante) de dict por clave
        # (sí controlada por el atacante): ``dict`` conserva el orden de inserción, así que
        # reinsertar una clave tras usarla la mueve al final y la deja como
        # "más recientemente usada" para la expulsión LRU de ``_evict``.
        self._hits: dict[str, dict[str, deque[float]]] = {}

    def check(self, bucket: str, key: str) -> None:
        """Registra una petición; lanza 429 con ``Retry-After`` si se supera el límite."""
        limit, window = self._limits[bucket]
        limit *= self._scale
        now = self._clock()
        keys = self._hits.setdefault(bucket, {})
        hits = keys.pop(key, None) or deque()
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            if hits:
                keys[key] = hits  # todavía vigente: se reinserta (LRU) sin contar de más
            retry = max(1, math.ceil(hits[0] + window - now))
            raise ProblemError(
                429,
                "rate_limited",
                "Demasiados intentos. Espera un momento y vuelve a probar.",
                headers={"Retry-After": str(retry)},
            )
        hits.append(now)
        keys[key] = hits
        self._evict(keys)

    def _evict(self, keys: dict[str, deque[float]]) -> None:
        """Expulsa las claves más antiguas hasta respetar ``max_keys_per_bucket`` (S-01)."""
        while len(keys) > self._max_keys_per_bucket:
            oldest = next(iter(keys))
            del keys[oldest]

    def reset(self) -> None:
        self._hits.clear()

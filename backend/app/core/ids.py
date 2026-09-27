"""Identificadores UUID v7 (RFC 9562) generados en la aplicación."""

import os
import time
import uuid

# Espacio de nombres fijo para derivar ids estables cuando un ``client_uuid`` global (único por
# diseño) ya pertenece a otra cuenta: la importación de cuentas (`services/account.py`) y el
# `set_upsert` de `/sync` (S-05, `docs/reviews/f3-security.md`) usan el mismo espacio para no
# duplicar la lógica y para que ambos caminos deriven el mismo id ante la misma entrada.
DERIVED_UUID_NAMESPACE = uuid.UUID("6f0f7a3e-3c1c-5d0e-9a53-5b1a0b6f0c11")


def uuid7() -> uuid.UUID:
    """UUID v7: 48 bits de milisegundos Unix + aleatorio (ordenable por tiempo)."""
    millis = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    value = (millis & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76
    value |= ((rand >> 68) & 0xFFF) << 64
    value |= 0b10 << 62
    value |= rand & ((1 << 62) - 1)
    return uuid.UUID(int=value)


def derived_uuid(user_id: uuid.UUID, original: uuid.UUID) -> uuid.UUID:
    """UUID v5 estable derivado de un ``client_uuid`` ajeno para una cuenta dada.

    Se usa cuando un ``client_uuid`` global (único por diseño, p. ej. en la importación de una
    cuenta o en ``/sync``) ya pertenece a **otra** cuenta: en vez de fallar revelando que ese id
    existe en el sistema (fuga de un bit, IDOR parcial, ver S-05) o de sobrescribir datos ajenos,
    se deriva un id nuevo y estable para la cuenta actual. La misma entrada (mismo usuario, mismo
    id original) siempre produce el mismo resultado, así que reintentar la operación es
    idempotente.
    """
    return uuid.uuid5(DERIVED_UUID_NAMESPACE, f"{user_id}:{original}")

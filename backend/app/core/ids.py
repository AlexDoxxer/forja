"""Identificadores UUID v7 (RFC 9562) generados en la aplicación."""

import os
import time
import uuid


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

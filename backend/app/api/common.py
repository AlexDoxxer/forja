"""Utilidades compartidas por los routers."""

import base64
import json
from typing import Any, Final

from app.core.errors import TITLES, ProblemError
from app.schemas import api

ERRORS: Final = {code: {"model": api.Problem, "description": TITLES[code]} for code in TITLES}


def errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta en OpenAPI las respuestas de error de una operación."""
    return {code: dict(ERRORS[code]) for code in codes}


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    """Decodifica un cursor opaco; un cursor manipulado es un 422."""
    if cursor is None:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ProblemError(422, "validation_error", "El cursor no es válido.") from exc
    if not isinstance(data, dict):
        raise ProblemError(422, "validation_error", "El cursor no es válido.")
    return data

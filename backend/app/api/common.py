"""Utilidades compartidas por los routers."""

import base64
import hashlib
import json
from typing import Any, Final

from fastapi import Response
from pydantic import BaseModel

from app.core.errors import TITLES, ProblemError
from app.schemas import api


def etag_json(if_none_match: str | None, model: BaseModel) -> Response:
    """Respuesta JSON con ``ETag`` débil (hash del cuerpo) y ``304`` si ``If-None-Match`` coincide."""
    body = json.dumps(
        model.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=False
    ).encode()
    etag = f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    sent = if_none_match or ""
    if sent.strip() == "*" or etag in {token.strip() for token in sent.split(",")}:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)



ERRORS: Final = {code: {"model": api.Problem, "description": TITLES[code]} for code in TITLES}


def errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta en OpenAPI las respuestas de error de una operación."""
    return {code: dict(ERRORS[code]) for code in codes}


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    """Decodifica un cursor opaco; un cursor manipulado es un 422."""
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ProblemError(422, "validation_error", "El cursor no es válido.") from exc
    if not isinstance(data, dict):
        raise ProblemError(422, "validation_error", "El cursor no es válido.")
    return data

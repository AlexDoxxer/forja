"""Middleware de seguridad: ``X-Request-ID``, cabeceras, tamaño de cuerpo y CSRF."""

import time
import uuid
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.errors import ProblemError, problem_response
from app.core.logging import get_logger, request_id_var
from app.security.tokens import CSRF_COOKIE, CSRF_HEADER, UNSAFE_METHODS, csrf_matches

API_PREFIX: Final = "/api/v1"
DEFAULT_BODY_LIMIT: Final = 1 * 1024 * 1024
LARGE_BODY_LIMIT: Final = 10 * 1024 * 1024
LARGE_BODY_PATHS: Final = frozenset({f"{API_PREFIX}/me/import", f"{API_PREFIX}/sync"})

SECURITY_HEADERS: Final = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; script-src 'self'; "
        "style-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
}

_log = get_logger("forja.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """``X-Request-ID``, cabeceras de seguridad y línea de acceso sin PII."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if 8 <= len(incoming) <= 64 and incoming.isascii() else uuid.uuid4().hex  # noqa: PLR2004
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(API_PREFIX):
            response.headers.setdefault("Cache-Control", "no-store")
        route = request.scope.get("route")
        _log.info(
            "request",
            extra={
                "method": request.method,
                "route": getattr(route, "path", request.url.path if route else "unmatched"),
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "request_id": rid,
            },
        )
        return response


class BodyLimitAndCsrfMiddleware(BaseHTTPMiddleware):
    """Límite de tamaño por ``Content-Length`` y CSRF de doble envío en métodos no seguros."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith(API_PREFIX):
            limit = LARGE_BODY_LIMIT if path in LARGE_BODY_PATHS else DEFAULT_BODY_LIMIT
            length = request.headers.get("content-length")
            if length is not None and length.isdigit() and int(length) > limit:
                error = ProblemError(
                    413, "payload_too_large", "El cuerpo de la petición supera el límite."
                )
                return problem_response(error, request)
            if request.method in UNSAFE_METHODS and not csrf_matches(
                request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
            ):
                error = ProblemError(
                    403, "csrf_failed", "Falta o no es válido el token CSRF (X-CSRF-Token)."
                )
                return problem_response(error, request)
        return await call_next(request)

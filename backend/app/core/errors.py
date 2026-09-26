"""Errores RFC 9457 (``application/problem+json``) centralizados (ADR 0009)."""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_var

PROBLEM_MEDIA_TYPE: Final = "application/problem+json"

TITLES: Final[Mapping[int, str]] = {
    400: "Petición incorrecta",
    401: "No autenticado",
    403: "Acción no permitida",
    404: "Recurso no encontrado",
    405: "Método no permitido",
    409: "Conflicto",
    413: "Cuerpo demasiado grande",
    422: "Datos no válidos",
    429: "Demasiadas peticiones",
    500: "Error interno",
    503: "Servicio no disponible",
}

_log = get_logger("forja.errors")


class ProblemError(Exception):
    """Error de aplicación que se serializa como problema RFC 9457."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str | None = None,
        *,
        title: str | None = None,
        headers: Mapping[str, str] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.detail = detail
        self.title = title or TITLES.get(status, "Error")
        self.headers = dict(headers or {})
        self.extra = dict(extra or {})


def unauthenticated() -> ProblemError:
    return ProblemError(401, "unauthenticated", "Inicia sesión para continuar.")


def forbidden(code: str = "forbidden", detail: str | None = None) -> ProblemError:
    return ProblemError(403, code, detail or "No tienes permiso para esta acción.")


def not_found(detail: str = "El recurso no existe.") -> ProblemError:
    return ProblemError(404, "not_found", detail)


def conflict(code: str, detail: str) -> ProblemError:
    return ProblemError(409, code, detail)


def unprocessable(code: str, detail: str, **extra: Any) -> ProblemError:
    return ProblemError(422, code, detail, extra=extra)


def problem_response(error: ProblemError, request: Request | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"/problems/{error.code.replace('_', '-')}",
        "title": error.title,
        "status": error.status,
        "code": error.code,
        "request_id": request_id_var.get(),
    }
    if error.detail is not None:
        body["detail"] = error.detail
    if request is not None:
        body["instance"] = request.url.path
    body.update(error.extra)
    headers = {"Content-Type": PROBLEM_MEDIA_TYPE, **error.headers}
    return JSONResponse(body, status_code=error.status, headers=headers, media_type=PROBLEM_MEDIA_TYPE)


def validation_issues(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "loc": [part for part in err.get("loc", ()) if isinstance(part, str | int)],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "value_error")),
        }
        for err in errors
    ]


def install_handlers(app: FastAPI) -> None:
    """Registra los manejadores de excepciones que producen ``problem+json``."""

    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(exc, request)

    @app.exception_handler(RequestValidationError)
    async def _request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = ProblemError(
            422,
            "validation_error",
            "Hay datos no válidos en la petición.",
            extra={"errors": validation_issues(exc.errors())},
        )
        return problem_response(error, request)

    @app.exception_handler(ValidationError)
    async def _domain_validation(request: Request, exc: ValidationError) -> JSONResponse:
        error = ProblemError(
            422,
            "validation_error",
            "Hay datos no válidos en la petición.",
            extra={"errors": validation_issues(exc.errors(include_url=False, include_context=False))},
        )
        return problem_response(error, request)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}.get(
            exc.status_code, "conflict" if exc.status_code == 409 else "http_error"
        )
        error = ProblemError(exc.status_code, code, None if exc.status_code == 404 else str(exc.detail))
        return problem_response(error, request)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        _log.error("unhandled_exception", extra={"error_type": type(exc).__name__})
        error = ProblemError(500, "internal_error", "Ha ocurrido un error inesperado.")
        return problem_response(error, request)

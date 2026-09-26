"""Tokens opacos, cookies de sesión/CSRF y hash de IP."""

import hashlib
import hmac
import secrets
from typing import Final

from fastapi import Request, Response

SESSION_COOKIE: Final = "__Host-forja_session"
CSRF_COOKIE: Final = "__Host-forja_csrf"
CSRF_HEADER: Final = "X-CSRF-Token"
UNSAFE_METHODS: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def new_token() -> str:
    """Token aleatorio de 32 bytes (URL-safe)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hexadecimal: lo único que se guarda de la sesión."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_ip(ip: str | None, secret: str) -> str | None:
    if not ip:
        return None
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


def set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    value = token or new_token()
    response.set_cookie(
        CSRF_COOKIE, value, max_age=None, path="/", secure=True, httponly=False, samesite="lax"
    )
    return value


def csrf_matches(cookie: str | None, header: str | None) -> bool:
    if not cookie or not header:
        return False
    return hmac.compare_digest(cookie.encode(), header.encode())

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


def client_ip(request: Request, trusted_proxy_count: int = 0) -> str | None:
    """IP real del cliente para el rate limit y el ``ip_hash`` de auditoría (S-02).

    Por defecto (``trusted_proxy_count=0``, "confiar en ninguno") ignora por completo
    ``X-Forwarded-For`` -- que cualquier cliente puede fijar a lo que quiera, distinto en
    cada petición -- y usa el par IP del socket TCP (``request.client``), que el cliente no
    puede falsificar. Solo cuando el despliegue confirma cuántos proxies de confianza hay
    delante de la app (``TRUSTED_PROXY_COUNT`` en el entorno, ver ``.env.example``) se lee la
    cabecera, tomando el salto que ese número de proxies no pudo haber sobrescrito (contando
    desde la derecha, no el primer valor, que sigue controlando el cliente).
    """
    peer = request.client.host if request.client else None
    if trusted_proxy_count <= 0:
        return peer
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    index = len(hops) - trusted_proxy_count
    if 0 <= index < len(hops):
        return hops[index]
    return peer


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

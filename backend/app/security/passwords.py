"""Contraseñas: argon2id (parámetros OWASP), política mínima y lista local de comunes."""

import asyncio
from functools import lru_cache
from typing import Final

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH: Final = 10

# OWASP: m = 19 MiB, t = 2, p = 1 como mínimo (ADR 0003).
_HASHER: Final = PasswordHasher(
    time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
)

COMMON_PASSWORDS: Final = frozenset(
    """
    1234567890 0123456789 123456789012 1q2w3e4r5t 1qaz2wsx3edc qwertyuiop qwerty1234 qwerty12345
    qwertyuiop123 asdfghjkl1 asdfghjklñ zxcvbnm123 password12 password123 password1234 password1!
    passw0rd12 passw0rd123 p@ssw0rd12 p@ssword123 contraseña contraseña1 contraseña12
    contraseña123 contraseña1234 micontraseña mipassword1 miclave1234 clave12345 clave123456
    abcdefghij abcd123456 abc1234567 iloveyou12 iloveyou123 letmein123 welcome123 welcome1234
    admin12345 admin123456 administrator changeme123 trustno1234 football123 baseball123
    superman123 monkey12345 dragon12345 master12345 shadow12345 sunshine123 princess123
    starwars123 whatever123 freedom123 hello12345 hola123456 holamundo1 holamundo123 bienvenido1
    barcelona10 realmadrid1 realmadrid10 futbol12345 gimnasio123 entrenar123 forja12345
    forja123456 forjaforja1 1111111111 0000000000 2222222222 1212121212 1234512345 9876543210
    0987654321 12345678910 123456789a a123456789 a1234567890 qazwsxedc12 zaq12wsxcde qweasdzxc1
    q1w2e3r4t5 q1w2e3r4t5y6 1q2w3e4r5t6y 1qazxsw23edc passpass12 password00 password11
    password99 letmein1234 iloveyou1234 sunshine12 princess12 michael1234 jennifer123 jordan2323
    """.split()
)


def is_weak_password(password: str, email: str | None = None) -> bool:
    """``True`` si la contraseña está en la lista local, es un único carácter repetido o
    contiene el usuario del correo."""
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS or len(set(lowered)) <= 2:  # noqa: PLR2004
        return True
    if email:
        local = email.split("@", 1)[0].lower()
        if len(local) >= 4 and local in lowered:  # noqa: PLR2004
            return True
    return False


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _HASHER.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _HASHER.check_needs_rehash(stored_hash)


@lru_cache(maxsize=1)
def decoy_hash() -> str:
    """Hash señuelo: el login con un correo inexistente cuesta lo mismo que con uno real."""
    return _HASHER.hash("decoy-password-not-used")


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(stored_hash: str, password: str) -> bool:
    return await asyncio.to_thread(verify_password, stored_hash, password)

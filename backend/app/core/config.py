"""Configuración de Forja: exclusivamente por variables de entorno (MASTER_PROMPT §12.3).

Toda variable documentada en ``.env.example`` tiene aquí su campo validado. Un valor inválido
hace fallar el arranque (fallo rápido), nunca se sustituye en silencio por un valor por defecto.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATASET_REPO = "https://github.com/hasaneyldrm/exercises-dataset"
DEFAULT_DATASET_COMMIT = "7455efae41b330c265e7cd4b78dfa848e7ce5ebd"
MIN_SECRET_KEY_LENGTH = 32

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
Locale = Literal["es", "en"]


class Settings(BaseSettings):
    """Ajustes de la aplicación leídos del entorno (nombres en mayúsculas, sin prefijo)."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        env_file=None,
    )

    database_url: PostgresDsn
    secret_key: SecretStr
    public_base_url: AnyHttpUrl
    media_root: Path = Path("/var/lib/forja/media")
    media_require_auth: bool = True
    dataset_repo: AnyHttpUrl = AnyHttpUrl(DEFAULT_DATASET_REPO)
    dataset_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")] = DEFAULT_DATASET_COMMIT
    registration_open: bool = False
    diet_feature_enabled: bool = True
    default_locale: Locale = "es"
    log_level: LogLevel = "INFO"
    gunicorn_workers: Annotated[int, Field(ge=1, le=32)] = 2
    session_ttl_days: Annotated[int, Field(ge=1, le=365)] = 30
    metrics_enabled: bool = False

    @field_validator("database_url")
    @classmethod
    def _require_asyncpg_driver(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+asyncpg":
            msg = "DATABASE_URL debe usar el esquema postgresql+asyncpg://"
            raise ValueError(msg)
        return value

    @field_validator("secret_key")
    @classmethod
    def _require_strong_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_SECRET_KEY_LENGTH:
            msg = f"SECRET_KEY debe tener al menos {MIN_SECRET_KEY_LENGTH} caracteres"
            raise ValueError(msg)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve los ajustes del proceso (cacheados; se leen una sola vez del entorno)."""
    return Settings()

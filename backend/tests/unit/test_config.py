"""Validación de la configuración por entorno (MASTER_PROMPT §12.3)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_DATASET_COMMIT, Settings, get_settings

VALID_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://forja:clave@db:5432/forja",
    "SECRET_KEY": "k" * 48,
    "PUBLIC_BASE_URL": "https://forja.example.org",
}


@pytest.fixture
def base_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


@pytest.mark.usefixtures("base_env")
def test_defaults_follow_master_prompt() -> None:
    settings = Settings()
    assert settings.media_require_auth is True
    assert settings.dataset_commit == DEFAULT_DATASET_COMMIT
    assert str(settings.dataset_repo).startswith("https://github.com/hasaneyldrm/")
    assert settings.registration_open is False
    assert settings.diet_feature_enabled is True
    assert settings.default_locale == "es"
    assert settings.log_level == "INFO"
    assert settings.gunicorn_workers == 2
    assert settings.session_ttl_days == 30
    assert settings.metrics_enabled is False
    assert settings.media_root == Path("/var/lib/forja/media")


def test_environment_overrides_are_parsed(base_env: pytest.MonkeyPatch) -> None:
    base_env.setenv("MEDIA_REQUIRE_AUTH", "false")
    base_env.setenv("REGISTRATION_OPEN", "true")
    base_env.setenv("GUNICORN_WORKERS", "4")
    base_env.setenv("DEFAULT_LOCALE", "en")
    base_env.setenv("MEDIA_ROOT", "/srv/media")
    settings = Settings()
    assert settings.media_require_auth is False
    assert settings.registration_open is True
    assert settings.gunicorn_workers == 4
    assert settings.default_locale == "en"
    assert settings.media_root == Path("/srv/media")
    assert settings.secret_key.get_secret_value() == "k" * 48
    assert "k" * 48 not in repr(settings)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("DATABASE_URL", "postgresql://forja:clave@db:5432/forja"),
        ("DATABASE_URL", "mysql://forja@db/forja"),
        ("SECRET_KEY", "corta"),
        ("PUBLIC_BASE_URL", "no-es-una-url"),
        ("DATASET_COMMIT", "7455efae"),
        ("GUNICORN_WORKERS", "0"),
        ("DEFAULT_LOCALE", "fr"),
        ("LOG_LEVEL", "VERBOSE"),
    ],
)
def test_invalid_values_fail_fast(base_env: pytest.MonkeyPatch, variable: str, value: str) -> None:
    base_env.setenv(variable, value)
    with pytest.raises(ValidationError):
        Settings()


def test_missing_required_variables_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in VALID_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.usefixtures("base_env")
def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()

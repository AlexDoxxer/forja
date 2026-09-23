"""`.env.example` documenta exactamente las variables que valida `Settings` (§12.3)."""

from pathlib import Path

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[3] / ".env.example"
# Variables consumidas por docker compose (servicios `db` y `web`), no por la API.
COMPOSE_ONLY = frozenset({"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "WEB_PORT"})
MASTER_PROMPT_VARIABLES = frozenset(
    {
        "DATABASE_URL",
        "SECRET_KEY",
        "PUBLIC_BASE_URL",
        "MEDIA_ROOT",
        "MEDIA_REQUIRE_AUTH",
        "DATASET_REPO",
        "DATASET_COMMIT",
        "REGISTRATION_OPEN",
        "DIET_FEATURE_ENABLED",
        "DEFAULT_LOCALE",
        "LOG_LEVEL",
        "GUNICORN_WORKERS",
    }
)


def declared_variables() -> set[str]:
    names: set[str] = set()
    for raw in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.add(line.split("=", 1)[0])
    return names


def test_env_example_matches_settings() -> None:
    settings_variables = {name.upper() for name in Settings.model_fields}
    assert declared_variables() - COMPOSE_ONLY == settings_variables


def test_env_example_covers_master_prompt_variables() -> None:
    assert declared_variables() >= MASTER_PROMPT_VARIABLES

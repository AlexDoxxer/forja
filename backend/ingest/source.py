"""Lectura y validación del dataset de origen (``data/exercises.json``, MASTER_PROMPT §3)."""

import json
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ingest.domain import INSTRUCTION_LANGS

DATA_FILE: Final = "data/exercises.json"
SCHEMA_FILE: Final = "data/exercises.schema.json"
MAX_REPORTED_ERRORS: Final = 20


class SourceError(ValueError):
    """El dataset de origen no existe, no es JSON o no cumple su esquema."""


class RawExercise(BaseModel):
    """Registro del dataset tal cual (solo se validan los campos que usa Forja)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(pattern=r"^[0-9]{4}$")
    name: str = Field(min_length=1)
    category: str
    body_part: str
    equipment: str
    target: str
    muscle_group: str
    secondary_muscles: tuple[str, ...]
    instructions: dict[str, str]
    instruction_steps: dict[str, tuple[str, ...]]
    media_id: str = Field(min_length=1)
    image: str
    gif_url: str
    attribution: str


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        msg = f"No se puede leer {path}: {exc}"
        raise SourceError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"{path} no es JSON válido: {exc}"
        raise SourceError(msg) from exc


def validate_against_schema(data: Any, schema: Any) -> None:
    """Valida ``data`` contra el JSON Schema 2020-12 del dataset (incluye ``format``)."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<raíz>'}: {error.message}"
            for error in errors[:MAX_REPORTED_ERRORS]
        )
        msg = f"El dataset no cumple exercises.schema.json ({len(errors)} errores): {details}"
        raise SourceError(msg)


def parse_records(data: Any) -> tuple[RawExercise, ...]:
    """Convierte la lista JSON en registros tipados y comprueba ids únicos e idiomas."""
    if not isinstance(data, list):
        msg = "data/exercises.json debe ser una lista de ejercicios"
        raise SourceError(msg)
    try:
        records = tuple(RawExercise.model_validate(item) for item in data)
    except ValidationError as exc:
        msg = f"Registro de ejercicio inválido: {exc}"
        raise SourceError(msg) from exc
    seen: set[str] = set()
    for record in records:
        if record.id in seen:
            msg = f"Id de ejercicio duplicado: {record.id}"
            raise SourceError(msg)
        seen.add(record.id)
        missing = [
            lang
            for lang in INSTRUCTION_LANGS
            if not record.instructions.get(lang) or not record.instruction_steps.get(lang)
        ]
        if missing:
            msg = f"El ejercicio {record.id} no tiene instrucciones en: {', '.join(missing)}"
            raise SourceError(msg)
    return tuple(sorted(records, key=lambda record: record.id))


def load_dataset(root: Path, *, validate_schema: bool = True) -> tuple[RawExercise, ...]:
    """Lee ``<root>/data/exercises.json``, lo valida contra su esquema y lo tipa."""
    data = _load_json(root / DATA_FILE)
    if validate_schema:
        validate_against_schema(data, _load_json(root / SCHEMA_FILE))
    return parse_records(data)

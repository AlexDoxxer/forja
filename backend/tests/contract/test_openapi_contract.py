"""Contrato OpenAPI versionado (`contracts/openapi.yaml`).

Comprueba que el contrato es OpenAPI 3.1 válido, que cubre exactamente los endpoints de
MASTER_PROMPT §9 (más las ampliaciones aprobadas en ADR 0009), que las convenciones
transversales se cumplen en todas las operaciones y que todos los ejemplos (que usan los
mocks MSW del frontend) validan contra sus esquemas. Cuando exista la app FastAPI, el
agente backend-api añade aquí la comparación con el esquema exportado.
"""

from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "openapi.yaml"
BASE_URI = "urn:forja:openapi"
HTTP_METHODS = ("get", "put", "post", "delete", "patch")
UNSAFE_METHODS = frozenset({"put", "post", "delete", "patch"})

# Endpoints de MASTER_PROMPT §9 (prefijo /api/v1 declarado en `servers`).
MASTER_PROMPT_ENDPOINTS = frozenset(
    {
        ("get", "/health"),
        ("get", "/ready"),
        ("post", "/auth/register"),
        ("post", "/auth/login"),
        ("post", "/auth/logout"),
        ("get", "/auth/me"),
        ("post", "/auth/password"),
        ("get", "/auth/check"),
        ("get", "/profile"),
        ("put", "/profile"),
        ("put", "/profile/parq"),
        ("get", "/body-metrics"),
        ("post", "/body-metrics"),
        ("delete", "/body-metrics/{metric_id}"),
        ("get", "/exercises"),
        ("get", "/exercises/{exercise_id}"),
        ("get", "/exercises/{exercise_id}/alternatives"),
        ("get", "/catalog/facets"),
        ("put", "/exercises/{exercise_id}/favorite"),
        ("delete", "/exercises/{exercise_id}/favorite"),
        ("post", "/generator/preview"),
        ("post", "/programs"),
        ("post", "/programs/{program_id}/regenerate-day"),
        ("post", "/programs/{program_id}/swap"),
        ("get", "/programs"),
        ("get", "/programs/{program_id}"),
        ("patch", "/programs/{program_id}"),
        ("delete", "/programs/{program_id}"),
        ("post", "/programs/{program_id}/activate"),
        ("post", "/programs/{program_id}/duplicate"),
        ("put", "/programs/{program_id}/days/{day_id}"),
        ("get", "/programs/{program_id}/export.pdf"),
        ("get", "/programs/{program_id}/calendar.ics"),
        ("post", "/sessions"),
        ("get", "/sessions"),
        ("get", "/sessions/{session_id}"),
        ("patch", "/sessions/{session_id}"),
        ("post", "/sessions/{session_id}/sets"),
        ("patch", "/sessions/{session_id}/sets/{set_id}"),
        ("delete", "/sessions/{session_id}/sets/{set_id}"),
        ("post", "/sessions/{session_id}/finish"),
        ("post", "/sync"),
        ("get", "/stats/overview"),
        ("get", "/stats/volume"),
        ("get", "/stats/exercise/{exercise_id}"),
        ("get", "/records"),
        ("get", "/sessions/next"),
        ("get", "/nutrition/settings"),
        ("put", "/nutrition/settings"),
        ("post", "/nutrition/targets/calculate"),
        ("post", "/nutrition/plans"),
        ("get", "/nutrition/plans/{plan_id}"),
        ("post", "/nutrition/plans/{plan_id}/swap"),
        ("get", "/nutrition/plans/{plan_id}/shopping-list"),
        ("get", "/foods"),
        ("get", "/me/export"),
        ("post", "/me/import"),
        ("delete", "/me"),
        ("get", "/admin/settings"),
        ("put", "/admin/settings"),
        ("get", "/admin/users"),
        ("patch", "/admin/users/{user_id}"),
        ("post", "/admin/ingest"),
        ("get", "/admin/ingest/runs"),
    }
)

# Ampliaciones aprobadas (ADR 0009): CSRF, sesiones activas (§10.2/§11), créditos (§2.1),
# acciones del wizard sobre planes sin guardar (§10.2.3) y listado de planes de comidas.
APPROVED_EXTENSIONS = frozenset(
    {
        ("get", "/auth/csrf"),
        ("get", "/auth/sessions"),
        ("delete", "/auth/sessions/{auth_session_id}"),
        ("get", "/about"),
        ("post", "/generator/preview/regenerate-day"),
        ("post", "/generator/preview/swap"),
        ("get", "/nutrition/plans"),
    }
)

PUBLIC_OPERATIONS = frozenset(
    {
        ("get", "/health"),
        ("get", "/ready"),
        ("get", "/about"),
        ("get", "/auth/csrf"),
        ("post", "/auth/register"),
        ("post", "/auth/login"),
    }
)
IDEMPOTENT_POSTS = frozenset({("post", "/sessions"), ("post", "/sessions/{session_id}/sets")})
# Errores que deliberadamente no son problem+json: `auth_request` de nginx exige 401 sin
# cuerpo y el healthcheck de /ready devuelve el detalle de comprobaciones.
NON_PROBLEM_ERRORS = frozenset({("get", "/auth/check", "401"), ("get", "/ready", "503")})
ETAG_OPERATIONS = frozenset(
    {
        ("get", "/exercises"),
        ("get", "/exercises/{exercise_id}"),
        ("get", "/exercises/{exercise_id}/alternatives"),
        ("get", "/catalog/facets"),
    }
)


@cache
def load_contract() -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


def operations() -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, item in load_contract()["paths"].items():
        for method in HTTP_METHODS:
            if method in item:
                yield method, path, item[method]


def resolve(node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if ref is None:
        return node
    target: Any = load_contract()
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return cast("dict[str, Any]", target)


def validator_for(schema: dict[str, Any]) -> Draft202012Validator:
    resource: Resource[Any] = DRAFT202012.create_resource(load_contract())
    registry: Registry[Any] = Registry().with_resource(uri=BASE_URI, resource=resource)
    wrapped = {"$id": f"{BASE_URI}-example", "allOf": [rebase_refs(schema)]}
    return Draft202012Validator(wrapped, registry=registry, format_checker=FormatChecker())


def rebase_refs(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: (
                f"{BASE_URI}{value}"
                if key == "$ref" and value.startswith("#")
                else rebase_refs(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [rebase_refs(item) for item in node]
    return node


def examples() -> Iterator[tuple[str, dict[str, Any], Any]]:
    """Todos los ejemplos del contrato con el esquema que deben cumplir."""
    contract = load_contract()
    for name, schema in contract["components"]["schemas"].items():
        if "example" in schema:
            yield f"schemas/{name}", schema, schema["example"]
    for name, response in contract["components"]["responses"].items():
        for media, body in response.get("content", {}).items():
            if "example" in body:
                yield f"responses/{name} {media}", body["schema"], body["example"]
    for method, path, operation in operations():
        bodies: list[tuple[str, dict[str, Any]]] = []
        if "requestBody" in operation:
            bodies.extend(("request", b) for b in operation["requestBody"]["content"].values())
        for status, response in operation["responses"].items():
            bodies.extend((status, b) for b in resolve(response).get("content", {}).values())
        for label, body in bodies:
            if "example" in body:
                yield f"{method.upper()} {path} {label}", body["schema"], body["example"]
        for parameter in operation.get("parameters", []):
            param = resolve(parameter)
            if "example" in param:
                yield f"{method.upper()} {path} ?{param['name']}", param["schema"], param["example"]


def test_contract_is_valid_openapi_31() -> None:
    contract = load_contract()
    assert contract["openapi"].startswith("3.1")
    validate(contract)


def test_contract_covers_master_prompt_endpoints_exactly() -> None:
    declared = {(method, path) for method, path, _ in operations()}
    missing = MASTER_PROMPT_ENDPOINTS - declared
    unexpected = declared - MASTER_PROMPT_ENDPOINTS - APPROVED_EXTENSIONS
    assert not missing, f"Endpoints de §9 sin contrato: {sorted(missing)}"
    assert not unexpected, f"Endpoints no aprobados: {sorted(unexpected)}"


def test_server_prefix_is_api_v1() -> None:
    assert load_contract()["servers"][0]["url"] == "/api/v1"


def test_operation_ids_are_unique() -> None:
    ids = [operation["operationId"] for _, _, operation in operations()]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(("method", "path", "operation"), list(operations()))
def test_security_conventions(method: str, path: str, operation: dict[str, Any]) -> None:
    security = operation.get("security", load_contract()["security"])
    schemes = {name for requirement in security for name in requirement}
    if (method, path) in PUBLIC_OPERATIONS:
        assert "sessionCookie" not in schemes or len(security) > 1
    else:
        assert "sessionCookie" in schemes
    if method in UNSAFE_METHODS:
        assert all("csrfToken" in requirement for requirement in security), (
            f"{method.upper()} {path} debe exigir X-CSRF-Token"
        )


@pytest.mark.parametrize(("method", "path", "operation"), list(operations()))
def test_error_responses_are_problem_details(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    for status, response in operation["responses"].items():
        code = int(status)
        resolved = resolve(response)
        if code >= 400 and (method, path, status) not in NON_PROBLEM_ERRORS:
            assert "application/problem+json" in resolved.get("content", {}), (
                f"{method.upper()} {path} {status} debe ser application/problem+json"
            )


def test_paginated_lists_use_cursor_envelope() -> None:
    paginated = 0
    for method, path, operation in operations():
        refs = {parameter.get("$ref", "") for parameter in operation.get("parameters", [])}
        if "#/components/parameters/Cursor" not in refs:
            continue
        paginated += 1
        assert method == "get", path
        assert "#/components/parameters/Limit" in refs, path
        body = operation["responses"]["200"]["content"]["application/json"]["schema"]
        schema = resolve(body)
        assert set(schema["required"]) == {"items", "next_cursor"}, path
        assert schema["properties"]["next_cursor"]["type"] == ["string", "null"], path
    assert paginated >= 9


def test_idempotency_key_required_on_session_writes() -> None:
    for method, path, operation in operations():
        refs = {parameter.get("$ref", "") for parameter in operation.get("parameters", [])}
        has_key = "#/components/parameters/IdempotencyKey" in refs
        assert has_key == ((method, path) in IDEMPOTENT_POSTS), f"{method.upper()} {path}"


def test_catalog_reads_expose_etag_and_not_modified() -> None:
    for method, path, operation in operations():
        if (method, path) in ETAG_OPERATIONS:
            assert "ETag" in operation["responses"]["200"]["headers"]
            assert "304" in operation["responses"]


def test_media_attribution_is_mandatory_in_exercise_media() -> None:
    schemas = load_contract()["components"]["schemas"]
    assert "attribution" in schemas["ExerciseMedia"]["required"]
    attribution = schemas["MediaAttribution"]["properties"]
    assert attribution["text"]["const"] == "© Gym visual"
    assert attribution["url"]["const"] == "https://gymvisual.com/"


def test_contract_declares_examples() -> None:
    assert len(list(examples())) >= 20


@pytest.mark.parametrize(("where", "schema", "example"), list(examples()))
def test_examples_match_their_schemas(where: str, schema: dict[str, Any], example: Any) -> None:
    errors = sorted(validator_for(schema).iter_errors(example), key=lambda e: list(e.path))
    assert not errors, f"{where}: " + "; ".join(e.message for e in errors[:5])

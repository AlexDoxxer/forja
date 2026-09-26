"""El OpenAPI exportado por FastAPI coincide con ``contracts/openapi.yaml`` (F2-BE-17)."""

import os
import re
from functools import cache
from typing import Any

import pytest

from tests.contract.test_openapi_contract import HTTP_METHODS, load_contract, resolve

PREFIX = "/api/v1"
# Pydantic/FastAPI añaden 422 a toda operación con entrada y ``validation_error`` estándar.
IGNORED_EXTRA_STATUSES = frozenset({"422"})


@cache
def generated() -> dict[str, Any]:
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/forja")
    os.environ.setdefault("SECRET_KEY", "k" * 40)
    os.environ.setdefault("PUBLIC_BASE_URL", "https://forja.test")
    from app.main import create_app  # noqa: PLC0415

    spec: dict[str, Any] = create_app().openapi()
    return spec


def operations(spec: dict[str, Any], *, prefix: str) -> dict[tuple[str, str], dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for path, item in spec["paths"].items():
        for method in HTTP_METHODS:
            if method in item:
                op = dict(item[method])
                op["_path_parameters"] = item.get("parameters", [])
                found[(method, path.removeprefix(prefix))] = op
    return found


def _params(op: dict[str, Any], spec: dict[str, Any]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for raw in [*op.get("_path_parameters", []), *op.get("parameters", [])]:
        node = raw
        while "$ref" in node:
            target: Any = spec
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            node = target
        result.add((node["name"].lower(), node["in"]))
    return result


CONTRACT_OPS = operations(load_contract(), prefix="")


def test_same_operations_and_ids() -> None:
    mine = operations(generated(), prefix=PREFIX)
    assert set(mine) == set(CONTRACT_OPS)
    for key, contract_op in CONTRACT_OPS.items():
        assert mine[key]["operationId"] == contract_op["operationId"], key


@pytest.mark.parametrize("key", sorted(CONTRACT_OPS))
def test_parameters_status_codes_and_body_match(key: tuple[str, str]) -> None:
    mine = operations(generated(), prefix=PREFIX)[key]
    contract = CONTRACT_OPS[key]
    missing = _params(contract, load_contract()) - _params(mine, generated())
    assert not missing, f"{key}: parámetros del contrato sin implementar: {sorted(missing)}"
    contract_codes = set(contract["responses"])
    assert contract_codes <= set(mine["responses"]), (
        f"{key}: faltan respuestas {contract_codes - set(mine['responses'])}"
    )
    extra = set(mine["responses"]) - contract_codes - IGNORED_EXTRA_STATUSES
    assert not extra, f"{key}: respuestas fuera del contrato {extra}"
    assert ("requestBody" in contract) == ("requestBody" in mine), key


def _properties(
    schema: dict[str, Any], schemas: dict[str, Any]
) -> tuple[set[str], set[str]] | None:
    node = resolve_ref(schema, schemas)
    if "properties" in node:
        return set(node["properties"]), set(node.get("required", []))
    return None


def resolve_ref(node: dict[str, Any], schemas: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        node = schemas[node["$ref"].rsplit("/", 1)[-1]]
    return node


def test_shared_component_schemas_have_the_same_shape() -> None:
    contract = load_contract()["components"]["schemas"]
    mine = generated()["components"]["schemas"]
    compared = 0
    for name, schema in contract.items():
        if name not in mine or "properties" not in schema:
            continue
        expected = _properties(schema, contract)
        actual = _properties(mine[name], mine)
        assert expected is not None
        assert actual is not None
        assert actual[0] == expected[0], f"{name}: propiedades distintas"
        # FastAPI marca como no requeridos los campos con valor por defecto
        assert actual[1] <= expected[1] or name == "Problem", f"{name}: required distinto"
        compared += 1
    assert compared >= 80


def test_request_bodies_reference_the_contract_schema_names() -> None:
    mine = operations(generated(), prefix=PREFIX)
    for key, contract_op in CONTRACT_OPS.items():
        if "requestBody" not in contract_op:
            continue
        expected = contract_op["requestBody"]["content"]["application/json"]["schema"]
        actual = mine[key]["requestBody"]["content"]["application/json"]["schema"]
        if "$ref" in expected and "$ref" in actual:
            assert actual["$ref"].rsplit("/", 1)[-1] == expected["$ref"].rsplit("/", 1)[-1], key


def test_paths_use_contract_prefix() -> None:
    assert load_contract()["servers"][0]["url"] == PREFIX
    assert all(p.startswith(PREFIX) for p in generated()["paths"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", generated()["info"]["version"])
    assert generated()["info"]["version"] == load_contract()["info"]["version"]
    _ = resolve

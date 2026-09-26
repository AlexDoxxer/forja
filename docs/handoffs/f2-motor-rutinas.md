# Handoff · Fase 2 · motor-rutinas

## Resumen
Adaptación al contrato 1.1.0 (CC-0003) y arreglo del caso principiante sin material.
`ENGINE_VERSION` sube a **0.1.1** porque cambia la salida de los snapshots golden.

## Ficheros tocados
- `engine/forja_engine/models.py`: `PlanWarningCode` + `EXCLUDED_EXERCISE`, `AVOIDED_EXERCISE`, `UNKNOWN_EXERCISE` (igual que `contracts/openapi.yaml`).
- `engine/forja_engine/ops.py`: `_exercise_violations` emite los códigos nuevos (id inexistente, excluido, evitado por músculo/patrón).
- `engine/forja_engine/select.py`: `Selector._unsafe_for_beginner` descarta pino y empuje vertical con peso corporal de dificultad ≥ 3 para principiantes.
- `engine/forja_engine/version.py`, `engine/pyproject.toml`, `engine/uv.lock`: versión 0.1.1.
- `engine/tests/test_ops.py`, `engine/tests/test_edges.py`, `engine/tests/golden/*.json` (+ `06-*.md`): tests y snapshots.

## Decisiones (y ADRs)
- Sin ADR nuevo. El principiante nunca recibe pino: la cadena de relajación baja a `pattern_affinity` (empuje horizontal, p. ej. flexión) con aviso `slot_relaxed` ya existente. Si no hubiera ninguno, el hueco se descarta con aviso, sin excepción.
- Los snapshots 01-12 solo cambian en `engine_version`; el único cambio de contenido es el 06 (principiante, peso corporal).
- `avoided_muscle_substituted` se conserva en la generación (sustitución de hueco); solo `validate_plan` usa los códigos nuevos.

## Cómo verificar (comandos exactos)
```
cd engine && uv run pytest -k "not combinations"
cd engine && uv run pytest            # incluye las 1.890 combinaciones
cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy --strict forja_engine tests
```

## Métricas
Cobertura 100 % líneas y 100 % ramas (`--cov-branch`). Test de contrato de enumeraciones en verde.

## Riesgos/pendientes
- El snapshot 06 cambió: los programas ya generados con 0.1.0 conservan su `generator_version`.
- El listado de candidatos para principiantes ya no incluye pino aunque falten alternativas.

## Peticiones a otros agentes
- backend-api: el `engine` cambia de versión a 0.1.1; ejecutar `uv lock --project backend` para refrescar la dependencia local y, si la persiste, actualizar cualquier constante de `generator_version` en sus tests.

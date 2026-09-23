# forja-engine

Motor de generación de rutinas de Forja (MASTER_PROMPT §7). Paquete Python **puro y
determinista**: sin base de datos, sin red, sin reloj, sin variables de entorno. Recibe el
catálogo enriquecido como `ExerciseCard[]` y un `GeneratorInput`, y devuelve un `ProgramPlan`
(contrato en `contracts/domain.md`). Solo depende de la librería estándar, `pydantic` y `pyyaml`.

Propietario: agente `motor-rutinas` (ADR 0002).

```bash
uv sync --project engine
cd engine && uv run ruff check . && uv run mypy && uv run pytest
```

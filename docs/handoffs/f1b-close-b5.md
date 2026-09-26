# Handoff · F1b-CLOSE-B5 · motor-rutinas

Rama `f1b/close-b5` (sin fusionar). ENGINE_VERSION 0.2.1.

## 1. Resumen
Cierra la fuga de B5 (`0720` side-to-side chin con `bodyweight`/`home_bands`) y las
notas baratas de la revisión: bloque de brazos limitado, texto para principiantes, `0970`
fuera de `home_dumbbells` y `0017` fuera de los main de fuerza avanzada.

## 2. Ficheros tocados
- `specs/engine-rules.yaml`: `fixture_gated` (+`0720`, «side-to-side chin»), `bar_gated`,
  `advanced_strength_main_excluded_ids`, `arms_block`, `general_fitness_elbow_extension`.
- `engine/forja_engine/{tables,split,select,volume,version}.py`, `engine/pyproject.toml`, `engine/uv.lock`.
- `engine/tests/test_f1b_fixes.py` (tests nuevos), `engine/tests/golden/*.json` regenerados.

## 3. Decisiones
- Bloque de brazos (énfasis `arms`): solo hypertrophy/toning y no principiantes.
- general_fitness: la extensión de codo del bloque de énfasis pasa a prioridad 3 (la más
  baja) y se omite desde 5 días. NO se pudo usar prioridad 4: `SlotRef.priority` está limitado a 1-3 por
  contrato (`domain.md`, `openapi.yaml`); cambiarlo exigiría un CC.
- Principiantes con énfasis: frase añadida a `rationale_es` («el énfasis se aplica con la
  elección de ejercicios, no con series extra»). No se toca el volumen objetivo.
- C7c y C9 omitidos.

## 4. Cómo verificar
`cd engine && uv run pytest` (suite completa) y `FORJA_UPDATE_GOLDEN=1 uv run pytest tests/test_golden.py --no-cov` para regenerar.

## 5. Estado por hallazgo
B5 cerrado (test de catálogo completo para bodyweight y home_bands); (a), (b), (c), (d) hechos.

## 6. Métricas
Suite completa: 2135 passed, cobertura 100 %; mypy y ruff limpios.

## 7. Riesgos, pendientes y peticiones
- Orquestador: ejecutar `uv lock --project backend` (pin de forja-engine 0.2.1).
- Prioridad 4 requeriría ampliar el contrato de `SlotRef.priority`.

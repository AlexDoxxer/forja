# Handoff · F1b-FIX-2 · motor-rutinas

## 1. Resumen
Con el catálogo regenerado, `test_full_gym_main_squat_and_hinge_use_real_lifts` fallaba: el
avanzado 5 días elegía `1760` (goblet, mancuerna, staple) como sentadilla principal. Se añade una
bonificación de puntuación para barra/barra hexagonal/máquina/smith en slots `main` de sentadilla
y bisagra (B1, ADR 0012). Rama `f1b/fix-engine-2`.

## 2. Ficheros tocados
- `specs/engine-rules.yaml`: `scoring.lower_main_barbell_or_machine: 20` y
  `lower_main_preferred_equipment: [barbell, trap_bar, machine, smith]`.
- `engine/forja_engine/tables.py` (campos nuevos), `engine/forja_engine/select.py`
  (`LOWER_MAIN_PATTERNS`, `_main_equipment_bonus(card, slot)`).
- `engine/tests/golden/*` (12 perfiles, `.json` y `.md`) regenerados.

## 3. Decisiones
- Bonificación (no exclusión dura) para no dejar slots vacíos sin barra/máquina; aplica a todos
  los niveles y objetivos (no solo fuerza). Valor 20 > `loadable_in_main` 10 + staple 15 de goblet.
- No se tocó `specs/overrides/` (ingesta).

## 4. Cómo verificar
`cd engine && uv run pytest -q` · `uv run ruff check . && uv run ruff format --check .` ·
`uv run mypy --strict forja_engine tests`.

## 5. Estado
Suite completa: 2127 passed, cobertura 100 % líneas / ramas, ruff y mypy limpios.
`test_benchmark` (p95 < 150 ms) falló una vez dentro de la suite completa (184 ms) con la máquina
cargada (load ~5) y pasa aislado; es ruido de entorno, no de este cambio.

## 6. Volumen de brazos con énfasis `arms` (revisión §7)
Ningún golden usa `emphasis=arms`, se midió con los mismos perfiles vía `generate`
(series planificadas vs punto medio del objetivo ya multiplicado x1,5):
| perfil | sin énfasis | con énfasis | objetivo | desviación al medio |
|---|---|---|---|---|
| intermedio 4d hipertrofia | 13,5 | 16,0 | 12-21 | -3 % (ok) |
| avanzado 5d hipertrofia | 15,3 | 21,4 | 15-24 | +10 % (ok) |
| intermedio 4d general_fitness | 10,3 | 17,0 | 6-12 | +89 % (fuera) |
| avanzado 5d general_fitness | 12,4 | 24,1 | 9-15 | +100 % (fuera) |
| principiante 3d (ambos) | 10,1 / 9,1 | sin cambio | — | sin efecto |
Hipertrofia intermedio/avanzado está dentro de ±15 %; general_fitness sobrepasa mucho y el
principiante no responde al énfasis. No es un arreglo de tabla simple: no se persigue aquí.

## 7. Pendiente
- Revisar el reparto de brazos con énfasis en general_fitness y principiante (motor/experto).

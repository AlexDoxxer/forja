# Handoff · f1b-close-nutrition · motor-nutricion

Rama `f1b/close-nutrition` (sin fusionar). `forja_nutrition` 0.2.0 -> 0.2.1.

## 1. Qué se hizo
- N1: el suelo de grasa de 0,8 g/kg usa el mismo peso ajustado que la proteína (`min(peso, peso a IMC 27)`) en `energy.py`; `macros.py` no cambia de firma.
- `meal_slots: []` en `sesamo` y `apio` (`data/foods.json`); `mostaza` ya lo tenía.
- N3: `planner._build_day_meals` penaliza (+4 usos virtuales) los alimentos ya usados en el día; es un peso blando, no excluye.

## 2. Resultados
- Sweep 288: 0 días > 35 % grasa (máx. 34,9 %), 0 alérgenos, 0 sobre máx./bajo 30 %, `tolerance_not_met` 4,2 % (antes 4,5 %).
- Días con un alimento repetido: 47 % -> 3,2 %.
- Varón 108 kg IMC 34 en déficit: grasa <= 35 % y suelo sobre 68 g (test).

## 3. Tests
227 pasan (`-m "not slow"`), 100 % líneas y ramas, ruff y mypy --strict limpios; sweep lento pasado. Nuevos: N1 (energy), sesamo/apio/mostaza nunca seleccionados, repetición < 30 %. La propiedad de suelos ahora usa el peso ajustado.

## 4. Goldens
Regenerados (6) con `UPDATE_GOLDEN=1`; `nutrition_version` 0.2.1.

## 5. Specs
`specs/nutrition.yaml` sin cambios (la copia empaquetada sigue idéntica byte a byte). Sin cambios en `contracts/`.

## 6. Petición al orquestador
Ejecutar `uv lock --project backend` (versión de nutrición 0.2.1).

## 7. Pendiente / notas
El barrido de 288 no incluye obesidad; la cobertura de N1 es el test unitario. Faltan la nota de UI de alérgenos no filtrables (frontend-ui) y el CC v1.1 (arquitecto).

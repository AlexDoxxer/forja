# Handoff · Fase 1b FIX · motor-nutricion

Rama: `f1b/fix-motor-nutricion` (sin fusionar). Zona escrita: `nutrition/**`, `specs/nutrition.yaml`
(fuente, ADR 0011), `docs/CONTRACT_CHANGES.md` (CC-0004 propuesto) y este handoff.

## Resumen

Se aplican los hallazgos B6, B7, C12, C13, C14, C15 y la decisión 5 de
`docs/reviews/f1b-experto-entrenamiento.md`. La tolerancia del contrato no se sube. Versión del motor
y del paquete `0.2.0`; snapshots regenerados.

| Hallazgo | Estado | Evidencia |
|---|---|---|
| B6 alérgenos | hecho | `avena`, `cuscus`, `cerveza` con `gluten`; `leche_almendra` con `tree_nuts` y rol `carb`; `cacahuete`, `mantequilla_cacahuete`, `altramuz` con `peanuts` + `tree_nuts`; `aceite_coco` con `tree_nuts`. Tests de auditoría en `tests/test_foods.py`; barrido: 0 violaciones de alérgeno |
| B7 porciones e idoneidad | hecho | `max_portion_g` y `meal_slots` en los 193 alimentos; ítems < 30 % de la porción típica eliminados; barrido: 0 ítems sobre `max_portion_g`, 0 bajo el 30 %, 0 desayunos con legumbre/pescado/carne guisada |
| C12 grasas y procesados | hecho | aceite de oliva x4, coco/girasol x0,25; `weekly_max` (procesados 2, hígado 1); topes anchoa 30 g, hígado 100 g |
| C13 tono y frecuencia del aviso | hecho | texto neutro; `tolerance_not_met` en 13/288 planes (4,5 %) |
| C14 proteína en obesidad | hecho | IMC >= 30 usa min(peso, peso a IMC 27); tope 220 g/día (`specs/nutrition.yaml`) |
| C15 catálogo | hecho parcial | `macro_role` de `leche_almendra`; `sesamo`, `mostaza`, `apio` siguen sin valor de `Allergen` (no filtrables: petición a backend/frontend) |
| Decisión 5 | hecho | techo duro 35 %: 0 días por encima; sobrepaso de grasa x2 (x3 en reintento); ítem de grasa opcional (>= 70 % cubierto); aviso solo por kcal, proteína o techo |

Barrido de 288 perfiles (`scripts/sweep.py`, 2.016 días): grasa > 35 % kcal 0 días (máx. 33,8 %);
`tolerance_not_met` 13/288 = 4,5 % (objetivo <= 25 %); días veganos con desviación de grasa > +20 %:
0/504. Antes (según la revisión): 7,6 % de días > 35 % y 286/288 avisos.

## Ficheros tocados

`nutrition/forja_nutrition/{__init__,energy,macros,models,planner,swap,tables}.py`,
`data/{foods.json,nutrition.yaml}`, `nutrition/scripts/{__init__,sweep}.py`,
`nutrition/tests/{test_foods,test_models,test_planner,test_properties,test_swap,test_tables,test_energy,test_macros,test_realism}.py`,
`tests/golden/*.json`, `nutrition/pyproject.toml`, `nutrition/uv.lock`, `specs/nutrition.yaml`,
`docs/CONTRACT_CHANGES.md`.

## Decisiones

- `specs/nutrition.yaml` es la fuente (ADR 0011) y `data/nutrition.yaml` es copia idéntica (`cp`).
  Claves nuevas: `fat.max_pct_kcal: 0.35`, `tolerances.fat_over_allowed: 0.20` (informativa),
  `protein_bodyweight_basis`, `protein_max_g_per_day: 220`.
- El techo de grasa es `max(35 % kcal, objetivo de grasa)`: el suelo de seguridad de grasa
  (0,8 g/kg) prevalece en personas muy pesadas.
- Planificador: filas del solver normalizadas por objetivo e importancia (kcal y proteína pesan más);
  `bvls` en lugar de `trf` (9x más rápido); pulido a nivel de día con los mismos alimentos;
  hasta 10 intentos de selección por día (40 si hay exceso de grasa) y recorte final de grasa
  (`trim_fat`) que garantiza el techo mientras haya ítems recortables. Los alimentos proteicos densos se
  eligen más a menudo; los no grasos con mucha grasa (tofu, tempeh, embutidos) menos.
- `meal_slots` vacío = no se selecciona solo (condimentos, bebidas, leche condensada, harinas, yema);
  `swap` prefiere sustitutos aptos para la comida y respeta `max_portion_g`.
- `cacahuete` y derivados llevan `peanuts` (CC-0002 aprobado) y `tree_nuts` por precaución: el
  perfil «alergia a frutos secos» nunca recibe cacahuete.
- No se emite ningún aviso `info` por desviación de grasa (no existe código en el contrato); la
  desviación sigue visible en `MacroDeviation`.
- S6 (texto de `energy_note`) no se ha tocado.

## Cómo verificar

```
cd nutrition && uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -m "not slow"            # 224 tests, 100 % líneas y ramas
uv run pytest -m slow --no-cov         # barrido completo de 288 perfiles (~15 s)
uv run python -m scripts.sweep         # métricas en JSON
```

## Métricas

224 tests en verde (modo rápido), cobertura 100 % líneas y 100 % ramas; ruff y mypy --strict sin
errores. Sweep rápido de 48 perfiles dentro del modo rápido; el completo es `slow`.

## Riesgos y pendientes

- Los perfiles del barrido (4 cuerpos: 52/60/80/95 kg) son mi reconstrucción de la revisión; el
  revisor puede repetirlo con los suyos. Casos extremos (3 comidas con > 4.000 kcal o 1.200 kcal)
  siguen fallando algún día y emiten `tolerance_not_met`, como debe ser.
- El planificador tarda ~0,05 s por plan; los tests de propiedad son más lentos que antes.
- `Food` gana campos y la regla de `tolerance_not_met` cambia respecto a `contracts/domain.md` §6.2:
  propuesto como CC-0004 (no se ha tocado `contracts/`).
- Los planes guardados con `foods_hash` o `nutrition_version` anteriores no coinciden (esperado).

## Peticiones a otros agentes

- backend-api: ejecutar `uv lock --project backend` (versión del paquete `forja-nutrition` 0.2.0); si
  expone `Food`, decidir sobre los campos nuevos según CC-0004.
- arquitecto: resolver CC-0004.
- frontend-ui: texto de `tolerance_not_met` (C13) y aviso «no filtrable» para sésamo, mostaza y apio.

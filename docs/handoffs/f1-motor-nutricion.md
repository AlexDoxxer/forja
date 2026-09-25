# Handoff · Fase 1 · motor-nutricion

Rama: `f1/motor-nutricion` (desde `main` con `contracts-v1`, sin fusionar). Fecha: 2026-09-25.
Zona escrita: `nutrition/**` + este handoff, `docs/TASKS.md` (filas F1-NUT) y una propuesta en
`docs/CONTRACT_CHANGES.md` (CC-0001). No se han tocado `specs/`, `contracts/` ni otros paquetes.

## Resumen

Paquete `forja_nutrition` completo según MASTER_PROMPT §8 y `contracts/domain.md` §6:

- **`energy.py`**: TMB Mifflin-St Jeor (hombre/mujer/media para `unspecified`), GET con ajuste por
  días de entreno (tope 1,9), ajuste por objetivo/ritmo con tope de déficit de 500 kcal y la
  función pública `calculate_target`.
- **`macros.py`**: proteína por objetivo con recorte a [1,6; 2,2] g/kg, grasa (≥ 0,8 g/kg y ≥ 20 %
  kcal), carbohidratos como resto exacto, fibra 14 g/1000 kcal.
- **`safety.py`**: bloqueos tipados (`NutritionBlock`: menor de 18, embarazo, lactancia), IMC < 18,5
  con `lose` ⇒ `maintain`, suelo de kcal `max(TMB, 1200/1500/1350)`.
- **`foods.py` + `data/foods.json`**: 193 alimentos (USDA FoodData Central SR Legacy 2018-04, consulta
  2026-09-23) con `fdc_id` real, nombre ES, categoría, dietas, alérgenos, porción y unidad.
- **`planner.py`**: `plan_week` (7 días, 3-5 comidas): plantilla mediterránea (proteína + hidrato +
  verdura/fruta + grasa), selección sembrada con penalización de repetición semanal y de
  «no me gusta», gramos por `scipy.optimize.lsq_linear` acotado, redondeo (5 g o unidades),
  realimentación del error de redondeo a las comidas siguientes del día y re-verificación de
  tolerancias (±5 % kcal / ±10 % macros, o aviso `tolerance_not_met`).
- **`shopping.py`**: lista de la compra agregada por categoría en orden de `FoodCategory`.
- **`swap.py`**: intercambio dentro de la misma categoría, dieta/alérgenos/exclusiones respetados,
  gramos reescalados a las kcal del alimento sustituido, totales del día recalculados.
- **`models.py`/`tables.py`/`seeding.py`**: DTOs del contrato (frozen, `extra="forbid"`), carga
  validada de `nutrition.yaml` y semilla derivada (SHA-256 del JSON canónico de la entrada).

API pública (`import forja_nutrition`): `calculate_target`, `plan_week`, `swap_food`,
`shopping_list`, `load_foods`, con las firmas de `domain.md` §6.3.

## Ficheros tocados

```
nutrition/forja_nutrition/{__init__,models,tables,energy,macros,safety,foods,seeding,planner,shopping,swap}.py
nutrition/forja_nutrition/data/{foods.json,foods_sources.md,nutrition.yaml}
nutrition/tests/{conftest,test_models,test_tables,test_foods,test_macros,test_safety,test_energy,
                 test_seeding,test_planner,test_shopping,test_swap,test_properties,test_snapshots}.py
nutrition/tests/golden/*.json   (6 snapshots)
docs/handoffs/f1-motor-nutricion.md  docs/TASKS.md (F1-NUT-01…10 → hecha)
docs/CONTRACT_CHANGES.md (CC-0001)
```

## Decisiones (y ADRs)

No se necesitan ADRs nuevos; decisiones de implementación (ninguna cambia el contrato):

1. **`nutrition.yaml` empaquetado**: ADR 0005 limita la E/S a ficheros empaquetados y la tarea
   pedía escribir solo en `nutrition/`, así que el motor lee `forja_nutrition/data/nutrition.yaml`,
   copia exacta de `specs/nutrition.yaml` (versión 1). **Riesgo de deriva** (ver abajo). Las claves
   `3/4/5` de `meal_templates`/`meal_kcal_split` son enteros en YAML y se validan como `int`.
2. **Fórmula de TMB fija por sexo** (`male`/`female`/media), coherente con
   `specs/sex-modifiers.yaml#bmr_formula`, sin leer ese fichero (es de `motor-rutinas`).
3. **Suelos de proteína/grasa y kcal**: si `proteína + grasa` mínimas superaran las kcal
   objetivo (p. ej. 400 kg), las kcal suben hasta cubrirlas (punto fijo en
   `macros.resolve_energy_and_fat`) y se añade `kcal_floor_applied`; así los carbohidratos nunca
   son negativos y `4P+4C+9G == kcal` exactamente (contrato: ±2 %).
4. **`fat_floor_applied`** se emite cuando manda el suelo del 20 % de kcal (no el de g/kg); es
   frecuente en perfiles normales. `protein_clamped` está implementado pero la tabla real nunca lo
   dispara (todos los valores caen dentro de [min, max]).
5. **`unit_foods` de la tabla**: la unidad se decide por alimento (`Food.unit_grams`), no por la
   lista genérica de `rounding.unit_foods` (huevo, plátano, manzana, naranja, yogur, rebanada de
   pan, más kiwi, mandarina, bagel, muffin, tortitas, pita).
6. **Pesos crudos/secos**: legumbres, arroz, pasta, avena, harinas… usan el valor seco/crudo de USDA
   (coherente con una lista de la compra de ingredientes); el motor no modela mermas de cocción.
7. **`condiments` y `beverages`** están en el catálogo (y son intercambiables entre sí) pero el
   planificador no los elige (evita p. ej. cerveza como «hidrato»). `swap_food` tampoco propone
   sustitutos de esas categorías.
8. **Error explícito** (`ValueError`) si dieta + alérgenos + exclusiones dejan **cero** alimentos
   elegibles o `swap_food` no encuentra sustituto: no es un bloqueo de seguridad del contrato
   (`NutritionBlockReason` no lo cubre). Con frutas/verduras (sin alérgenos, aptas para las 4
   dietas) esto solo pasaría excluyéndolas todas.
9. **`energy_note`**: 39 de 193 alimentos superan el 12 % de `|kcal − (4P+4C+9G)|`: 2 por alcohol
   (cerveza, vino), 3 por fibra alta y el resto verduras/frutas de baja densidad calórica, donde USDA
   usa factores de Atwater específicos. Detalle en `data/foods_sources.md`.
10. **Cacahuete**: no es `tree_nuts` (es legumbre) y `Allergen` no tiene valor propio ⇒ propuesta
    **CC-0001** (`peanuts`). Mientras tanto se evita con `excluded_food_ids`.
11. La semilla derivada usa SHA-256 del JSON canónico de la entrada sin `seed`; el PRNG es
    `random.Random(seed)` consumido en orden fijo (día → comida → rol).

## Cómo verificar

```bash
export PATH=$HOME/.local/bin:$PATH
make lint-python lint-placeholders typecheck-python test-nutrition     # desde la raíz del worktree
# o solo el paquete:
cd nutrition && uv run ruff check . && uv run ruff format --check . && uv run mypy \
  && uv run pytest -m "not slow"
# regenerar snapshots tras un cambio intencionado (subir NUTRITION_VERSION y revisar el diff):
cd nutrition && UPDATE_GOLDEN=1 uv run pytest tests/test_snapshots.py
```

Resultados obtenidos: `make lint-python lint-placeholders typecheck-python test-nutrition` en verde;
`coverage_gate`: líneas 100 %, ramas 100 % (mín. 100 / 95).

## Métricas

| Concepto | Valor |
|---|---|
| Tests | 189 (≈ 23 s), incluidas 10 propiedades Hypothesis y 7 de snapshots |
| Cobertura | 100 % líneas, 100 % ramas (770 sentencias, 174 ramas) |
| mypy `--strict` / ruff | 0 errores (26 ficheros) |
| Alimentos | 193 en 14 categorías, 4 dietas, 0 ids duplicados, 100 % con `fdc_id` |
| Coherencia kcal↔macros | 0 alimentos fuera del 12 % sin `energy_note` (test) |
| Propiedades §8.6 | suelos siempre respetados; macros = kcal (0 % de diferencia); ningún excluido/alérgeno/fuera de dieta (plan y swap); reproducible con semilla |
| Bloqueos §8.5 probados | menor de 18, embarazo, lactancia, IMC < 18,5 + `lose`, suelo de kcal |
| Desviación diaria | típicamente ±0–5 % kcal y ±0–15 % macros (aviso si se excede) |

## Riesgos/pendientes

1. **Deriva `specs/nutrition.yaml` ↔ `data/nutrition.yaml`**: hay dos copias. Un test futuro o un
   paso de build debería compararlas (petición abajo).
2. **Tolerancias**: con ≈ 200 alimentos y 3-4 por comida, algunos días (sobre todo dietas
   restringidas: vegana sin frutos secos) superan ±10 % en grasa; se señala con
   `tolerance_not_met`, según contrato. Calidad culinaria mejorable (p. ej. raciones grandes de
   verdura en meriendas); el experto debe revisar planes (F1b-EXP-06).
3. **Datos de alimentos**: alérgenos y dietas se etiquetaron por composición genérica, no por
   marca; margarina se trata como no vegana por precaución. Requiere revisión del experto.
4. Alimentos de USDA en inglés traducidos a mano (nombres ES); sin «paella», «tortilla de patata»,
   etc. (no hay recetas, solo ingredientes).
5. El motor lanza `ValueError` si no queda ningún alimento elegible (decisión 8).
6. El sustituto automático de `swap_food` es reproducible entre procesos (semilla SHA-256 de
   plan, día, comida y alimento; test con valor fijado). Cambiar esa fórmula altera la salida ⇒
   subir `NUTRITION_VERSION`.

## Peticiones a otros agentes

- **arquitecto**: resolver CC-0001 (`peanuts`); valorar añadir un test que compare
  `specs/nutrition.yaml` con `nutrition/forja_nutrition/data/nutrition.yaml`, o decidir que la
  fuente única sea el fichero empaquetado.
- **experto-entrenamiento** (F1b-EXP-06): revisar planes de ejemplo, suelos, etiquetas de alérgenos/
  dietas y `energy_note`.
- **backend-api**: calcular `age_years` y `missing_profile_data` antes de llamar al motor (el motor
  nunca emite ese bloqueo porque `NutritionInput` exige los datos); `week_start` debe ser lunes;
  cachear `load_foods()` no hace falta (memoizado); `foods_hash` identifica el snapshot de alimentos.
- **frontend-ui**: mostrar `notices` con tono neutro; `tolerance_not_met` no es un error.

## Planes de ejemplo (semana del 2026-09-28, primeros 2 días)

**Perfil A — mujer, 29 años, 166 cm, 60 kg, actividad ligera + 3 días de entreno, mantener
(ritmo suave), vegana, alergia a frutos secos, 4 comidas.**
BMR 1332 · GET 1964 (×1,475) · objetivo 1964 kcal · P 108 g · G 48 g · HC 275 g · fibra 27 g.
Avisos: descargo de salud, `tolerance_not_met`.

| Día 1 (2050 kcal, +4,4 %) | |
|---|---|
| Desayuno (498) | Tofu sedoso 290 g, arroz blanco 80 g, pipas de girasol 5 g |
| Comida (806) | Alubia pinta (seca) 155 g, muffin inglés 1 ud, aceite de coco 15 g |
| Merienda (172) | Guisante partido (seco) 35 g, aceite de coco 5 g |
| Cena (574) | Alubia blanca (seca) 110 g, pan integral 1 rebanada, aceite de canola 15 g |

| Día 2 (2050 kcal, +4,4 %) | |
|---|---|
| Desayuno (594) | Alubia pinta (seca) 105 g, pan blanco 1 rebanada, mantequilla de cacahuete 25 g |
| Comida (621) | Alubia negra (seca) 85 g, espárrago 320 g, semilla de chía 55 g |
| Merienda (193) | Maíz dulce 5 g, brócoli 320 g, semilla de lino 15 g |
| Cena (642) | Alubia roja (seca) 120 g, tortita de maíz 1 ud, sésamo 30 g |

(Sin ningún fruto seco de árbol en los 7 días; el cacahuete no lo es. Lista de la compra:
`shopping_list(plan)`.)

**Perfil B — mujer, 45 años, 155 cm, 52 kg, sedentaria, pérdida (`lose`), omnívora, 4 comidas
(cerca del suelo).** BMR 1103 · GET 1323 · −15 % daría 1125 kcal ⇒ **suelo de 1200 kcal**
(`kcal_floor_applied`) · P 109 g · G 42 g · HC 97 g · fibra 17 g.

| Día 1 (1199 kcal, −0,1 %) | |
|---|---|
| Desayuno (272) | Yogur natural desnatado 3 ud, nuez de macadamia 5 g |
| Comida (513) | Lenteja (seca) 60 g, tortita de trigo 1 ud, coco (pulpa) 60 g |
| Merienda (101) | Leche semidesnatada 145 g, cacahuete 5 g |
| Cena (314) | Filete de ternera 280 g |

| Día 2 (1171 kcal, −2,4 %) | |
|---|---|
| Desayuno (302) | Requesón 160 g, endibia 480 g |
| Comida (402) | Salmón 185 g, arroz blanco 25 g, mandarina 1 ud |
| Merienda (144) | Yogur griego natural desnatado 1 ud, bulgur 10 g, nuez de macadamia 5 g |
| Cena (323) | Anchoa en aceite 90 g, muffin inglés 1 ud |

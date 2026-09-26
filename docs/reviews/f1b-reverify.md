# Gate 1 · Re-revisión de dominio (experto-entrenamiento)

Rama `f1b/reverify` sobre `main` (contiene f1b/fix-ingesta, fix-motor-rutinas, fix-engine-2 y
fix-motor-nutricion). Informe original: `docs/reviews/f1b-experto-entrenamiento.md` (§7).
Modo rápido: sin suites completas; se leyeron los 12 goldens (`engine/tests/golden/*.json|md`), el
fixture `engine/tests/fixtures/catalog.json` y los specs, se auditaron los goldens con un script
propio (dificultad, ids vetados, fixture_gated, series, ondulación) y se ejecutaron dos barridos de
nutrición: el `nutrition/scripts/sweep.py` del autor (288 perfiles) y uno propio de 384 planes
(cuerpos 48/66/70/108 kg, alérgenos peanuts+tree_nuts, lactose+egg, fish+shellfish+gluten, 4 dietas,
3 objetivos, 3 y 5 comidas; semillas 5001+). Nada de la salida se ha commiteado.

## Veredicto: Puerta 1 = FAIL (1 BLOQUEANTE abierto: B5, corrección de una línea)

| ID | Veredicto | Evidencia |
|---|---|---|
| B1 | CERRADO | Goldens 02/03/10/11: sentadilla principal = `0042`/`0043` (barra), bisagra = `0085`/`0811`/`0032`/`0117`; ningún `1760`, `3533`, `0044` como principal en `full_gym`. `1760` solo aparece en `home_dumbbells` (01) y `custom` sin barra (12), `3533` solo en peso corporal (06, 08): correcto. Cuádriceps 03 = 14 (rango 14-20). |
| B2 | CERRADO (parte series) | Todas las series de principal ≤ `prescription.max`: hipertrofia 3-4, fuerza 4-5, toning/general 3, resistencia 2; principiantes (01, 06, 09) en el mínimo exacto. +1 serie solo en 05 desde la semana 3 (6 series en `0043`/`0091`, avanzado). El déficit de volumen se avisa (ver CAMBIO-V). |
| B3 | CERRADO | Cero ejercicios d3 en principiante/intermedio en las 5-6 semanas de los 12 planes; sin `0471`, `3302`, `1759`, `0535`. Staples 136. |
| B4 | CERRADO | 04/05: heavy day 3-5 y 3-6 reps, medium 4-7; `0044` fuera; RIR ≥ 2 en la intermedia salvo el último accesorio de intensificación (`3562` RIR 1, semana 4; aceptable); descarga 2-3 series RIR 4. |
| B5 | **ABIERTO** | `fixture_gated` funciona para 61 de 62 casos (0 dominadas/fondos/anillas/`2400` en 06, 07, 08). Fuga: `0720` «side-to-side chin» (`equipment_code: bodyweight`, d2, no staple) queda como `vertical_pull` principal en **06 (días 2 y 3, 2-3 × 8-12, principiante)** y **08 (días 2 y 3, 2 × 15-25)**: exige barra y es una dominada lateral. La lista `name_en_any` solo casa «chin-up»/«chin up», no «chin». Un barrido del catálogo (`equipment_group` bodyweight/band, `vertical_pull\|vertical_push`, d ≤ 2, no gated) devuelve únicamente `0720`. Además no hay aviso «sin barra de dominadas» porque el slot no se relaja. |
| B6 | CERRADO | `avena`, `cuscus`, `cerveza` = gluten; `leche_almendra` = tree_nuts y rol carb; `cacahuete`, `mantequilla_cacahuete`, `altramuz` = peanuts+tree_nuts; `aceite_coco` = tree_nuts. Auditoría propia por palabra clave sobre 193 alimentos: 0 omisiones reales. Ambos barridos: 0 violaciones de alérgeno. |
| B7 | CERRADO | Sweep del autor (288): 0 días > 35 % grasa (máx. 33,8 %), tolerance_not_met 4,5 %, 0 desayunos con legumbre/pescado/carne guisada, 0 ítems sobre `max_portion_g` o bajo el 30 %, 193/193 alimentos con `max_portion_g`. Mi barrido (384): tolerance_not_met 1,8 %, 0 ítems sobre máx, 0 bajo 30 %, 0 desayunos malos, 0 alérgenos. Ver CAMBIO-N1 (grasa > 35 % en obesidad) y (b). |
| B8 | CERRADO | Ningún «behind neck/head», «upright row» ni «rear pull» en las semanas de los 12 planes, calentamiento incluido; `low_quality_ids` excluye `0100`, `0543`, `0777`. |

Criterios §7 comprobados: (1a) dificultad OK; (1b) sin skill_gated ni contraindicated; (1c) sets OK;
(1d) OK; (1e) heavy ≥ 3 reps y `excluded_ids` OK; `ENGINE_VERSION` 0.2.0. (3) ingesta: 136 staples,
celdas exentas documentadas. (4) nutrición: cumplido en ambos barridos salvo CAMBIO-N1.

### Corrección exacta de B5 (motor-rutinas, `specs/engine-rules.yaml`)

```diff
 fixture_gated:
   presets: [bodyweight, home_bands]
-  ids: ["2400"]
+  ids: ["2400", "0720"]
```

Añadir también `"side-to-side chin"` a `name_en_any` (misma sección) y un test de catálogo: para
`bodyweight` y `home_bands`, ningún candidato de `vertical_pull` ni `vertical_push` con d ≤ 2 casa una
palabra de la lista gated. Regenerar goldens 06 y 08 (esperado: `vertical_pull` cae a `horizontal_pull`
con `slot_relaxed` «Sin barra de dominadas: hemos usado remos.»). Re-comprobación: 0 apariciones de
`0720` en 06/08. Con eso B5 pasa a CERRADO y la Puerta 1 a PASS sin más cambios.

## Notas abiertas del handoff

### (a) general_fitness con énfasis brazos (+89 % / +100 %) y principiantes que ignoran el énfasis: CAMBIO (no BLOQUEANTE)

- No es un riesgo de seguridad ni rompe la prescripción: las series por ejercicio respetan la tabla
  (B2) y `volume_out_of_range` se emite. El sobrepaso viene de la línea base: el golden 11 sin énfasis
  ya da brazos 17,6 vs 4-8 y el 03 (hipertrofia, sin énfasis) 22,8 vs 10-16. Causa: los días
  push/pull/upper llevan dos accesorios directos de brazos (`elbow_flexion`, `elbow_extension`) y la
  frecuencia alta (6-7 días) los repite 4-6 veces por semana, con objetivo de brazos bajo.
- Principiante ignora el énfasis: coherente con B2 (principiantes en el mínimo del rango, sin subir
  series). Lo que falla es la comunicación: el wizard preselecciona `lower_glutes` para mujeres
  principiantes (golden 01) y el plan no cambia el volumen (glúteos 7,5 vs 12-18).
- Arreglo propuesto para F2 (motor-rutinas, sin cambio de contrato):
  1. `engine-rules.yaml#emphasis_overrides.arms`: limitar el bloque adicional a `goal in {hypertrophy,
     toning}` y a `experience != beginner`.
  2. `split-templates.yaml`: para `general_fitness`, bajar el slot `elbow_extension` de push/pull/upper a
     `priority: 4` (primero en caerse) o eliminarlo cuando `days_per_week >= 5`.
  3. `texts.py`: nueva línea de `rationale_es` para principiantes con énfasis distinto de `balanced`:
     «Como estás empezando, mantenemos las series al mínimo del rango y aplicamos el énfasis con la
     elección y el orden de ejercicios; lo ampliaremos cuando avances de nivel.»
  4. Alternativa de una línea: subir el objetivo de brazos de general_fitness en
     `volume-targets.yaml` de 4-8 a 6-10 (calibración, no evidencia).
- Énfasis de brazos en hipertrofia (intermedio -3 %, avanzado +10 % sobre el punto medio): APROBADO.

### (b) Sésamo, mostaza y apio sin valor de `Allergen`: sin CC para v1; dato + nota de UI

- Estado actual: `mostaza` tiene `meal_slots: []` (nunca se elige sola). `sesamo` (comida/cena, máx.
  15 g) y `apio` (comida/cena, máx. 120 g) sí se seleccionan: en mi barrido de 384 planes (2.688 días)
  aparece sésamo en 356 días (13 %) y apio en 46. Una persona alérgica al sésamo no puede declararlo.
- Decisión: **no hace falta CC para v1**; el enum `Allergen` es aditivo y se amplía en v1.1 (`sesame`,
  `celery`, `mustard`, y si se quiere completar los 14 de la UE, `sulphites`, `lupin`, `mollusc`).
  Para v1:
  1. motor-nutricion (obligatorio antes de publicar, dato de dos líneas): `sesamo` y `apio` con
     `meal_slots: []` (no se seleccionan solos), o retirarlos del `foods.json` v1. Tras el cambio: 0
     apariciones en el barrido.
  2. frontend-ui: nota bajo el selector de alergias: «No podemos filtrar sésamo, apio, mostaza, sulfitos
     ni moluscos. Revisa los ingredientes; si tienes alguna de estas alergias, consulta con tu médico.»
  3. arquitecto: abrir CC aditivo para v1.1 con los valores nuevos.
- Es CAMBIO (con la corrección de dato como condición de lanzamiento), no BLOQUEANTE de la Puerta 1: B6
  trataba etiquetas erróneas y están corregidas.

## CAMBIOS que permanecen (no bloquean la Puerta 1)

| ID | Tema | Propietario | Acción exacta |
|---|---|---|---|
| CAMBIO-V | Volumen (criterio §7.2: ≥ 85 % del mínimo y brazos ±15 %) no se cumple en 10 de 12 goldens. Mejoran 02/09/12 (brazos 13,5 / 5,6 / 22,8, dentro de rango) pero hay déficits por tiempo y plantilla: 01 hombros 3 vs 6-10, gemelos y core 0; 05 glúteos 6,5 vs 10-14; 10 cuádriceps 12 vs 17-24; 11 core 0; 12 glúteos 5,5 vs 9-14; y brazos por encima en 03 (22,8 vs 10-16), 05 (12,3 vs 6-10), 11 (17,6 vs 4-8). Todo se avisa con `volume_out_of_range`. | motor-rutinas | F2: gemelos/core con prioridad no menor que accesorios de brazos en plantillas de ≤ 3 días; un solo accesorio de brazos en push/pull de 6-7 días; ver (a). |
| CAMBIO-N1 | Grasa > 35 % kcal en obesidad: varón 108 kg (IMC 34), déficit, 2.032 kcal: objetivo de grasa 86,4 g = 38,2 % por el suelo de 0,8 g/kg de peso total; 98 combinaciones de día con 35,0-39,2 %. Es la excepción documentada (`max(35 %, objetivo)`), pero 0,8 g/kg de peso total es excesivo en obesidad. | motor-nutricion | Aplicar el mismo peso ajustado que en proteína (min(peso, peso a IMC 27)) al suelo de 0,8 g/kg: 85,5 kg ⇒ 68 g = 30 %. |
| CAMBIO-C7c | Vuelta a la calma no se ajusta a los grupos del día (01 día 1: pecho y cuádriceps). | motor-rutinas | Ordenar por solapamiento con los grupos entrenados. |
| CAMBIO-C9 | Preferencia de remo sobre tirón vertical en circuitos: no aplicada. | motor-rutinas | F2. |
| CAMBIO-C5 | Dominada asistida en máquina (`0017`) como principal de un avanzado de fuerza (05). Aceptable (d1) pero mejor priorizar `0027`/`0198`. | motor-rutinas | Puntuación de barra/polea también para tirón vertical en fuerza. |
| CAMBIO-B5b | `0970` dominada asistida con banda en `home_dumbbells` (01, día 3): requiere anclaje/barra. | arquitecto + motor | CC v1.1 `pullup_bar`/`bench` pendiente; mientras, `"assisted pull-up"` en `fixture_gated` también para `home_dumbbells`. |
| CAMBIO-N3 | Un mismo alimento aparece más de una vez en el mismo día en ~47 % de los días (aceite, pan…). Solo observación. | motor-nutricion | F2: tope de repeticiones por alimento y día. |

## Resumen para el orquestador

Puerta 1: **FAIL** por B5 (una fuga: `0720` en 06 y 08). Fix: `fixture_gated.ids += ["0720"]` en
`specs/engine-rules.yaml`, regenerar goldens 06 y 08. Resto B1-B4, B6-B8: CERRADO. Notas (a) y (b):
CAMBIO; (b) exige el retoque de datos de `sesamo`/`apio` antes de publicar, sin CC en v1.

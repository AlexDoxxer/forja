# Fase 1b · Revisión de dominio (experto-entrenamiento)

> Revisor: `experto-entrenamiento` · Rama `f1b/experto-entrenamiento` · Base: `main` @ `0fbf678`
> (ingesta, motor-rutinas, motor-nutricion y frontend fusionados). Fecha: 2026-09-26.
> Tareas cubiertas: F1b-EXP-01 … 06 en un único informe.
> Método: lectura de specs y handoffs; muestreo aleatorio semillado de 100 ejercicios
> (`random.seed(20260926)`) y de 150 nombres (`seed 7`) sobre `engine/tests/fixtures/catalog.json`;
> lectura completa de los 12 snapshots `engine/tests/golden/*.md`; barrido reproducible del
> planificador de nutrición (288 perfiles × 7 días = 2.016 días-comida; script en «Cómo verificar»
> del handoff) y de los 193 alimentos de `nutrition/forja_nutrition/data/foods.json`.
> No se ha modificado nada fuera de `docs/reviews/` y `docs/handoffs/`.

## 0. Veredicto

**Puerta 1: NO SUPERADA.** 8 BLOQUEANTES abiertos. Ninguno exige rediseño: son correcciones
localizadas (dos en el filtro de selección del motor, una en la tabla de periodización, un grupo de
etiquetas de alérgenos y dos ajustes del planificador de comidas). Con el punto B1 corregido, 10 de
los 12 snapshots cambian de forma sustancial; hay que regenerarlos y re-revisarlos.

| Severidad | Nº | Significado |
|---|---|---|
| BLOQUEANTE | 8 | Seguridad, violación de la spec del MASTER_PROMPT o salida inutilizable. Impide cerrar la fase. |
| CAMBIO | 17 | Debe corregirse antes del cierre de la Fase 1b; no bloquea por sí solo. |
| SUGERENCIA | 8 | Mejora recomendada, sin coste de gate. |

Veredicto por área:

| Área | Veredicto | Resumen |
|---|---|---|
| Enriquecimiento (100 aleatorios) | CAMBIOS | 91/100 correctos; 9 errores o dudas (§5.1) y 3 familias sistemáticas (dificultad de dominadas/fondos, mecánica de press de tríceps, equipamiento «peso corporal» que exige barra o banco). |
| Staples (144) | BLOQUEANTE | 11 staples no deben serlo (B3, B5, C1); la celda `vertical_push × bodyweight` solo se cumple con ejercicios gimnásticos. |
| Nombres ES | CAMBIOS | 0 calcos graves en el muestreo de 150; 1 fuga de texto interno (`1288`), 1 nombre que contradice sus instrucciones (`3234`), 1 clasificación errónea (`0858`); ver §5.3 para los 31 dudosos. |
| Tablas `specs/` | BLOQUEANTE | Periodización de fuerza (B4) y conflicto asignación↔prescripción (B2); resto CAMBIOS/SUGERENCIAS. |
| Snapshots (12) | BLOQUEANTE | 12/12 con al menos un hallazgo; causa raíz mayoritaria: B1 (§5.5). |
| Nutrición | BLOQUEANTE | Etiquetas de alérgenos (B6) y realismo/tolerancias (B7). Fórmulas y suelos de seguridad: APROBADOS. |

## 1. Decisiones sobre los cinco riesgos abiertos

### Riesgo 1 · Principiantes con peso corporal reciben ejercicios de pino

**Decisión: la dificultad deja de ser relajable para principiante e intermedio, y los ejercicios de
habilidad (gimnásticos, olímpicos, balísticos) quedan fuera de la selección automática.**

Causa verificada: en `engine-rules.yaml#relaxation_order` la primera relajación es `difficulty`.
El slot `vertical_push` de un principiante con `bodyweight` solo tiene `0471` (flexión en pino) y
`3302` (pino), ambos dificultad 3, y ambos son *staples* con `role: main`. El motor los elige tras
relajar la dificultad (snapshots 06 y 08: «flexión en pino 2 × 20 s», «pino» en circuito). Peor
aún, `0471` tiene `load_type: time`, de modo que la flexión en pino se prescribe como isométrico de
20 s. El mismo mecanismo produce `0535` cargada colgante con kettlebell (dificultad 3) como bisagra
principal de 5 series en el snapshot 01 (principiante, mujer).

Regla propuesta (exacta):

1. `relaxation_order` pasa a `[staple, target_group, pattern_affinity, difficulty]` y la relajación
   `difficulty` **solo se aplica a `advanced`**, y solo a slots `accessory`. Para `beginner` e
   `intermediate` nunca se supera `difficulty.cap (+ accessory_extra)`. Si tras las otras
   relajaciones no hay candidato, el slot se elimina con `slot_dropped`/`equipment_insufficient`.
2. Nueva clave `skill_gated` en `engine-rules.yaml` (detalle en §6): ejercicios que nunca se
   seleccionan automáticamente, para ningún nivel, salvo que estén en `favorite_exercise_ids`. Incluye
   handstand/pino, flexión en pino, planche, front/back lever, muscle-up, cargadas, arrancadas,
   envión/push press/thruster, pistol, dragon flag, L-sit/V-sit, skin the cat, saltos en profundidad
   y flexiones con palmada.
3. Ingesta: `0471` y `3302` pasan a `is_staple: false`, `role: accessory`; `0471` a
   `load_type: bodyweight`; `3302` (pino = sostén de equilibrio, no un empuje) a `role: accessory`
   y queda dentro del `skill_gated`.
4. Para el empuje vertical sin material **no hay alternativa segura en el dataset** (los únicos
   ejercicios `vertical_push` con `equipment_group: bodyweight` son los dos de pino). Decisión: el
   slot cae por `pattern_affinity` a `horizontal_push` (flexión inclinada/declinada) y el motor emite
   `slot_relaxed` con texto: «Sin material no hay un empuje vertical seguro para tu nivel: hemos usado
   flexiones. Con mancuernas o bandas podrás trabajar hombros.» El volumen de hombros queda bajo
   objetivo con aviso, que es el comportamiento honesto. No se inventa un ejercicio.
5. Test de aceptación (propiedad): para `beginner` e `intermediate`, ningún ejercicio del plan
   supera dificultad 2; para todos los niveles, ningún id de `skill_gated` aparece sin favorito.
6. La celda `vertical_push × bodyweight` del requisito «≥ 2 staples por celda» queda **exenta** con
   motivo escrito en `docs/enrichment-report.md` («solo existen ejercicios gimnásticos»).

### Riesgo 2 · Volumen inalcanzable en plantillas de 6 slots (pecho bajo, brazos alto)

**Decisión: la tabla de prescripción manda sobre la asignación; el déficit de volumen se avisa, no se
compensa inflando series; y se corrigen plantillas y créditos.**

Medición sobre los 12 snapshots (fuera del margen ±15 % de `volume_warning_ratio`): pecho por debajo
en 7 de 12, hombros en 5, core en 6, isquios/glúteos/gemelos en 4 cada uno; brazos por encima en 7 de
12 (17 vs 14 en el 02; 22 vs 16 en el 03; 27 vs 21 en el 12; 16 vs 8 en el 11).

Causas:

- **Pecho**: `upper_a` y `upper_b` solo aportan un press principal (máx. 5 series) y un press
  accesorio (máx. 4): techo teórico 9 series/semana frente a 10–16 del objetivo intermedio de
  hipertrofia. No existe ningún slot `chest_fly` en los días de torso.
- **Brazos**: `set_credit.relevant_secondary: 0.5` acredita a brazos la mitad de cada serie de todo
  empuje y tirón (~15 series de compuestos → +7,5), de modo que el objetivo de brazos se «cumple» con
  cero trabajo directo. El resultado es el patrón visto en los snapshots: curls y extensiones de **1
  serie** (02 día 1, 03, 11, 12) y aun así brazos por encima del objetivo.
- **Asignación** (`allocation.bounds_by_role.main: [2, 5]`) permite 5 series de un principal aunque
  la prescripción diga `[3, 3]` (toning) o `[3, 4]` (hipertrofia) y los principiantes deban ir «en el
  mínimo del rango» (§7.5). Ver B2.

Cambios:

1. `volume-targets.yaml#set_credit`: añadir `secondary_credit_by_group: { arms: 0.3 }` (la evidencia
   sostiene contribución real pero parcial de press y remo al tríceps y bíceps; 0,3 es el valor
   conservador usado en la práctica). Resto de grupos sin cambio en 0,5. El motor lo aplica en
   `volume.card_credits` y `volume.slot_credits`.
2. `engine-rules.yaml#allocation.bounds_by_role.accessory` de `[1, 4]` a `[2, 4]`: un accesorio de 1
   serie no es un estímulo; si el tiempo no da para 2 series, se elimina el slot (ajuste (c) de §7.2)
   en lugar de dejar 1. Se aplica también a los slots de bloque de énfasis.
3. Bloques de énfasis: `emphasis_overrides.arms.append_block.to` de `"*"` a
   `[upper_a, upper_b, push, pull]` (nunca días de pierna; 27 vs 21 en el snapshot 12 incluye brazos en
   el día de pierna) y `min_days` 3 se mantiene.
4. Plantilla `upper_a`: sustituir el slot 4 `{vertical_pull, accessory, back, 2}` por
   `{ pattern: chest_fly, role: accessory, group: chest, priority: 2 }`. Pecho pasa de techo 9 a 12 en
   4 días; espalda mantiene `horizontal_pull` main (A) + `vertical_pull` main y `horizontal_pull`
   accessory (B) = 3 slots.
5. Aceptación tras regenerar: ningún grupo por debajo de 85 % del mínimo del rango salvo que el
   equipamiento no permita entrenarlo (el motor ya lo avisa), y brazos (créditos 0,3) dentro del
   rango ±15 % en los snapshots 02, 03, 05, 09, 11 y 12.

### Riesgo 3 · Días pesados de fuerza a 1–4 repeticiones

**Decisión: se corrige. Suelo de 3 repeticiones, RIR ≥ 2 salvo avanzados en semanas de
intensificación, y la ondulación solo se aplica a compuestos cargables.**

Causa verificada: `periodization.yaml#strength_undulation.heavy_day: { reps_shift: -2, rir: 1 }`
aplicado sobre `3–6` da `1–4` (snapshots 04 y 05). Problemas concretos:

- Un rango que empieza en 1 repetición con RIR 3 es una contradicción (RIR 3 en 1 rep es una carga
  del ~70 % del 1RM, no un día pesado) y con RIR 1–2 empuja a máximos de 1RM a intermedios sin
  supervisión. El texto `rationale_es` del propio plan dice «3-6 repeticiones» mientras la tabla
  muestra `1-4`.
- La ondulación se aplica a **todos** los ejercicios `main`, incluidas la sentadilla goblet, el press
  militar con kettlebell y los «buenos días» con barra (snapshots 04 y 05: «buenos días con barra
  4 × 1-4 a 240 s»). Los buenos días a series de 1–4 son de riesgo lumbar alto y nadie debe cargarlos
  cerca del máximo sin técnica probada.
- La regla de RIR `max(día, semana)` hace que el día «pesado» de la semana 1 sea RIR 3, o sea, no es
  pesado.

Tabla propuesta (§6, diff exacto):

```yaml
strength_undulation:
  enabled_for: [intermediate, advanced]
  applies_to: { mechanic: compound, load_type: external, equipment_any: [barbell, trap_bar, smith, machine, cable, dumbbell] }
  excluded_ids: ["0044", "0090", "0115", "0749", "3759"]   # buenos días: nunca a alta carga
  heavy_day:  { reps_shift: -1, min_reps: 3, rir_floor: { intermediate: 2, advanced: 1 } }   # 3-6 -> 3-5
  medium_day: { reps_shift: 1,  rir: 2 }                                                     # 3-6 -> 4-7
```

Resultado: día pesado 3–5 reps, día medio 4–7 reps; RIR 2 mínimo para intermedios. Series 4–5 con
descanso 240–300 s se mantienen. `rationale_es` debe citar el rango real («3-5 y 4-7 repeticiones»).

### Riesgo 4 · Puntuación extra `loadable_in_main: +10`

**Decisión: se aprueba como extensión de §7.2 con tres condiciones; debe documentarse en un ADR
(o en `docs/CONTRACT_CHANGES.md`) porque no está en el MASTER_PROMPT.**

Justificación: sin ella, un slot principal de gimnasio podía resolverse con flexión de rodillas o
banda, algo indefendible. **Pero el síntoma que la motivó era en parte consecuencia de B1**: al
excluirse por error los press y sentadillas de barra por `target_muscle`, quedaban candidatos flojos.
Condiciones:

1. Se revalida tras corregir B1 (los snapshots con `+10` deben mantener la mejora sin B1).
2. Dependencia del nivel: para `beginner`, `loadable_equipment` = `[dumbbell, machine, smith, cable,
   kettlebell, sled]` (sin barra libre: técnica y seguridad; máquina y goblet enseñan el patrón). Para
   `intermediate`/`advanced` se añade `barbell, trap_bar, ez_bar, weighted`.
3. No se aplica con objetivo `endurance` (circuitos con peso corporal son válidos) ni cuando el único
   material disponible es banda/peso corporal (ya ocurre).

Adicional (CAMBIO C5): para `strength` en intermedios/avanzados, +10 más a `barbell`/`trap_bar` en
slots `main`: hoy el press de banca del snapshot 04/05 sale con mancuernas en lugar de barra.

### Riesgo 5 · Días veganos y sin frutos secos con grasa 15–25 % por encima

**Decisión: no se sube la tolerancia del contrato; se corrige el planificador y se introduce un techo
absoluto de grasa. El sobrepaso relativo no es un problema de salud por sí mismo, pero el techo sí
debe existir.**

Medición (288 perfiles: 4 cuerpos × 4 dietas × 3 combinaciones de alérgenos × 3 objetivos × 3 y 4
comidas, `NutritionInput` válidos, semilla derivada, 2.016 días):

| Dieta | Días con grasa > +15 % del objetivo | Días con \|desv. grasa\| > 10 % | Grasa media (% kcal) | Grasa > 35 % kcal |
|---|---|---|---|---|
| omnívora | 23–27 % | 45–48 % | 25,8 | 3,2 % de días |
| pescetariana | 27–32 % | 48 % | 26,0 | 5,2 % |
| vegetariana | 58–68 % | 76–85 % | 27,7 | 11,5 % |
| vegana | 57–61 % | 82–88 % | 27,8 | 10,7 % |
| Total | 44 % | 65 % | 26,8 | 7,6 % (máx. 43,4 %) |

Además, **286 de 288 planes emiten `tolerance_not_met`**: el aviso ha dejado de informar. El
sobrepaso medio (26–28 % kcal en grasa) está dentro del rango de referencia (20–35 %), pero en 1 de
cada 13 días se supera el 35 % y llega al 43 %.

Causa: la plantilla exige siempre proteína + hidrato + verdura/fruta + **grasa** en cada comida, la
selección es uniforme dentro de cada rol (`select_food`, peso base 10 con penalización por repetición),
y las porciones se acotan solo por `_MAX_PORTION_MULTIPLIER = 6.0` × la porción típica. En dietas sin
lácteos ni frutos secos, las fuentes de proteína vegetal disponibles son densas en grasa (soja seca
19 g/100 g, harina de soja 20, tempeh, pipas, sésamo) y el ítem «grasa» se suma encima.

Cambios (B7 y C12, propietario motor-nutricion):

1. Techo duro: grasa ≤ 35 % de las kcal del día. Si la solución de `lsq_linear` lo rebasa, se
   reintenta con la penalización de grasa ×3 y, si persiste, se emite aviso.
2. Función objetivo: ponderar el error de grasa por encima del objetivo ×2 (asimétrico); el error por
   debajo del suelo (`fat.min_g_per_kg`, 20 % kcal) sigue siendo hard.
3. El ítem «grasa» de una comida es opcional: se omite si la grasa aportada por proteína + hidrato ya
   cubre ≥ 70 % del presupuesto de grasa de esa comida.
4. Aceite de oliva virgen extra: peso de selección ×4 en `fats_oils`; `aceite_coco` y `aceite_girasol`
   ×0,25 (gastronomía española; el coco es grasa saturada casi pura).
5. `tolerance_not_met` solo cuando kcal o proteína se salen de ±5 %/±10 %, o la grasa supera el techo
   del 35 %. La desviación de grasa dentro de la banda 20–35 % se registra como `info` en el plan pero
   no como aviso.
6. Criterios de re-verificación con el mismo barrido de 288 perfiles: 0 días con grasa > 35 % kcal;
   `tolerance_not_met` en ≤ 25 % de los planes; días veganos con desviación de grasa > +15 % ≤ 25 %.

## 2. Hallazgos BLOQUEANTES (8)

Formato: **ID · título** — propietario — fichero(s) — evidencia — corrección exacta.

### B1 · El filtro de grupo objetivo usa `target_muscle` del dataset y excluye las sentadillas y bisagras de barra
- **Propietario:** motor-rutinas (`engine/forja_engine/select.py`, `volume.py`). Alternativa parcial:
  ingesta (override de `target_muscle`), descartada por invasiva.
- **Evidencia:** `select.py:99` asigna `self.group[card.id] = tables.muscle_group(card.target_muscle)` y
  `candidates()` (líneas 141–146) descarta todo candidato cuyo grupo ≠ `slot.group` salvo relajación.
  En el dataset, **46 de 58 sentadillas** y **52 de 56 bisagras** tienen `target_muscle` = `glutes`
  (o `lower_back`), mientras que los slots piden `quads`/`hamstrings`. Consecuencias observables:
  en gimnasio completo el slot `squat` principal se resuelve con `1760` sentadilla goblet
  (snapshots 02, 03, 05, 09, 10, 11, 12) o `3533` sentadilla con peso corporal 5 × 6-10 (snapshots 03
  día 6, 11 día 7, 12 día 5), y el slot `hinge` con `0044` buenos días con barra (todos los planes de gimnasio con slot de bisagra; hasta 5 series principales, incluso para el principiante del snapshot 09).
  Peso muerto (`0032`), peso muerto rumano (`0085`), sentadilla de barra (`0043`), prensa (`0739`),
  hack y multipower están todos excluidos. Además `card_credits` acredita a *glúteos* toda sentadilla
  de barra, así que cuádriceps queda por debajo (snapshots 05 y 10 fuera de margen; 02 y 03 en el límite) y glúteos por encima.
- **Corrección:**
  1. En `Selector.__init__` y en `volume.card_credits`, para tarjetas con `mechanic == compound` y
     `movement_pattern` en `{squat, lunge, hinge, horizontal_push, vertical_push, horizontal_pull,
     vertical_pull}` el «grupo de entrenamiento» es `tables.engine_rules.pattern_groups[pattern]`
     (squat→quads, lunge→quads, hinge→hamstrings, …), no el derivado de `target_muscle`. Para el resto
     (aislamientos) se mantiene `target_muscle`.
  2. El crédito secundario de compuestos (`compound_secondary_groups`) ya cubre glúteos en squat/hinge/
     lunge; el grupo de `target_muscle` no se acredita adicionalmente si coincide con uno de esos.
  3. `slot_touches_avoided` no cambia (usa músculos, no patrón).
  4. Test nuevo: en el catálogo real, para cada uno de los slots `main` de `split-templates.yaml` y
     equipamiento `full_gym`, `candidates(...)` contiene ≥ 1 staple de barra o máquina; y ningún plan
     `full_gym` de nivel intermedio/avanzado usa `3533`, `1760`, `0044` como principal si existe
     alternativa.
  5. Subir `ENGINE_VERSION` (actual 0.1.0) y regenerar los 12 snapshots.

### B2 · La asignación de series supera la tabla de prescripción y los principiantes no van al mínimo
- **Propietario:** motor-rutinas (`specs/engine-rules.yaml#allocation`, `engine/forja_engine/allocate.py`,
  `prescribe.py`).
- **Evidencia:** MASTER §7.5 fija `hypertrophy main 3–4`, `fat_loss/toning main 3`, `general_fitness
  main 3` y «principiantes: series en el mínimo del rango». Los snapshots muestran: 01 principiante
  hipertrofia, sentadilla goblet **5** series y bisagra **5**; 09 principiante forma general, **5, 5,
  4, 5** series principales (tabla: 3); 07 tonificación, flexión y remo **5** series (tabla: 3);
  02/03/10 hipertrofia, principales de **5** (tabla: 3–4). `bounds_by_role.main: [2, 5]` y el
  reparto hacia el punto medio del objetivo de volumen pasan por encima de `prescription.yaml`.
- **Corrección:** derivar los límites por ejercicio de la tabla: `main.max = prescription[goal][main]
  .sets.max`; `accessory.max = prescription[goal][accessory].sets.max`; nunca menos de 2; los
  principiantes usan el mínimo del rango exacto (no ajustar al alza por volumen). La regla de
  `accumulation_extra_cap` (+1 serie) solo se aplica a `intermediate` y `advanced` y solo a partir de
  la semana 3. El déficit de volumen resultante se comunica con `volume_out_of_range` (comportamiento
  correcto) y se compensa con las plantillas (Riesgo 2), no con series. Test: para todos los planes de
  las 1.890 combinaciones, `sets ≤ prescription.max (+1 en acumulación tardía)`.

### B3 · La dificultad se relaja hasta 3 en principiantes y hay staples gimnásticos/olímpicos
- **Propietario:** motor-rutinas (`engine-rules.yaml`) + ingesta (`staples.yaml`, `enrichment-overrides.yaml`).
- **Evidencia:** ver Riesgo 1. Snapshot 01: `0535` cargada colgante con kettlebell (d3) como bisagra
  principal de 5 series, dos días por semana, para principiante. Snapshots 06 y 08: `0471` flexión en
  pino 2 × 20 s y `3302` pino en circuito.
- **Corrección:** regla completa del Riesgo 1 (relajación, `skill_gated`, staples, `load_type`).
  Diffs en §6.1 y §6.3.

### B4 · Días pesados de fuerza a 1–4 repeticiones aplicados a ejercicios inadecuados
- **Propietario:** motor-rutinas (`specs/periodization.yaml`, `engine/forja_engine/periodize.py`,
  `texts.py`).
- **Evidencia y corrección:** Riesgo 3.

### B5 · Los presets `bodyweight` y `home_bands` devuelven ejercicios que exigen barra, banco, anillas o máquina de polea
- **Propietario:** ingesta (override) + motor-rutinas (filtro por preset).
- **Evidencia:** de 245 ejercicios de fuerza del grupo `bodyweight`, **62 (25 %)** exigen barra de
  dominadas, paralelas, suspensión, anillas o máquina (dominadas, fondos, elevaciones colgado,
  `0498`/`0808`/`0809` con correas, `2400` «máquina de dominadas con polea» con `equipment_code:
  bodyweight`). Otros 19 requieren banco o cajón. Snapshot 07 (solo bandas): `2400` curl femoral
  inverso en máquina de dominadas con polea, `0488`/`0489` hiperextensión como **principal** 3 × 8-13,
  `0130` extensión de cadera en banco. Snapshot 06 y 08 (peso corporal): `1429` dominada con agarre
  ancho 2 × 8-12 (principiante) y dominada 2 × 15-25 (intermedio; no existe una serie realista de
  15–25 dominadas: ver C9). El enum `EquipmentCode` del contrato está congelado
  (`contracts/openapi.yaml:2012`), así que no se pueden crear códigos `pullup_bar`/`bench` sin
  CC.
- **Corrección (sin cambio de contrato):**
  1. Ingesta: `enrichment-overrides.yaml#by_id` admite `equipment_code`; `2400` → `cable`.
  2. `engine-rules.yaml` nueva sección `fixture_gated` (ver §6.1): lista de `display_name_en`
     (subcadenas) y ids que requieren estructura fija. Se excluyen automáticamente cuando el preset de
     equipamiento es `bodyweight` o `home_bands`; con `home_dumbbells`, `full_gym` y `custom` se
     permiten.
  3. En estos presets el slot `vertical_pull` cae por `pattern_affinity` a `horizontal_pull`
     (`3168` remo en sentadilla con toalla, `3166` remo de pie con peso corporal, ambos sin estructura).
  4. Texto `slot_relaxed` específico: «Sin barra de dominadas: hemos usado remos.»
  5. Ingesta/arquitecto: abrir CC (v1.1, no bloquea) para añadir `pullup_bar` y `bench` a
     `EquipmentCode` y a un preset «peso corporal con barra».
  6. Wizard (frontend): texto del preset `bodyweight` «Sin material. Si tienes barra de dominadas,
     usa “equipamiento propio”.»

### B6 · Etiquetas de alérgenos incorrectas o incompletas
- **Propietario:** motor-nutricion (`nutrition/forja_nutrition/data/foods.json`, tests).
- **Evidencia (auditoría de los 193 alimentos):**
  - `avena`: sin alérgenos. La avena está declarada como cereal con gluten en el Reglamento (UE)
    1169/2011 y es la fuente habitual de contaminación cruzada: debe llevar `gluten`.
  - `cuscus`: sin alérgenos. El cuscús es sémola de trigo duro: **gluten**.
  - `cerveza`: sin alérgenos. Lleva malta de cebada: **gluten**.
  - `leche_almendra`: sin alérgenos y `macro_role: protein`. Es almendra: **`tree_nuts`**; además 0,4 g
    de proteína/100 g no es una fuente proteica (rol `none`/`carb`).
  - `cacahuete` y `mantequilla_cacahuete`: sin alérgeno alguno; el perfil A del handoff («alergia a
    frutos secos») **recibe mantequilla de cacahuete** (día 2 mostrado). La alergia a
    cacahuete y a frutos secos de árbol coexisten en 25–40 % de los casos y en el habla común
    «frutos secos» incluye el cacahuete. Hasta resolver CC-0002, `cacahuete` y `mantequilla_cacahuete`
    llevan también `tree_nuts`; cuando se apruebe `peanuts`, se separan y el selector de UI vincula
    ambos.
  - `altramuz`: alérgeno UE (altramuces) con reactividad cruzada con cacahuete; etiquetar `peanuts`
    o `tree_nuts` en el mismo cambio.
- **Corrección exacta:** ver §6.4 (diff sobre `foods.json`) y añadir a `nutrition/tests` un test de
  auditoría con la lista de verdad: `{trigo, cebada, centeno, avena, espelta, cuscús, bulgur, harina de
  trigo, pan, pasta, cerveza} ⊆ gluten`; `{almendra, avellana, nuez*, anacardo, pistacho, piñón,
  macadamia, coco, leche de almendra} ⊆ tree_nuts`.

### B7 · Planes de comida no realistas: sin límites de porción ni idoneidad por comida
- **Propietario:** motor-nutricion (`planner.py`, `foods.json`, `specs/nutrition.yaml`).
- **Evidencia (barrido de 288 perfiles):**
  - Sin `max_portion_g` por alimento. Máximos en una sola comida: 1.500 g de sandía, 1.200 mL de leche,
    985 g de patata, 900 g de calabacín/tomate/berenjena, 720 g de brócoli. Handoff: 55 g de semilla de
    chía, 30 g de sésamo, 90 g de anchoas en aceite, 480 g de endibia, 320 g de espárrago, 290 g de
    tofu sedoso.
  - Sin idoneidad por comida: **legumbres, pescado o carne cruda de guiso en el desayuno**: 160/504
    desayunos omnívoros, **312/504 veganos** contienen legumbres secas (judías pintas con pan blanco y
    mantequilla de cacahuete «de desayuno»); guisante partido seco en meriendas 37 veces; hígado de
    vacuno en 8 desayunos.
  - Cantidades irrisorias «para cuadrar»: «Maíz dulce 5 g», «Sésamo 5 g», «Aceite de coco 5 g».
  - `tolerance_not_met` en 286/288 planes: pierde significado (Riesgo 5).
- **Corrección:**
  1. `foods.json`: nuevos campos `max_portion_g` (por alimento; regla: ≤ 2,5 × `typical_portion_g`
     salvo cereales, legumbres y proteínas animales que admiten ≤ 4 ×; verduras de hoja/frutas ≤ 2 ×;
     semillas, frutos secos y aceites ≤ 2 ×) y `meal_slots` (lista de `breakfast`, `mid_morning`,
     `lunch`, `snack`, `dinner`).
  2. `meal_slots` por defecto: legumbres secas, pescado, marisco, carne, hígado, verduras cocinadas
     (col, coliflor, espárrago, alcachofa, berenjena, calabacín, puerro, acelga) → solo `lunch` y
     `dinner`. Desayuno: lácteos, huevo, avena, pan, tortitas, bagel, fruta, frutos secos, aguacate,
     tofu (vegano), jamón. Merienda/media mañana: fruta, lácteo, frutos secos, pan/tortitas, huevo.
  3. Porción mínima útil: si el solver deja un ítem < 30 % de `typical_portion_g` (5 g de maíz), se
     elimina el ítem y se reparte.
  4. `_MAX_PORTION_MULTIPLIER = 6.0` desaparece; se usa `max_portion_g`.
  5. Criterio de re-verificación: en el mismo barrido, 0 desayunos con legumbre/pescado/carne guisada;
     ningún ítem por encima de `max_portion_g`; 0 ítems < 30 % de la porción típica.

### B8 · Ejercicios contraindicados por defecto se seleccionan en los planes
- **Propietario:** motor-rutinas (`engine-rules.yaml`, `select.py`); ingesta como apoyo.
- **Evidencia:** snapshot 02, día 3: calentamiento con `1325` **jalón tras nuca en polea con agarre
  ancho**, y snapshot 03 día 4: `0764` press en multipower con agarre supino como calentamiento. El
  calentamiento específico toma «un ejercicio ligero del patrón del primer slot principal» sin filtro
  de seguridad: cualquier variante tras nuca (jalones, press militar, dominada, extensión de tríceps
  tras nuca: `0086`, `0747`, `0772`, `0788`, `1325`, `1367`, `0670`, `1718`, `1748`) es candidata. La
  posición tras nuca con carga es de riesgo elevado para el hombro y la columna cervical y no aporta
  nada que no aporte la versión frontal. `0119/0120/0121`, `0123` (remo al mentón con barra) y
  variantes también entran en slots `shoulder_raise` (03 día 4, `0121`).
- **Corrección:** `engine-rules.yaml#exclusions.contraindicated_default` (§6.1) con
  `name_en_any: ["behind neck", "behind head", "rear pull-up", "wide grip rear", "upright row"]` e ids
  explícitos; se aplica en `Selector.__init__` (fuera de `usable`) salvo `favorite_exercise_ids`.
  Además, el calentamiento específico debe elegir el ejercicio de **menor dificultad** entre los
  `is_staple` del patrón y nunca uno con `role: accessory` de variante exótica (§C7).

## 3. Hallazgos CAMBIO (17)

**C1 · Staples (ingesta, `specs/overrides/staples.yaml` + `enrichment-overrides.yaml`).** Retirar
como staples y/o corregir: `0046` sentadilla hack con barra (carga posterior incómoda, no
fundamental); `1759` pistol (d3); `0044` buenos días → `role: accessory`, `is_staple: false` (el
peso muerto rumano `0085`/`1459` es el estándar); `0489`/`0488` hiperextensión (aislamiento lumbar,
necesita banco romano) → `is_staple: false`; `0251` fondos de pecho → `difficulty: 3`,
`is_staple: false`; `0553` press militar a dos manos con kettlebell → `is_staple: false` (existen
`0405`, `0426`, `0091`); `0471`/`3302` (B3); `3193` glute-ham raise y `0496` curl femoral inverso con
apoyo en banco → `difficulty: 3`, `is_staple: false` y añadir `0696`, `1766` (curl femoral inverso
asistido, d1) como staples de `knee_flexion` bodyweight; `2135` plancha lastrada → mantener solo como
staple de gimnasio y añadir **`3239` plancha de rodillas con toque de hombro** como staple
bodyweight (no existe plancha simple en el dataset); `1160` burpee → dejar de ser staple de `cardio`
para principiantes (ver S2). Celda `hinge × bodyweight`: la única bisagra genuina sin material es
`3292` «elevator»; exenta del mínimo de 2 con motivo («la bisagra sin material se cubre por afinidad
con `glute_isolation`»).

**C2 · Puntuación de accesorios (motor-rutinas, `engine-rules.yaml#scoring`, `select.py`).** Los
accesorios se eligen por azar entre cientos de variantes: `elbow_flexion` tiene 146 candidatos y solo
6 staples. Resultado en los snapshots: «curl predicador invertido con mancuerna a una mano»
(`1414`), «curl alto con mancuernas» (`1664`), «zancada de sprint en multipower» (`0769`), «curl de
bíceps sentado sobre fitball» (`0390`), «press de tríceps con peso corporal» (`0816`). Añadir
`staple_in_accessory: 12` y `main_requires_compound: true` (un slot `main` nunca se rellena con
`mechanic: isolation`, hoy ocurre con hiperextensión en los snapshots 06, 07, 08).

**C3 · Créditos y bloques de brazos (motor-rutinas).** Riesgo 2, puntos 1 y 3.

**C4 · Cobertura de pecho por plantilla (motor-rutinas, `split-templates.yaml`).** Riesgo 2, punto 4.

**C5 · `loadable_in_main` y preferencia de barra en fuerza (motor-rutinas).** Riesgo 4.

**C6 · Accesorios de 1 serie y orden de bloques (motor-rutinas, `allocate.py`, `timefit.py`,
`compose.py`).** Riesgo 2, punto 2; y ordenar los bloques del día: todos los compuestos en series
rectas primero, después las superseries de aislamiento (snapshot 12 día 2: la superserie de
isquiotibial y cuádriceps precede a la sentadilla dividida).

**C7 · Calentamiento y vuelta a la calma (motor-rutinas, `select.py:241–299`).**
(a) Calentamiento cardio: siempre `3636` «rodillas altas contra la pared» 180 s en las 12 sesiones y
en todos los días; rotar entre los `role: warmup` disponibles según equipamiento (marcha, comba,
bicicleta, elíptica, cuerdas). (b) El ejercicio específico se elige por menor dificultad entre staples
del patrón; para `strength` main, sustituirlo por las series de aproximación 40/60/80 % de
`periodization.progression.warmup_ramp` sobre el propio ejercicio. (c) La vuelta a la calma debe
elegir los estiramientos de los grupos entrenados ese día: snapshot 01 día 2 (isquios, hombros,
espalda) termina con «postura de ángulo abierto sentado» (aductores) y deltoides posterior; snapshot 09
día 2 igual. Regla: ordenar candidatos por solapamiento con los grupos del día. (d) `30 s por lado`
para posturas simétricas («ángulo abierto sentado», «mariposa») no tiene sentido: sin `per_side` si el
ejercicio es bilateral.

**C8 · Día de recuperación activa (motor-rutinas, `engine-rules.yaml#recovery`).** Snapshot 11 día 4:
«carrera de zancada corta» 20 min como «cardio suave» más 2 estiramientos. Para recuperación activa
usar solo cardio de bajo impacto (`bike`, `elliptical`, `stepmill` a ritmo suave, caminata `3666`,
`2311`), 20–30 min a RPE 3–4 (texto: «puedes hablar con frases completas») y 5–6 ejercicios de movilidad
dinámica de `role: mobility`/`warmup` (no 2 estiramientos estáticos). Excluir carrera, saltos y
pliometría.

**C9 · Repeticiones imposibles en peso corporal difícil (motor-rutinas, `prescribe.py`).** Snapshot
08 (resistencia, intermedio, peso corporal): «dominada 2 × 15-25», «dominada con agarre ancho 15-25».
Regla: para ejercicios `load_type: bodyweight` de la familia dominada/fondos/flexión en pino, techo de
repeticiones prescritas 12 y suelo 5; si el rango de la tabla lo supera, se usa el techo y se avisa.
En circuitos de resistencia, preferir `horizontal_pull` (remo) sobre `vertical_pull` (B5 lo fuerza en
peso corporal).

**C10 · Errores de enriquecimiento (ingesta, `enrichment-overrides.yaml`).** Ver §5.1: `0555`
«patada sentado» está como `knee_flexion` pero las instrucciones describen una extensión de rodilla
(→ `knee_extension`; el snapshot 12 lo usa como sustituto de isquiotibial); `0352`, `1625`, `0812–0815`
press cerrado y fondos como `elbow_extension` **aislamiento** (→ `mechanic: compound`); `0677` fondos
en anillas → d3; `1367`, `0670` dominada tras nuca → `difficulty: 3` (además de B8); `0471`
`load_type: bodyweight`; regla `keywords.difficulty_level_3_any` añadir `"pull-up"`, `"chin-up"`,
`"chin up"`, `"dip"` cuando `equipment == body weight` y sin `assisted|band|negative|kneeling|
inverted|bench|on floor|between benches|bench leg` en el nombre (dominadas y fondos estrictos son
nivel intermedio-avanzado); `0858` «wind sprints» es carrera (instrucciones: «empieza a correr lo más
rápido que puedas»), no un abdominal: `cardio`.

**C11 · Nombres ES (ingesta, `specs/overrides/names_es.json`).** Ver §5.3 (tabla completa de
correcciones). Prioritarias: `1288` fuga «(variante de apoyo)»; `3234` «aperturas altas» contradice
sus instrucciones (aperturas en banco plano); `0858`; `0043` «sentadilla profunda con barra» → «sentadilla
trasera con barra» (es el ejercicio fundamental y «profunda» induce a error sobre el rango);
`3562`/`1409` (puente de glúteo con barra ↔ hip thrust con barra).

**C12 · Selección de grasas y procesados (motor-nutricion).** Riesgo 5, puntos 3–4, más: `bacon`,
`salchicha_cerdo`, `jamon_cocido`, `jamon_curado`, `anchoa_lata`, `higado_vacuno` con límite de
aparición semanal (procesados 2/semana; hígado 1/semana) y `max_portion_g` (anchoa 30 g; hígado 100 g).

**C13 · Tono de los avisos y `tolerance_not_met` (motor-nutricion + frontend).** Un aviso que aparece
en el 99 % de los planes es ruido; además los textos que ya se muestran son punitivos o técnicos
(«factores de Atwater específicos de este alimento»). Ver Riesgo 5 punto 5 y S6.

**C14 · Proteína en obesidad (motor-nutricion, `specs/nutrition.yaml#protein_g_per_kg`).** 2,1 g/kg de
peso total para `lose` con un usuario de 130 kg da 273 g/día (irreal y con carbohidratos inviables). Con
IMC ≥ 30 usar `min(peso, peso a IMC 27)` × g/kg. La tabla y el motor deben copiar el criterio; se
mantienen 1,6–2,2 g/kg y el tope absoluto de 220 g/día.

**C15 · `macro_role` y catálogo (motor-nutricion, `foods.json`).** `leche_almendra` `protein`→`carb`;
`cerveza`, `vino_tinto`, `refresco_cola`, `zumo_*` → mantener fuera del selector (ya lo están por
categoría). `haba` (fresca) como proteína con 7 g/100 g y 88 kcal: legumbre, correcto. Añadir
etiquetas para los alérgenos UE no cubiertos por §8.1 y presentes en el catálogo: `sesamo` (sésamo),
`mostaza`, `apio` (apio), `altramuz` (altramuces), `almeja/calamar/pulpo/mejillon` (moluscos ya como
`shellfish`); si el contrato no admite nuevos valores, documentarlo en la UI como «no filtrable»
(tarea de backend/frontend).

**C16 · Exclusión de zona lumbar (motor-rutinas, `select.py`).** El snapshot 12 declara evitar
«bisagra y zona lumbar» pero incluye `0293`/`3200` remo inclinado (carga lumbar isométrica), y el filtro
solo mira `target_muscle` ∈ `avoid_muscles`. Regla: si `lower_back` ∈ `avoid_muscles`, excluir también
`hinge`, y los ejercicios cuyo `display_name_en` contenga `bent over|bent-over|good morning|
deadlift|hyperextension|back extension|jefferson|zercher|stiff leg`. Preferir el remo sentado en polea
(`0861`, columna neutra) y regenerar el snapshot 12.

**C17 · Deriva de tablas (arquitecto / backend).** Ya señalada por motor-nutricion: dos copias de
`nutrition.yaml`; añadir un test que compare `specs/nutrition.yaml` con
`nutrition/forja_nutrition/data/nutrition.yaml` (byte a byte) en CI.

## 4. Hallazgos SUGERENCIA (8)

- **S1 · Multiplicador `*` de `lower_glutes` = 0,8** rebaja el tren superior de una mujer principiante
  a 6,4–9,6 series (por debajo del mínimo efectivo de hipertrofia). Propuesta: `"*": 0.9` para
  `beginner`. No bloquea (es preselección editable).
- **S2 · Finisher de cardio para principiantes con pérdida de grasa**: excluir `1160` burpee y `2612`
  salto a la comba de las opciones de finisher salvo intermedios; preferir caminata inclinada `3666`,
  bicicleta `2138`, elíptica `2141`.
- **S3 · Progresión de RIR en mesociclos de 6–8 semanas**: `rir_by_week: [3, 2, 2, 1, 1, 1, 1]` deja 4
  semanas seguidas con RIR 1 en 8 semanas. Propuesta: máximo 2 semanas seguidas con RIR ≤ 1:
  `[3, 2, 2, 2, 1, 1, 2]` en 7 semanas (semana de acumulación final con RIR 2 antes de descarga).
  Para 4–5 semanas se mantiene `[3, 2, 2, 1, 1]`.
- **S4 · Avisos del plan**: los snapshots tienen 8–16 avisos (`volume_out_of_range` por grupo).
  Agruparlos en un único aviso con lista de grupos y una frase de acción. Mejora la lectura sin cambiar
  el contrato (mismo `code`, `message_es` compuesto).
- **S5 · Efecto del sexo en descansos**: el −15 % de descanso de accesorios está justificado en la
  spec pero la evidencia es limitada; reformular `explanation_es` como «descansos algo más cortos en
  accesorios, que puedes ajustar» (sin «resistencia a la fatiga»).
- **S6 · `energy_note`** (`foods.json`): texto técnico. Propuesta: «Las calorías de este alimento no
  cuadran exactamente con sus macros por el método de cálculo de la fuente (USDA).» / «Incluye las
  calorías del alcohol.» / «Rico en fibra: aporta algo menos de energía de la que sugieren sus
  carbohidratos.» Cambio de texto solamente.
- **S7 · Regla `+1 rep` femenina** (`isolation_rep_max_delta`) produce rangos raros en core («10-21»,
  «6-11»). Aplicarla solo a accesorios de aislamiento con pesos externos, no al core.
- **S8 · Calentamiento con `rationale_es`**: los textos «2 min-3 min» y «1 min 30 s-2 min» se leen
  mal; usar «entre 2 y 3 minutos» y «entre 1 min 30 s y 2 minutos».

## 5. Revisión por bloques

### 5.1 Enriquecimiento (muestreo aleatorio de 100: `seed 20260926`)

91 correctos (patrón, mecánica, rol, dificultad, lateralidad y carga plausibles). Errores y dudas
(9):

| Id | Ejercicio | Problema | Corrección |
|---|---|---|---|
| `0352` | dumbbell neutral grip bench press | `elbow_extension` aislamiento; es un press cerrado (compuesto) | `mechanic: compound` |
| `1625` | smith decline close grip bench press | ídem | `mechanic: compound` |
| `0677` | ring dips | d2; anillas inestables | `difficulty: 3` |
| `1367` | wide grip rear pull-up | d2; tras nuca | `difficulty: 3` + `contraindicated_default` |
| `0471` | handstand push-up | `load_type: time` | `bodyweight`; `is_staple: false` |
| `2400` | inverse leg curl (on pull-up cable machine) | `equipment_code: bodyweight` | `cable` |
| `3193` | glute-ham raise | d2, staple; exige máquina GHD y control excéntrico | `difficulty: 3`, `is_staple: false` |
| `0543` | kettlebell pirate supper legs | `shoulder_raise`; instrucciones = press inclinado a una mano | excluir de auto-selección o `other`; ver §5.3 |
| `0814` | triceps dip | `elbow_extension` aislamiento; los fondos son compuestos | `mechanic: compound` |

Familias sistemáticas (ver C10, B5, B8): (a) dominadas y fondos estrictos a dificultad 2 (más `0555`, detectado en la revisión de nombres: `knee_flexion` cuando la instrucción describe una extensión de rodilla);
(b) dominadas/fondos/hiperextensiones/correas/anillas con `equipment_code: bodyweight` (62 ejercicios);
(c) tras nuca sin marca de riesgo.

Lateralidad, `load_type: time` (isométricos, cardio) y rol `warmup`/`mobility` estaban correctos en
las 100 muestras. Los 8 `other` justificados son razonables (prehabilitación de manguito rotador y
rotadores de cadera, tabla de equilibrio, turkish get-up).

### 5.2 Staples (144)

Cobertura por patrón × grupo: la matriz del informe cumple el mínimo (≥ 2) en todas las celdas con
candidatos, pero **tres celdas se cumplen con ejercicios que no son fundamentales ni seguros**:

| Celda | Staples actuales | Problema | Acción |
|---|---|---|---|
| `vertical_push × bodyweight` | `0471`, `3302` | Pino y flexión en pino (d3) | Exenta; sin staples (B3/Riesgo 1) |
| `hinge × bodyweight` | `0489`, `0488` | Hiperextensión (lumbar; requiere banco romano) | Exenta; `3292` como bisagra sin material |
| `knee_flexion × bodyweight` | `0496`, `3193` | Variantes de nórdico (d3) | `0696`, `1766` |

Otros: `squat gym`: `0043`, `0042`, `0770`, `0739` correctos; `0046` fuera. `lunge`: correcto (`0410`
sentadilla búlgara: nivel intermedio, no principiante; se mantiene porque `difficulty: 2` es el tope).
`horizontal_push gym/home`: correcto; fuera `0251`. `horizontal_pull`: `3017` remo Pendlay es de
técnica avanzada; se mantiene por `0027` y `0180`, pero anotar en el informe que el motor no debe
preferirlo en principiantes (lo cubre C2). `vertical_pull`: `0652`/`1326`/`1429` dominadas estrictas
→ pasan a d3 (C10) y dejan de ser staples de principiante; `0017` asistida y `2330`/`0198` jalones
quedan como staples principales. Suficiente para el motor gracias a la afinidad `vertical_pull →
horizontal_pull`. Accesorios y core: aprobados.

Cobertura resultante tras los cambios: todas las celdas con ≥ 2, salvo las 3 exentas documentadas.

### 5.3 Nombres en español

**Muestreo de 150**: terminología correcta en el 97 % (146/150): «press de banca», «peso muerto rumano»,
«zancada», «sentadilla búlgara», «remo al mentón», «curl martillo», «jalón al pecho», «encogimiento de
hombros», «prensa de piernas», «elevación de talones», «multipower», «envión», «arrancada», «cargada».
Sin calcos graves. Consistencia de glosario 100 % (`validate_names` da 0 incidencias). Los 4 casos
a corregir:

| Id | Actual | Propuesta |
|---|---|---|
| `1288` | aperturas sobre fitball con mancuerna a una mano (variante de apoyo) | aperturas sobre fitball con mancuerna a una mano |
| `1305` | empuje de pecho con respuesta simple con balón medicinal | pase de pecho con balón medicinal |
| `0043` | sentadilla profunda con barra | sentadilla trasera con barra |
| `3562` | puente de glúteo con barra y dos piernas en banco | hip thrust con barra (espalda apoyada en banco) |

Observaciones de estilo (sin cambio obligatorio): «abdominal completo» para sit-up y «medio abdominal
completo» (`3202`) suenan a calco; propuesta «sit-up (abdominal completo)» y «medio sit-up». Alternan
«extensión de codos» (`0057`) y «extensión de tríceps»: unificar a «extensión de tríceps». «Caminata
monstruo» (`0628`): «caminata lateral con banda (monster walk)».

**Los 31 casos dudosos de `docs/names-es-review.md`** (verificados contra las instrucciones ES del
dataset):

| Id | Nombre propuesto por ingesta | Veredicto | Decisión / nombre final |
|---|---|---|---|
| `0003` | crunch bicicleta | APROBADO | Instrucciones: codo a rodilla contraria con extensión de la otra pierna. |
| `0100` | esquiador con barra | APROBADO | Sin equivalente; excluir de auto-selección (instrucciones incoherentes: bisagra con salto). |
| `0138` | elevación de cadera invertida (bottoms-up) | APROBADO | Es un crunch inverso; se conserva el nombre para no colisionar con `0872`. |
| `0137` | body-up (extensión de codos desde plancha) | CAMBIO | Instrucciones: manos en superficie elevada, cuerpo recto: «extensión de tríceps con peso corporal, manos en banco (body-up)». |
| `0172` | extensión de hombros en polea en banco inclinado | CAMBIO | «jalón con brazos rectos en polea, en banco inclinado» (coherente con `0238`). |
| `0260` | crunch capullo (cocoons) | CAMBIO | «crunch con manos en la nuca (cocoons)»; «capullo» es invento. |
| `0276` | bicho muerto (dead bug) | CAMBIO menor | «dead bug (bicho muerto)»: el anglicismo es el término de uso. |
| `0316` | press inclinado con mancuernas y codos a 90° (breeding) | CAMBIO | «press inclinado con mancuernas (breeding)»; no afirmar «codos a 90°» sin verificarlo. |
| `0543` | piernas de pirata con kettlebell | CAMBIO | «elevación con kettlebell a una mano en bisagra (pirate supper legs)»; excluir de auto-selección. |
| `0555` | patada sentado para isquiotibiales | CAMBIO | Instrucciones = extensión de rodillas sentado: «extensión de rodillas sentado (kick out)» y `knee_extension` (C10). |
| `0609` | puente de Londres con cuerda | CAMBIO | «remo de pie con cuerda en polea alta (london bridge)». |
| `0641` | abdominal Otis con disco | APROBADO | Otis-up es un sit-up lastrado; añadir «lastrado»: «abdominal Otis lastrado con disco». |
| `0777` | lanzador de hechizos con mancuernas (spell caster) | CAMBIO | Calco: «giro de tronco con mancuerna hacia el pie contrario (spell caster)». |
| `0844` | círculos de brazos inclinado lastrados | CAMBIO | Instrucciones: elevación lateral con torso inclinado: «elevación lateral inclinado con mancuernas (round arm)»; el patrón `rear_delt` es correcto. |
| `0858` | sprints de piernas tumbado | CAMBIO (error) | Instrucciones: «empieza a correr lo más rápido que puedas»: «sprints (wind sprints)», patrón `cardio`. |
| `1352` | extensión lumbar boca abajo | APROBADO | — |
| `1355` | estiramiento de dorsal a una mano contra la pared | APROBADO | — |
| `1362` | postura de la esfinge | APROBADO | — |
| `1417` | curl femoral con patada diagonal a una pierna sobre fitball | APROBADO | Largo pero descriptivo. |
| `1604` | el mejor estiramiento del mundo | CAMBIO | Calco: «zancada con rotación torácica (world's greatest stretch)». |
| `2203` | movilidad de hombro sentado con rodillo (flexores, depresores y retractores) | APROBADO | — |
| `2271` | gancho de izquierda (boxeo) | APROBADO | — |
| `3119` | sentadilla profunda en cuclillas | CAMBIO | Instrucciones: muslos paralelos: «sentadilla con peso corporal hasta paralelo (potty squat)». |
| `3234` | aperturas altas con mancuernas (hyght) | CAMBIO (error) | Instrucciones: aperturas en banco plano: «aperturas planas con mancuernas (hyght)». |
| `3292` | ascensor (bisagra de cadera con peso corporal) | CAMBIO | «bisagra de cadera con peso corporal (elevator)». |
| `3304` | despellejar al gato (skin the cat) | APROBADO | — |
| `3533` | sentadilla con peso corporal (cuádriceps) | APROBADO | — |
| `3665` | plancha power point | APROBADO | — |
| `3669` | arquero de pie (rotación de tronco) | APROBADO | — |
| `0653`/`1307` | flexión sobre bosu | APROBADO | Duplicado declarado y justificado. |
| `1759` | sentadilla pistol a una pierna | APROBADO | Corrección `(male)` ya en `name-fixes.yaml`. |

Nota de proceso: `names-es-review.md` propuso para `0858` una descripción que las instrucciones del
dataset contradicen. Las instrucciones del dataset son de calidad irregular (varias entradas son
plantillas genéricas: `0260`, `0641` y `0003` comparten texto de crunch). Regla para ingesta: ante
duda, el nombre ES sigue la instrucción, no la etiqueta `target`.

### 5.4 Tablas `specs/*.yaml`

| Fichero | Veredicto | Comentario |
|---|---|---|
| `volume-targets.yaml` | CAMBIOS | Rangos coherentes con la evidencia (hipertrofia 10–20 series/semana/grupo; fuerza 6–14). `set_credit`: crédito de brazos 0,3 (Riesgo 2). Añadir `secondary_credit_by_group`. |
| `prescription.yaml` | CAMBIOS | Valores aceptables (§7.5 fiel). Falta declarar que la asignación no puede superar `sets.max` (B2). Descansos y RIR coherentes con objetivo. `min_rest_s.main: 90` incompatible con tabla de resistencia (30–60): tratado en circuito; aceptable con la excepción documentada. |
| `periodization.yaml` | BLOQUEANTE | `heavy_day.reps_shift: -2` (B4). Descarga 55 %/RIR 4/carga 0,9: aprobada. S3 sobre RIR. |
| `sex-modifiers.yaml` | APROBADO | Solo preselección y ajustes finos documentados; nunca excluye ni limita cargas. S5 para el texto. |
| `split-templates.yaml` | CAMBIOS | Tabla días × nivel coherente con §7.3. Ajuste de `upper_a` y bloques de énfasis (Riesgo 2). Orden compuestos→aislamiento correcto dentro de cada plantilla. |
| `engine-rules.yaml` | CAMBIOS | `difficulty.cap` = 2/2/2 más `accessory_extra` mantiene el tope, pero `relaxation_order` lo anula (B3). `scoring.loadable_in_main` (Riesgo 4). Nuevas claves `skill_gated`, `contraindicated_default`, `fixture_gated`. |
| `nutrition.yaml` | APROBADO con C14 | Mifflin-St Jeor, factores 1,2–1,725 más ajuste 0–0,15 con tope 1,9, déficit 15 %/10 % con tope 500 kcal, suelos 1.200/1.500/1.350, IMC < 18,5 bloquea `lose`, proteína 1,6–2,2 g/kg, grasa ≥ 0,8 g/kg y ≥ 20 %, fibra 14 g/1.000 kcal: correctos y conservadores. |
| `pattern-affinity.yaml` | APROBADO | `vertical_pull → horizontal_pull`, `hinge → glute_isolation → knee_flexion` razonables. |
| `enrichment-rules.yaml`, `equipment-normalization.yaml`, `muscle-normalization.yaml` | CAMBIOS | Añadir regla de dificultad 3 para dominadas/fondos estrictos (C10). `lower_back → group: core` es discutible pero no cambia el comportamiento tras B1. |
| `glossary-es.yaml` | APROBADO | Términos de gimnasio de España correctos; `sled: prensa` aceptable. |

### 5.5 Snapshots (12)

Cada fila: veredicto y motivos (referencias a IDs de este informe).

| # | Perfil | Veredicto | Hallazgos |
|---|---|---|---|
| 01 | Principiante, mujer, mancuernas, hipertrofia, 3 d | BLOQUEANTE | B3 cargada colgante (d3) 5 series; B2 5 series de principal; B5 dominada con agarre ancho sin barra; C7 cooldown ajeno al día; volumen: pecho/hombros/isquios/gemelos/core bajos. |
| 02 | Intermedio, hombre, gimnasio, hipertrofia, 4 d | BLOQUEANTE | B1 goblet y buenos días como principales; B8 jalón tras nuca en calentamiento; B2 5 series; C6 curl y extensión de 1 serie; C3 brazos 17 vs 14; C4 pecho 9 vs 10–16. |
| 03 | Avanzado, hombre, gimnasio, hipertrofia, 6 d | BLOQUEANTE | B1 «sentadilla con peso corporal 5 × 6-10» como principal en día de pierna; buenos días 5 × 6-10 dos veces por semana; C3 brazos 22 vs 16; cuádriceps 13 vs 17. |
| 04 | Intermedia, mujer, gimnasio, fuerza, 4 d | BLOQUEANTE | B4 «buenos días con barra 4 × 1-4 a 240 s» (dos días); goblet 3-6; C2 extensión de cadera principal 1-5; C5 press con mancuernas en fuerza. |
| 05 | Avanzado, gimnasio, fuerza, 3 d, 6 sem | BLOQUEANTE | B4 (1-4); B1; `0553` press militar con kettlebell 5 × 1-4; C5 dominada asistida como principal de un avanzado. |
| 06 | Principiante, peso corporal, pérdida de grasa, 3 d | BLOQUEANTE | B3 flexión en pino 2 × 20 s; B5 dominadas; hiperextensión como principal (C2); volumen de hombros e isquios 0. |
| 07 | Intermedia, mujer, bandas, tonificación, 4 d | BLOQUEANTE | B5 `2400` en máquina de dominadas, hiperextensión principal; B2 5 series (tabla 3); core 12 vs 8; isquios 4 vs 14. |
| 08 | Intermedio, hombre, peso corporal, resistencia, 3 d | BLOQUEANTE | B3 pino y flexión en pino; B5 dominadas; C9 dominada 15–25; `0809` suspensión; arms 13 vs 8; hombros e isquios 0. |
| 09 | Principiante, hombre, gimnasio, forma general, 2 d | BLOQUEANTE | B1/B2 buenos días 5 × 8-12 para un principiante, goblet 5, press 5, remo 4; `0097` sentadilla dividida lateral con barra (accesorio exótico para principiante). |
| 10 | Avanzada, mujer, gimnasio, hipertrofia, 5 d | CAMBIOS | B1 (goblet, buenos días 3 veces por semana: días 3, 4 y 5); `1705` sentadilla sobre bosu como accesorio de cuádriceps; cuádriceps 11 vs 17. |
| 11 | Intermedio, gimnasio, forma general, 7 d | CAMBIOS | C8 día de recuperación con 20 min de carrera; C6 accesorios de 1 serie; core 0; B1 día 7 con sentadilla con peso corporal. |
| 12 | Intermedio, hombre, custom, hipertrofia, 5 d, limitación lumbar | CAMBIOS | C16 remo inclinado con limitación lumbar; C10 `0555` como isquio; C3 brazos 27 vs 21 y series de 1; C6 orden de superserie; curl femoral sentado 5 × 6-10 como «principal» (`role_compatible`). |

Aspectos aprobados en todos los snapshots: descansos (150 s hipertrofia, 240 s fuerza, 65–75 s
accesorios, −15 % en mujeres con suelo respetado), tempos, RIR por semana y descarga (55 %, RIR 4),
duración estimada ≤ presupuesto × 1,05, orden compuestos antes que aislamiento dentro de cada bloque,
progresión lineal de principiantes sin series extra, día de recuperación obligatorio a 7 días, avisos
de veinte hallazgos con el mismo `code`, y `rationale_es` en general comprensible (única corrección de
fondo: el rango citado en fuerza, B4).

### 5.6 Nutrición

- **Fórmulas** (`energy.py`, `macros.py`, `safety.py`): APROBADAS. Mifflin-St Jeor correcto; GET =
  TMB × (factor de actividad + ajuste por días) con tope 1,9 (el perfil A del handoff: ×1,475 con 3
  días y actividad ligera es razonable); déficit 15 %/10 % con tope de 500 kcal/día; suelos 1.200/1.500/
  1.350 kcal y no bajar del TMB; bloqueo de menores de 18, embarazo y lactancia; IMC < 18,5 con `lose`
  pasa a `maintain`. Grasa mínima 0,8 g/kg y 20 %; proteína 1,6–2,2 g/kg (C14 para IMC ≥ 30).
  `4P + 4C + 9G` cuadra con las kcal al 0 % (contrato ±2 %).
- **Perfil B (mujer, 52 kg, `lose`, suelo 1.200 kcal)**: correcto en cifras (P 109 g = 2,1 g/kg,
  G 42 g = 32 % kcal, HC 97 g). El plan mostrado no es creíble: «Filete de ternera 280 g» como cena
  única, «Requesón 160 g + endibia 480 g» de desayuno, «Anchoa en aceite 90 g + muffin inglés».
- **Perfil A (vegana, alergia a frutos secos)**: contiene mantequilla de cacahuete (B6), aceite de
  coco 15 g (C12), legumbres secas en desayuno y merienda (B7), «maíz dulce 5 g, brócoli 320 g,
  semilla de lino 15 g» como merienda.
- **Etiquetas de dieta**: `vegan` omitido correctamente en miel, mayonesa, mantequilla y margarina
  (conservador aceptable); `pescatarian` sin carne; sin errores encontrados. `shellfish` para
  cefalópodos (`pulpo`, `calamar`) es correcto (moluscos).
- **Alérgenos**: B6.
- **`energy_note`**: datos correctos; texto técnico (S6). 39 alimentos con nota; los 34 de «factores de
  Atwater específicos» incluyen verduras y frutas donde la discrepancia es inocua: aceptable.
- **Gastronomía española**: el catálogo contiene los alimentos de la dieta mediterránea, pero el
  planificador no tiene noción de plato: aceite de oliva compite con canola, girasol y coco; legumbre
  en el desayuno; ver B7 y C12.
- **Tono**: el aviso `tolerance_not_met` no debe aparecer en más de una cuarta parte de los planes y su
  texto debe ser informativo, no correctivo (C13).

## 6. Diffs propuestos

Todos los diffs son para que el propietario los aplique. Los identificadores de ejercicios son reales
(`@ 7455efae`).

### 6.1 `specs/engine-rules.yaml` (motor-rutinas)

```diff
 difficulty:
   cap: { beginner: 2, intermediate: 2, advanced: 2 }
   accessory_extra: { beginner: 0, intermediate: 0, advanced: 1 }
+  relax_difficulty_for: [advanced]      # solo accesorios; principiante/intermedio nunca superan el tope

 scoring:
   pattern_exact: 40
   target_group: 25
   staple_in_main: 15
+  staple_in_accessory: 12
   favorite: 10
   used_other_day: -30
   same_variant_group: -15
   above_difficulty: -10
   unilateral_in_strength_main: -20
-  loadable_in_main: 10
+  loadable_in_main: 10          # aprobado como extensión de §7.2 (ADR pendiente); ver Riesgo 4
+  barbell_in_strength_main: 10  # solo goal strength, intermedio/avanzado, equipment barbell|trap_bar
-loadable_equipment: [barbell, dumbbell, ez_bar, trap_bar, machine, smith, sled, cable, kettlebell, weighted]
+loadable_equipment:
+  beginner:     [dumbbell, machine, smith, sled, cable, kettlebell]
+  intermediate: [barbell, dumbbell, ez_bar, trap_bar, machine, smith, sled, cable, kettlebell, weighted]
+  advanced:     [barbell, dumbbell, ez_bar, trap_bar, machine, smith, sled, cable, kettlebell, weighted]
+main_requires_compound: true

-relaxation_order: [difficulty, staple, target_group, pattern_affinity]
+relaxation_order: [staple, target_group, pattern_affinity, difficulty]

 allocation:
   bounds_by_role:
-    main: [2, 5]
-    accessory: [1, 4]
+    main: from_prescription       # [sets.min, sets.max] de prescription.yaml; principiante = sets.min
+    accessory: [2, 4]             # nunca menos de 2 series; si no hay tiempo, se elimina el slot
     core: [1, 4]
+  accumulation_extra_from_week: 3  # el +1 serie solo desde la semana 3 y solo intermedio/avanzado

+# Ejercicios que nunca se eligen solos (salvo favorite_exercise_ids)
+skill_gated:
+  name_en_any: ["handstand", "planche", "maltese", "front lever", "back lever", "iron cross",
+                "muscle up", "muscle-up", "kipping", "dragon flag", "l-sit", "v-sit",
+                "skin the cat", "pistol", "one leg squat", "clean", "snatch", "jerk",
+                "push press", "thruster", "depth jump", "drop push", "clap push", "plyo push",
+                "turkish get up"]
+contraindicated_default:
+  name_en_any: ["behind neck", "behind head", "rear pull-up", "wide grip rear", "upright row"]
+  ids: ["0086", "0747", "0772", "0788", "1325", "1367", "0670", "1718", "1748",
+        "0119", "0120", "0121", "0123", "0246", "0363", "0437", "0775", "1765"]
+fixture_gated:                     # se excluyen con los presets bodyweight y home_bands
+  presets: [bodyweight, home_bands]
+  name_en_any: ["pull-up", "pull up", "chin-up", "chin up", "hanging", "dip", "ring",
+                "suspended", "suspension", "straps", "parallel bars", "straight bar",
+                "toes to bar", "on bench", "bench", "hyperextension", "glute-ham",
+                "donkey", "box jump", "captains chair"]
+  ids: ["2400"]
+low_quality_ids: ["0100", "0543", "0777"]  # instrucciones ≠ nombre; no auto-seleccionar

 warmup:
   cardio_share: 0.5
-  specific_items: 1
+  specific_items: 1
+  specific_pick: lowest_difficulty_staple   # nunca variantes exóticas ni contraindicadas
+  cardio_rotation: true
 recovery:
-  cardio_minutes: [5, 20]
+  cardio_minutes: [20, 30]
+  cardio_equipment_any: [bike, elliptical, stepmill]
+  cardio_ids_any: ["3666", "2311"]
+  mobility_items: 6
```

### 6.2 `specs/periodization.yaml`, `specs/volume-targets.yaml`, `specs/split-templates.yaml` (motor-rutinas)

```diff
 strength_undulation:
   enabled_for: [intermediate, advanced]
-  heavy_day: { reps_shift: -2, rir: 1 }
-  medium_day: { reps_shift: 0, rir: 2 }
+  applies_to: { mechanic: compound, load_type: external, equipment_any: [barbell, trap_bar, smith, machine, cable, dumbbell] }
+  excluded_ids: ["0044", "0090", "0115", "0749", "3759"]
+  heavy_day:  { reps_shift: -1, min_reps: 3, rir_floor: { intermediate: 2, advanced: 1 } }
+  medium_day: { reps_shift: 1, rir: 2 }
```

```diff
 set_credit: { target: 1.0, relevant_secondary: 0.5 }
+secondary_credit_by_group: { arms: 0.3 }
```

```diff
   upper_a:
     slots:
       - { pattern: horizontal_push,  role: main,      group: chest,      priority: 1 }
       - { pattern: horizontal_pull,  role: main,      group: back,       priority: 1 }
       - { pattern: vertical_push,    role: accessory, group: shoulders,  priority: 2 }
-      - { pattern: vertical_pull,    role: accessory, group: back,       priority: 2 }
+      - { pattern: chest_fly,        role: accessory, group: chest,      priority: 2 }
       - { pattern: elbow_flexion,    role: accessory, group: arms,       priority: 3 }
       - { pattern: elbow_extension,  role: accessory, group: arms,       priority: 3 }
...
-  arms:         { min_days: 3, append_block: { patterns: [elbow_flexion, elbow_extension], to: "*" } }
+  arms:         { min_days: 3, append_block: { patterns: [elbow_flexion, elbow_extension], to: [upper_a, upper_b, push, pull] } }
```

### 6.3 `specs/overrides/staples.yaml` y `enrichment-overrides.yaml` (ingesta)

```diff
-  squat:           ["0043", "0042", "0046", "0770", "0739", ... "3533", "3119", "1759"]
+  squat:           ["0043", "0042", "0770", "0739", "0413", "0534", "1760", "1004", "3533", "3119"]
-  hinge:           ["0032", "0085", "0117", "0811", "0044", "0549", "0991", "1459", "1757", "0489", "0488"]
+  hinge:           ["0032", "0085", "0117", "0811", "0549", "0991", "1459", "1757", "3292"]
-  horizontal_push: [..., "0251", ...]
+  horizontal_push: ["0025", "0047", "0577", "2144", "0748", "0289", "0314", "1254", "0493", "0662", "3211"]
-  vertical_push:   ["0091", "0587", "0774", "0405", "0426", "0553", "0997", "0471", "3302"]
+  vertical_push:   ["0091", "0587", "0774", "0405", "0426", "0997"]
-  knee_flexion:    ["0586", "0599", "0496", "3193"]
+  knee_flexion:    ["0586", "0599", "0696", "1766"]
-  core_anti_extension: ["0276", "2135", "0857"]
+  core_anti_extension: ["0276", "2135", "0857", "3239"]
```

```yaml
# enrichment-overrides.yaml#by_id (campos nuevos: equipment_code)
"0044": { role: accessory, is_staple: false }
"0471": { role: accessory, is_staple: false, load_type: bodyweight }
"3302": { role: accessory, is_staple: false }
"0251": { difficulty: 3 }
"0677": { difficulty: 3 }
"1367": { difficulty: 3 }
"0670": { difficulty: 3 }
"3193": { difficulty: 3 }
"0496": { difficulty: 3 }
"0555": { movement_pattern: knee_extension }
"0858": { movement_pattern: cardio, role: cardio, load_type: time }
"0352": { mechanic: compound }
"1625": { mechanic: compound }
"0812": { mechanic: compound }
"0813": { mechanic: compound }
"0814": { mechanic: compound, difficulty: 2 }
"0815": { mechanic: compound }
"2400": { equipment_code: cable }
```

Regla nueva en `keywords.difficulty_level_3_any` (o equivalente): `"pull-up"`, `"chin-up"`,
`"chin up"`, `"dip"` cuando `equipment == body weight` y sin `assisted|band|negative|kneeling|inverted|
bench|on floor|between benches|bench leg` en el nombre; los `by_id` de arriba prevalecen. Excepción de
la celda `vertical_push × bodyweight` y `hinge × bodyweight` en el test de matriz de staples
(documentar en `docs/enrichment-report.md`).

### 6.4 `nutrition/forja_nutrition/data/foods.json` (motor-nutricion)

```diff
 avena:           allergens: [] -> ["gluten"]
 cuscus:          allergens: [] -> ["gluten"]
 cerveza:         allergens: [] -> ["gluten"]
 leche_almendra:  allergens: [] -> ["tree_nuts"]; macro_role: protein -> carb
 cacahuete:       allergens: [] -> ["tree_nuts"]   # hasta CC-0002 (peanuts)
 mantequilla_cacahuete: allergens: [] -> ["tree_nuts"]
 altramuz:        allergens: [] -> ["tree_nuts"]   # hasta CC-0002; reacción cruzada con cacahuete
```

Nuevos campos por alimento (todos los 193): `max_portion_g`, `meal_slots`, `weekly_max` (procesados).
Valores mínimos del primer lote:

| Alimento | `max_portion_g` | `meal_slots` | `weekly_max` |
|---|---|---|---|
| semilla_chia, semilla_lino | 25 | breakfast, snack | — |
| sesamo | 15 | lunch, dinner | — |
| anchoa_lata | 30 | lunch, dinner | 2 |
| higado_vacuno | 100 | lunch, dinner | 1 |
| bacon, salchicha_cerdo, jamon_cocido, jamon_curado | 60 | breakfast, lunch, dinner | 2 |
| legumbres secas, pescado, marisco, carne | 4 × típica | lunch, dinner | — |
| verduras de hoja y frutas | 2 × típica (≤ 300 g) | según categoría | — |
| leche/yogur | 500 g | breakfast, snack | — |
| aceite_oliva | 30 | todos | — |
| aceite_coco, aceite_girasol | 10 | lunch, dinner | — |

`specs/nutrition.yaml` (copiar a `data/nutrition.yaml`): `fat: { max_pct_kcal: 0.35 }`,
`tolerances.fat_over_allowed: 0.20` (informativo, no genera aviso), `protein_bodyweight_basis:
adjusted_if_bmi_ge: 30`.

## 7. Criterios de re-verificación (Puerta 1)

Un hallazgo se cierra con evidencia reproducible. El revisor repite esto tras F1b-FIX:

1. Motor: `make test-engine` al 100 %/95 %; nuevos tests de propiedad: (a) principiante e intermedio
   ≤ dificultad 2; (b) nada de `skill_gated`, `contraindicated_default` ni `fixture_gated` en presets
   correspondientes; (c) `sets ≤ prescription.max (+1 desde semana 3)`; (d) en `full_gym`, el slot
   principal de squat/hinge nunca resuelve a `1760`, `3533`, `0044` habiendo alternativa; (e) heavy day
   ≥ 3 repeticiones y `excluded_ids` sin ondulación. `ENGINE_VERSION` subida. Las listas `name_en_any` se comparan por palabra completa (p. ej. `ring` no debe casar con «spring»).
2. Snapshots regenerados y **re-revisados** por este agente: los 12 sin BLOQUEANTE; volúmenes: ningún
   grupo < 85 % del mínimo salvo por equipamiento; brazos dentro de ±15 %.
3. Ingesta: `forja-ingest report` con los nuevos staples y las dos celdas exentas documentadas;
   `names_es.json` con las correcciones de §5.3; ejercicios `low_quality_ids` marcados.
4. Nutrición: `make test-nutrition` al 100 %; test de auditoría de alérgenos; barrido de 288 perfiles
   con: 0 días con grasa > 35 % kcal, `tolerance_not_met` en ≤ 25 % de planes, 0 desayunos con
   legumbre/pescado/carne guisada, 0 ítems fuera de `max_portion_g`.
5. Nuevo informe `docs/reviews/f1b-recheck.md` con veredicto por BLOQUEANTE.

## 8. Reparto por propietario

| Propietario | BLOQUEANTES | CAMBIOS | SUGERENCIAS |
|---|---|---|---|
| **motor-rutinas** | B1, B2, B3 (parte motor), B4, B5 (parte filtro), B8 | C2, C3, C4, C5, C6, C7, C8, C9, C16 | S1, S3, S4, S5, S7, S8 |
| **ingesta-datos** | B3 (staples y overrides), B5 (`2400`, ediciones de CC) | C1, C10, C11 | S2 (parte staples) |
| **motor-nutricion** | B6, B7 | C12, C13, C14, C15 | S6 |
| **arquitecto** | (apoya B5: CC v1.1 `pullup_bar`/`bench`; ADR para `loadable_in_main`) | C17 | — |
| **frontend-ui** | — | copy del preset `bodyweight` y `tolerance_not_met` (C13) | — |
| **orquestador** | asignar F1b-FIX y convocar la re-revisión | — | — |

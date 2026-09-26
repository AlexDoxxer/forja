# Handoff · Fase 1b · experto-entrenamiento

Rama: `f1b/experto-entrenamiento` (desde `main` @ `0fbf678`; sin fusionar). Fecha: 2026-09-26.
Tareas: F1b-EXP-01 … 06 (un único informe). Zona escrita: `docs/reviews/` y este handoff. No se ha
tocado `specs/`, `engine/`, `nutrition/`, `backend/` ni `docs/TASKS.md` (lo actualiza el orquestador).

## Resumen

Revisión de dominio completa de enriquecimiento, staples, nombres ES (31 dudosos + 150 muestreados),
tablas `specs/`, los 12 snapshots del motor y el motor de nutrición. Informe:
`docs/reviews/f1b-experto-entrenamiento.md`.

**Veredicto: Puerta 1 no superada. 8 BLOQUEANTES, 17 CAMBIOS, 8 SUGERENCIAS.**

Los BLOQUEANTES son:

| ID | Resumen | Propietario |
|---|---|---|
| B1 | El filtro de slot usa `target_muscle` del dataset: 46/58 sentadillas y 52/56 bisagras (peso muerto, sentadilla y prensa de barra) quedan excluidas; en gimnasio salen goblet, sentadilla con peso corporal y buenos días como principales | motor-rutinas |
| B2 | La asignación de series supera `prescription.yaml` (5 series de un principal donde la tabla dice 3; principiantes no al mínimo) | motor-rutinas |
| B3 | La relajación de dificultad mete ejercicios de dificultad 3 (cargada colgante, flexión en pino, pino) en planes de principiante; staples gimnásticos | motor-rutinas + ingesta |
| B4 | Días pesados de fuerza a 1–4 reps (buenos días a 1–4 reps) | motor-rutinas |
| B5 | Presets `bodyweight`/`home_bands` devuelven ejercicios que exigen barra de dominadas, banco, anillas o máquina (62/245 del grupo) | ingesta + motor-rutinas |
| B6 | Alérgenos mal etiquetados: avena, cuscús, cerveza (gluten), leche de almendra (frutos secos), cacahuete en perfil con alergia a frutos secos | motor-nutricion |
| B7 | Planes de comida irreales: sin porción máxima ni idoneidad por comida; `tolerance_not_met` en 286/288 planes; grasa > 35 % kcal en el 7,6 % de los días | motor-nutricion |
| B8 | Ejercicios contraindicados se seleccionan por defecto (jalón tras nuca como calentamiento) | motor-rutinas |

## Ficheros tocados

```
docs/reviews/f1b-experto-entrenamiento.md   (nuevo)
docs/handoffs/f1b-experto-entrenamiento.md  (nuevo)
```

## Decisiones (y ADRs)

Detalle y diffs exactos en el informe §1 y §6.

1. **Riesgo 1 (pino en principiantes)**: la dificultad no se relaja nunca para principiante e
   intermedio; nueva lista `skill_gated` (gimnásticos, olímpicos, balísticos) fuera de la selección
   automática; sin material no existe empuje vertical seguro en el dataset, así que el slot cae por
   afinidad a `horizontal_push` con aviso; celda `vertical_push × bodyweight` exenta del mínimo de
   2 staples.
2. **Riesgo 2 (volumen en 6 slots)**: la prescripción manda sobre la asignación; el déficit se avisa.
   Crédito secundario de brazos 0,3; accesorio mínimo 2 series; `upper_a` cambia `vertical_pull`
   accesorio por `chest_fly`; bloques de brazos solo en días de torso/empuje/tirón.
3. **Riesgo 3 (1–4 reps)**: se corrige a día pesado 3–5 reps (suelo 3), medio 4–7, RIR ≥ 2 en
   intermedios; ondulación solo en compuestos cargables (fuera buenos días, kettlebell, goblet).
4. **Riesgo 4 (`loadable_in_main +10`)**: aprobado con condiciones (por nivel, revalidar tras B1, no
   en resistencia) y con ADR pendiente (no está en MASTER §7.2).
5. **Riesgo 5 (grasa en veganos/sin frutos secos)**: no se sube la tolerancia del contrato; techo del
   35 % kcal, objetivo asimétrico, ítem de grasa opcional, aceite de oliva preferente, y
   `tolerance_not_met` solo para kcal/proteína/techo de grasa.
6. Nombres ES: 31 dudosos resueltos (16 APROBADOS, incluido el duplicado declarado, y 15 CAMBIO). Regla: ante
   duda el nombre sigue la instrucción ES, no la etiqueta `target` (afecta a `0858`, `0555`, `3234`).

## Cómo verificar

Todo es reproducible desde el worktree sin modificar nada. Ejemplos (las cifras del informe salen de
estos comandos):

```bash
export PATH=$HOME/.local/bin:$PATH
# B1: desajuste patrón ↔ grupo del target_muscle en el catálogo real (fixture del motor)
cd engine && uv run --locked python - <<'PY'
import json, yaml, collections
R = '..'
c = json.load(open(f'{R}/engine/tests/fixtures/catalog.json'))
canon = yaml.safe_load(open(f'{R}/specs/muscle-normalization.yaml'))['canonical']
pg = yaml.safe_load(open(f'{R}/specs/engine-rules.yaml'))['pattern_groups']
for p in ('squat', 'hinge', 'lunge'):
    xs = [x for x in c if x['movement_pattern'] == p]
    bad = [x for x in xs if canon[x['target_muscle']]['group'] != pg[p]]
    print(p, len(xs), 'desajustados', len(bad))
PY
# Volumen de los 12 snapshots frente al rango (±15 %): parsear las tablas «Volumen semanal» de
# engine/tests/golden/*.md y comparar «Planificado» con «Objetivo».
# B7/Riesgo 5: barrido de nutrición (288 perfiles = 4 cuerpos × 4 dietas × 3 alérgenos × 3 objetivos
# × 3-4 comidas). Recorrer plan_week(...) y agregar día a día:
#   desviación de grasa (day.deviation.fat), 9*grasa/kcal, gramos máximos por ítem, desayunos con
#   legumbres/pescado/carne, y presencia de tolerance_not_met en plan.notices.
cd ../nutrition && uv run --locked python -c "from forja_nutrition.planner import plan_week; print('ok')"
```

Tras F1b-FIX, el revisor repite el barrido y los criterios de la §7 del informe (0 días con grasa >
35 % kcal, `tolerance_not_met` ≤ 25 % de planes, 0 desayunos con legumbre/pescado/carne, propiedades
del motor, 12 snapshots sin BLOQUEANTE) y publica `docs/reviews/f1b-recheck.md`.

## Métricas

| Concepto | Valor |
|---|---|
| Ejercicios muestreados (enriquecimiento) | 100 (91 correctos, 9 con error o duda) |
| Nombres revisados | 150 muestreados + 31 dudosos (0 calcos graves en el muestreo; 4 correcciones) |
| Staples revisados | 144 (11 a retirar o degradar, 3 celdas del test a exentar) |
| Snapshots revisados | 12 (9 BLOQUEANTE, 3 CAMBIOS; los 12 requieren regeneración tras B1) |
| Alimentos auditados | 193 (7 etiquetas de alérgeno a corregir) |
| Planes de nutrición simulados | 288 perfiles / 2.016 días |
| Hallazgos | 8 BLOQUEANTE · 17 CAMBIO · 8 SUGERENCIA |

## Riesgos/pendientes

1. Los 12 snapshots cambiarán casi por completo al corregir B1; la re-revisión es obligatoria (tarea
   nueva `F1b-RECHECK`).
2. El enum `EquipmentCode` del contrato está congelado: no hay código para «barra de dominadas» ni
   «banco»; B5 se resuelve con exclusión por preset y queda abierto un CC v1.1.
3. `loadable_in_main` (extensión de §7.2) necesita ADR para no divergir del MASTER_PROMPT.
4. La calidad de las instrucciones ES del dataset es irregular (plantillas genéricas repetidas);
   algunas entradas (`0100`, `0543`, `0777`) quedan excluidas de la selección automática.
5. Las cifras de nutrición dependen de la semilla derivada y de la lista de alimentos actual; cualquier
   cambio de `foods.json` obliga a repetir el barrido.

## Peticiones a otros agentes

- **motor-rutinas**: B1, B2, B3 (relajación y `skill_gated`), B4, B5 (filtro `fixture_gated`), B8;
  CAMBIOS C2–C9 y C16; subir `ENGINE_VERSION` y regenerar snapshots; diffs en informe §6.1–6.2.
- **ingesta-datos**: B3 (staples, `load_type` de `0471`), B5 (`equipment_code` de `2400`; admitir el
  campo en `by_id`); CAMBIOS C1, C10, C11 (diffs en §6.3 y §5.3); actualizar
  `docs/enrichment-report.md` con las celdas exentas.
- **motor-nutricion**: B6, B7, C12–C15; diffs en §6.4; test de auditoría de alérgenos; repetir el
  barrido de 288 perfiles y adjuntar resultados.
- **arquitecto**: ADR sobre `loadable_in_main`; CC v1.1 para `pullup_bar`/`bench` en `EquipmentCode`;
  test de igualdad entre `specs/nutrition.yaml` y `nutrition/.../data/nutrition.yaml` (C17).
- **frontend-ui**: copy del preset `bodyweight` y del aviso `tolerance_not_met` (no punitivo).
- **orquestador**: encargar F1b-FIX con este reparto, actualizar `docs/TASKS.md` (F1b-EXP-01…06 →
  hechas) y convocar la re-revisión.

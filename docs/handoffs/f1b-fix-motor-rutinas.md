# Handoff · F1b-FIX · motor-rutinas

## 1. Resumen
Se aplican los hallazgos del informe `docs/reviews/f1b-experto-entrenamiento.md` asignados a
motor-rutinas: B1, B2, B3 (parte motor), B4, B5 (parte filtro), B8 y los cambios C2–C9 y C16.
`ENGINE_VERSION` sube a **0.2.0** (`engine/forja_engine/version.py`, `engine/pyproject.toml`) y los
12 snapshots golden (`.json` y `.md`) se regeneran. Rama `f1b/fix-motor-rutinas`.

## 2. Ficheros tocados
- `engine/forja_engine/`: `select.py` (gating, grupo por patrón, relajación, puntuación, avisos,
  calentamiento), `volume.py` (`training_group`, créditos secundarios por grupo), `allocate.py`
  (límites desde prescripción), `periodize.py` (ondulación B4, +1 serie desde semana 3),
  `prescribe.py` (techo C9, series de aproximación C7, movilidad por lado), `timefit.py`
  (accesorios nunca a 1 serie, orden de bloques C6), `tables.py` (modelos nuevos), `generator.py`.
- `specs/engine-rules.yaml`, `prescription.yaml`, `periodization.yaml`, `volume-targets.yaml`,
  `split-templates.yaml`.
- `docs/adr/0012-loadable-in-main-scoring.md` (+ fila en `docs/adr/README.md`).
- Tests: `engine/tests/test_f1b_fixes.py` (nuevo), ajustes en `test_edges.py`, `test_pipeline.py`,
  `test_tables.py`, y `engine/tests/golden/*`.

## 3. Decisiones (y ADRs)
- ADR 0012 aprueba `loadable_in_main: +10` con las condiciones del experto (lista por nivel, no en
  `endurance`, revalidada tras B1).
- Coincidencia de listas `name_en_any` por **palabra completa** (con plural `s`), no subcadena.
- `main_requires_compound` solo en slots de patrones compuestos y salvo que el patrón esté evitado
  (así `avoid_patterns` puede seguir sustituyendo hinge por curl femoral).
- Slots `lunge` de las plantillas pasan de grupo `glutes` a `quads` (coherente con B1, `lunge → quads`).
- Se añade `low_quality_ids: [0100, 0543, 0777]` tratado como `skill_gated` (excluye `0100` y `0543`
  del lado motor, como pidió el coordinador).
- Aviso específico de `slot_relaxed` para empuje vertical → flexiones y tirón vertical → remos
  (presets sin barra de dominadas). No se añadió ningún `PlanWarningCode` nuevo.
- Recuperación activa: cardio limitado a bici/elíptica/escaladora/caminata, 20–30 min, y 5 slots
  de movilidad en la plantilla `active_recovery`.

## 4. Cómo verificar
```
cd engine && uv run pytest -x -q -k "not combinations"
cd engine && uv run pytest            # incluye 1.890 combinaciones y propiedades
cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy --strict forja_engine tests
FORJA_UPDATE_GOLDEN=1 uv run pytest tests/test_golden.py   # solo para regenerar snapshots
```

## 5. Estado por hallazgo

| ID | Estado | Evidencia |
|---|---|---|
| B1 | hecho | `volume.training_group`; `test_full_gym_main_squat_and_hinge_use_real_lifts`; snapshots 02/03/10 sin `1760`/`3533`/`0044` como principal |
| B2 | hecho | `allocate.role_bounds` desde `prescription.yaml`; principiante en el mínimo; `test_safety_and_bounds_properties` (sets ≤ max, +1 desde semana 3) |
| B3 | hecho | `relax_difficulty_for: [advanced]` solo accesorios, `skill_gated`, `low_quality_ids`, aviso de flexiones; propiedad dificultad ≤ 2 |
| B4 | hecho | `periodization.yaml` (3-5 / 4-7, RIR ≥ 2 intermedios, `applies_to`, `excluded_ids`); snapshots 04/05; texto cita los rangos reales |
| B5 | hecho (parte motor) | `fixture_gated` por preset; propiedad en `bodyweight` y `home_bands`; aviso «sin barra de dominadas» |
| B8 | hecho | `contraindicated_default` fuera de `usable` (calentamiento incluido) salvo favoritos; upright rows excluidos |
| C2 | hecho | `staple_in_accessory: 12`, `main_requires_compound` |
| C3 | hecho | `secondary_credit_by_group: {arms: 0.3}`, bloque de brazos solo en upper_a/upper_b/push/pull |
| C4 | hecho | `upper_a` con `chest_fly` en lugar de `vertical_pull` |
| C5 | hecho | ADR 0012 + `barbell_in_strength_main: 10` |
| C6 | hecho | accesorios ≥ 2 series (el slot se elimina si no cabe); compuestos en series rectas antes de aislamientos y superseries (`order_working_blocks`) |
| C7 | parcial | (a) rotación del cardio de calentamiento, (b) específico = staple de menor dificultad y series de aproximación 40/60/80 % en fuerza, (d) `per_side` solo en ejercicios unilaterales: hechos. (c) la vuelta a la calma no se reordena por solapamiento con los grupos del día: pendiente |
| C8 | hecho | `recovery` con cardio de bajo impacto, 20–30 min, 5 ejercicios de movilidad; test `test_recovery_day_is_low_impact_with_mobility` |
| C9 | parcial | techo 12 / suelo 5 en dominadas, fondos y pino con peso corporal (`bodyweight_rep_limits`) con nota en el ejercicio; la preferencia de remo sobre tirón vertical en circuitos solo ocurre por B5 |
| C16 | hecho | con `lower_back` evitado se excluye `hinge` y `lumbar_avoid`; snapshot 12 sin remo inclinado |

## 6. Métricas
Cobertura, ruff y mypy: ver resultado final de la suite completa indicado en el mensaje de entrega.
Benchmark de p95: sin cobertura `generate` tarda ~25 ms; bajo cobertura y con la máquina cargada
(load average ~9) superó puntualmente los 150 ms (165–197 ms), sin regresión propia medible.
Volúmenes: los avisos `volume_out_of_range` por defecto son la consecuencia esperada de B2 (los
principales ya no inflan series); brazos dentro de rango en los snapshots 02, 03, 05, 09 y 11 no está
garantizado: el experto debe re-revisar.

## 7. Riesgos, pendientes y peticiones
- **Merge de main bloqueado**: el sistema de permisos denegó `git merge main`. Debe hacerlo el
  coordinador o el usuario. Tras fusionar la ingesta hay que regenerar el fixture
  (`forja-ingest export-cards --output ../engine/tests/fixtures/catalog.json`, ver
  `docs/handoffs/f1-ingesta-datos.md`) y los snapshots (`FORJA_UPDATE_GOLDEN=1 uv run pytest
  tests/test_golden.py`), y ejecutar la suite completa. Los snapshots actuales se generaron con el
  fixture anterior.
- C7(c) y la parte de circuitos de C9 quedan abiertas; S1, S3, S4, S5, S7 y S8 no se han tocado.
- **backend-api**: ejecutar `uv lock --project backend` (el motor pasa a 0.2.0) y actualizar
  constantes de `generator_version` en sus tests.
- Wizard (frontend): texto del preset `bodyweight` propuesto por el experto (B5.6).

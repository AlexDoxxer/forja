# Handoff · Fase 1 · motor-rutinas

Rama: `f1/motor-rutinas` (incluye `main` con la ingesta fusionada; sin fusionar a `main`).
Fecha: 2026-09-25. Versión del motor: `ENGINE_VERSION = 0.1.0`.

## Resumen

`engine/forja_engine/` implementa MASTER_PROMPT §7 completo como paquete puro y
determinista (sin BD, red, reloj, entorno ni `random` global):

- **Pipeline de 9 pasos**, un módulo por paso: `normalize` (defectos, equipamiento resuelto,
  semilla SHA-256, avisos de seguridad) → `split` (tabla §7.3 + sustituciones y bloques por
  énfasis) → `volume` (objetivo semanal × énfasis con suelo de mantenimiento; créditos 1,0 /
  0,5) → `allocate` (reparto serie a serie, ≤ 10 series efectivas por grupo y sesión) →
  `select` (filtro, puntuación de §7.2, desempate con `random.Random(seed, semana, día, slot)`,
  cadena de relajación dificultad → staple → músculo → patrón afín, 3 alternativas) →
  `prescribe` (§7.5, principiantes RIR +1 y series mínimas, modificadores de sexo) →
  `timefit` (estimación de §7.2 paso 7 y ajuste a–d; `main` solo como último recurso) →
  `periodize` (RIR por semana, +1 serie/grupo/semana, descarga 55 %, ondulación de fuerza,
  semanas `intensification`) → `compose` (DTOs, volumen, avisos, `rationale_es`).
  Orquestado por `generator.generate(input, catalog, tables=None)`.
- **Operaciones** (`ops.py`): `validate_plan`, `rebalance_after_edit`, `swap_exercise`,
  `regenerate_day` con la firma de `contracts/domain.md` §5.5 (más `tables` opcional).
- **Progresión** (`progression.py`): doble progresión, incrementos por tipo de ejercicio,
  bajada tras 2 fallos, peso corporal (+reps o variante más difícil), isométricos, e1RM de
  Epley y aproximación 40/60/80 % con calculadora de discos. Ninguna función recibe el sexo.
- **Tablas** (`tables.py`): todos los YAML de `specs/` validados con Pydantic estricto y
  referencias cruzadas; `tables_hash` SHA-256 del JSON canónico; `TablesError` al cargar.
- **Fixture**: `engine/tests/fixtures/catalog.json` = 1.324 `ExerciseCard` reales
  exportadas con `forja-ingest export-cards` (F1-ENG-19 hecha tras fusionar la ingesta).

## Ficheros tocados

| Zona | Ficheros |
|---|---|
| Motor | `engine/forja_engine/{__init__,version,models,tables,texts,draft,normalize,split,volume,allocate,select,prescribe,timefit,periodize,compose,generator,ops,progression}.py` |
| Tests | `engine/tests/{helpers,golden_profiles,test_models,test_tables,test_pipeline,test_edges,test_sex,test_combinations,test_properties,test_ops,test_progression,test_golden,test_benchmark}.py`, `engine/tests/fixtures/{__init__.py,catalog.json}`, `engine/tests/golden/` (12 × `.json` + `.md` + `README.md`) |
| Tablas del motor (ADR 0002: propiedad de motor-rutinas) | **nuevo** `specs/engine-rules.yaml`; ninguna otra tabla modificada |
| Docs | este handoff, `docs/TASKS.md` (estado F1-ENG-01…20 y nombre del handoff), `docs/CONTRACT_CHANGES.md` (CC-0003) |

Commits (Conventional Commits, rama `f1/motor-rutinas`):

```
cb6e40b feat(engine): add immutable domain DTOs and spanish text helpers
6dc9131 feat(engine): load and validate specs tables with tables hash
687b1e3 test(engine): add fixture catalog built from the pinned dataset
6d78515 feat(engine): add input normalization, split choice and volume targets
eebea2f feat(engine): add volume allocation, exercise selection and prescription
3522fd5 feat(engine): add time fitting, periodization and plan composition
1c8131e feat(engine): add progression suggestions, e1rm and warmup ramps
47f209d feat(engine): add plan operations and public api
65c1a04 test(engine): cover the 1890 goal-days-level-sex-preset combinations
4bdf6d5 test(engine): add hypothesis properties for plan invariants and determinism
3f3eaf5 test(engine): validate tables, dto invariants and openapi compatibility
53bf3b7 test(engine): prove sex never excludes exercises or limits loads
06a0523 feat(engine): let accumulation weeks exceed the per-exercise cap by one set
20f23bc test(engine): cover pipeline steps and degraded paths
e56df37 test(engine): cover plan validation, rebalance, swap and day regeneration
2967b4c test(engine): cover progression suggestions, e1rm and plate math
1a782eb test(engine): cover allocation, time-fit, volume and swap edge cases
525d2bb Merge branch 'main' into f1/motor-rutinas
e64f29c fix(engine): keep version 0.1.0 so the backend lockfile stays valid
2cfbe53 test(engine): regenerate fixture catalog with forja-ingest export-cards
7890dae fix(engine): pick cardio-pattern warm-ups and list every relaxation in warnings
701a389 feat(engine): prefer loadable equipment in main slots
eaa1784 test(engine): add 12 golden snapshots with readable renderings
17a8d8c test(engine): add p95 benchmark and finisher fallback test
(+ docs: handoff, tareas y CC-0003)
```

## Decisiones (y ADRs)

Sin ADR nuevo (`docs/adr/` es del arquitecto); las constantes nuevas viven en
`specs/engine-rules.yaml` para que el experto pueda revisarlas sin tocar código.

1. **`specs/engine-rules.yaml`** (nuevo): defectos `include_*` por objetivo, pesos de
   puntuación, orden de relajación, límites de series por ejercicio, grupo de los slots de
   énfasis, «secundarios relevantes» por patrón (squat → glúteo; bisagra → glúteo/isquios;
   empujes y tirones → brazos; zancada → cuádriceps/glúteo), pares antagonistas,
   calentamiento/calma/finisher/recuperación y pasos de carga para la progresión.
2. **Nivel de dificultad**: tope 2 para los tres niveles, +1 en accesorios para avanzados
   (con 1 para principiantes, mancuernas y peso corporal estándar quedarían fuera y casi
   todo slot se relajaría). La dificultad 3 conlleva −10.
3. **Relajación**: se sigue el orden literal de §7.2 (dificultad → staple → músculo →
   patrón afín). Avisan `slot_relaxed` la dificultad, el músculo y el patrón; quitar la
   exigencia de staple no avisa (es lo normal con material doméstico). Si el hueco toca un
   músculo/patrón evitado, el aviso es `avoided_muscle_substituted`. Sin candidatos: el slot
   se elimina con `equipment_insufficient` (habría con otro material) o `slot_dropped`.
4. **Extensión de puntuación** `loadable_in_main: +10` para material con carga progresiva en
   slots `main` (sin ella, en gimnasio salían flexiones de rodillas como press principal por
   empate aleatorio). No afecta si solo hay bandas o peso corporal. **Pendiente de experto.**
5. **Peso corporal siempre disponible** (`always_available_equipment`): se añade a la lista
   resuelta de cualquier preset.
6. **Entrada que no deja ningún ejercicio** (exclusiones/evitados/equipamiento) ⇒
   `pydantic.ValidationError` (`no_exercises_available`), coherente con «entradas inválidas ⇒
   ValidationError». Un día sin ningún slot cubierto recibe el ejercicio disponible más útil
   y el aviso `empty_day`; nunca excepción por falta de candidatos.
7. **Bloques**: cada ejercicio de series rectas en su bloque `main`; superseries de 2 con
   `rounds` = series de cada miembro y `rest_between_rounds_s` = mayor descanso; resistencia
   = un bloque `circuit`. Calentamiento = cardio suave (se prefieren los de rol `warmup`) +
   versión ligera del primer patrón principal; calma = 2 estiramientos de los grupos del día.
8. **Descansos**: `main` = punto medio del rango (múltiplo de 15 s); accesorio = punto medio
   (× 0,85 para mujeres, nunca por debajo del mínimo del rango); ajuste (d) al mínimo del
   rango. En **circuitos** el mínimo que exige `validate_plan` es el de accesorio (30 s): la
   tabla de resistencia (30–60 s) choca con `min_rest_s.main = 90` y la recuperación ocurre
   entre rondas.
9. **Ajuste al tiempo**: orden literal a → b → c → d; en (c) se quita primero el finisher. El
   límite usa minutos enteros (`floor(presupuesto × 1,05)`) para que `estimated_minutes`
   cumpla la propiedad sin redondeos.
10. **Periodización**: RIR semanal acotado al rango del rol (+1 principiantes); ondulación de
    fuerza pesado/medio alternando días de entrenamiento (RIR = máx(día, semana)); semanas con
    RIR ≤ 1 = `intensification`; principiantes sin series extra (progresión lineal). La
    acumulación puede superar en 1 serie el máximo por ejercicio (`accumulation_extra_cap`),
    si no los avanzados no progresarían en volumen.
11. **Sexo**: solo descanso de accesorios, +1 rep en aislamiento y +5 demostrador; el filtro de
    candidatos no recibe el sexo (probado para los 5 presets y todas las plantillas).
12. **`regenerate_day`**: reconstruye con semilla nueva (derivada de la del plan y de los
    ejercicios actuales si `seed = null`) penalizando los ejercicios actuales como «ya usados»
    y sustituye solo ese día en todas las semanas. **`swap_exercise`** conserva series, RIR
    y descanso y convierte reps ↔ duración si cambia el tipo de carga. Direcciones o
    reemplazos imposibles ⇒ `PlanOperationError(ValueError)` (la API ⇒ 422).
13. **`ENGINE_VERSION` se mantiene en 0.1.0**: `backend/uv.lock` fija la versión del paquete
    editable; subirla obliga a regenerar el lock del backend (zona de backend-api). A partir de
    ahora, cualquier cambio de salida debe subirla (con `uv lock --project backend`).
14. **`validate_plan` y códigos**: excluidos/evitados ⇒ `avoided_muscle_substituted`, id
    inexistente ⇒ `deprecated_exercise`, equipamiento ⇒ `equipment_insufficient`, con
    `message_es` precisos, hasta resolver **CC-0003**.

## Cómo verificar (comandos exactos)

```bash
cd /root/forja-kit/.claude/worktrees/agent-af841f657be0719cc     # o checkout de f1/motor-rutinas
export PATH=$HOME/.local/bin:$HOME/.local/npm10/bin:$PATH
make lint typecheck test; echo "exit $?"                           # exit 0
make test-engine                                                   # 100 % líneas y ramas
cd engine && uv run --locked pytest tests/test_combinations.py --no-cov -q   # 1.890 casos, ~26 s
uv run --locked pytest tests/test_properties.py tests/test_sex.py tests/test_golden.py --no-cov -q
FORJA_UPDATE_GOLDEN=1 uv run --locked pytest tests/test_golden.py --no-cov   # regenerar snapshots
# Regenerar la fixture (dataset @ 7455efae en <dir>/data/exercises.json + exercises.schema.json):
cd ../backend && uv run --locked forja-ingest export-cards --dataset-dir <dir> \
  --output ../engine/tests/fixtures/catalog.json
```

## Métricas

| Métrica | Valor |
|---|---|
| Tests del motor | 2.084 (1.890 combinaciones + 150/40/40 ejemplos hypothesis + 12 golden + unitarios) |
| Cobertura `forja_engine` | **100 % líneas, 100 % ramas** (umbral 100 / 95) |
| `make lint typecheck test` | exit 0 (engine, nutrition, backend 521 tests, frontend 44 tests) |
| 1.890 combinaciones | 0 errores, 26 s sin cobertura (~2 min la suite completa con cobertura) |
| `generate` con 1.324 tarjetas | p50 12 ms, **p95 21 ms** (presupuesto 150 ms) |
| Estrés adicional (fuera de la suite) | 3.000 entradas hypothesis aleatorias + `regenerate_day` + `swap_exercise`: 0 fallos |

### Ejemplos legibles (semana 1; el resto en `engine/tests/golden/*.md`)

**02 · Intermedio, hombre, gimnasio, hipertrofia, 4 días × 60 min**

| Bloque | Ejercicio | Series | Reps / tiempo | RIR | Descanso | Tempo |
|---|---|---|---|---|---|---|
| Calentamiento | rodillas altas contra la pared (3636) | 1 | 180 s | — | 0 s | — |
| Calentamiento | press de pecho de pie en máquina (3758) | 1 | 8-12 | — | 30 s | — |
| Trabajo | press de banca con mancuernas (0289) | 5 | 6-10 | 2 | 150 s | 3-0-1-0 |
| Trabajo | remo inclinado con mancuernas (0293) | 4 | 6-10 | 2 | 150 s | 3-0-1-0 |
| Superserie x3 | press de hombro en máquina a una mano (0590) | 3 | 10-15 por lado | 2 | 75 s | 2-0-1-1 |
| Superserie x3 | jalón en polea (0198) | 3 | 10-15 | 2 | 75 s | 2-0-1-1 |
| Superserie | curl en sentadilla en polea (1644) | 1 | 10-15 | 2 | 75 s | 2-0-1-1 |
| Superserie | extensión de codos tumbado con barra (0057) | 1 | 10-15 | 2 | 75 s | 2-0-1-1 |
| Vuelta a la calma | estiramiento de pecho con manos tras la cabeza (1259) | 1 | 35 s por lado | — | 0 s | — |
| Vuelta a la calma | estiramiento de dorsal a una mano contra la pared (1355) | 1 | 35 s por lado | — | 0 s | — |

**04 · Intermedia, mujer, gimnasio, fuerza, 4 días × 60 min (día pesado)**

| Bloque | Ejercicio | Series | Reps / tiempo | RIR | Descanso | Tempo |
|---|---|---|---|---|---|---|
| Calentamiento | rodillas altas contra la pared (3636) | 1 | 180 s | — | 0 s | — |
| Calentamiento | press de pecho de pie en máquina (3758) | 1 | 8-12 | — | 30 s | — |
| Trabajo | press de banca con mancuernas (0289) | 5 | 1-4 | 3 | 240 s | 2-1-X-0 |
| Trabajo | remo sentado en polea (0861) | 5 | 1-4 | 3 | 240 s | 2-1-X-0 |
| Superserie x2 | press de hombro en máquina a una mano (0590) | 2 | 6-10 por lado | 2 | 90 s | 2-0-1-0 |
| Superserie x2 | jalón en polea (0198) | 2 | 6-10 | 2 | 90 s | 2-0-1-0 |
| Vuelta a la calma | estiramiento de pecho con manos tras la cabeza (1259) | 1 | 35 s por lado | — | 0 s | — |
| Vuelta a la calma | estiramiento de dorsal a una mano contra la pared (1355) | 1 | 35 s por lado | — | 0 s | — |

Mesociclo: semanas 1–3 acumulación (RIR 3, 2, 2), semana 4 intensificación (RIR 1),
semana 5 descarga (RIR 4, 0,6 del volumen).

**07 · Intermedia, mujer, casa con bandas, tonificación, 4 días × 45 min**

| Bloque | Ejercicio | Series | Reps / tiempo | RIR | Descanso | Tempo |
|---|---|---|---|---|---|---|
| Calentamiento | rodillas altas contra la pared (3636) | 1 | 180 s | — | 0 s | — |
| Calentamiento | press de banca con banda elástica (1254) | 1 | 8-12 | — | 30 s | — |
| Trabajo | flexión (0662) | 5 | 8-12 | 2 | 105 s | 2-0-1-0 |
| Trabajo | remo en sentadilla con peso corporal (3168) | 5 | 8-12 | 2 | 105 s | 2-0-1-0 |
| Superserie | press por encima de la cabeza con giro con banda elástica (1012) | 1 | 12-15 | 2 | 50 s | 2-0-1-0 |
| Superserie | dominada y jalón Rocky (0678) | 1 | 12-15 | 2 | 50 s | 2-0-1-0 |
| Superserie | curl de bíceps por encima de la cabeza con banda a una mano (0986) | 1 | 12-16 por lado | 2 | 50 s | 2-0-1-0 |
| Superserie | body-up (extensión de codos desde plancha) (0137) | 1 | 12-16 | 2 | 50 s | 2-0-1-0 |
| Vuelta a la calma | estiramiento de pecho y parte frontal del hombro (1271) | 1 | 35 s por lado | — | 0 s | — |
| Vuelta a la calma | estiramiento de dorsal a una mano contra la pared (1355) | 1 | 35 s por lado | — | 0 s | — |

## Riesgos/pendientes

1. **Empuje vertical con peso corporal**: el dataset solo tiene 2 ejercicios (flexión en pino
   0471, pino 3302), ambos de dificultad 3. Siguiendo §7.2 se relaja la dificultad y se avisa
   (`slot_relaxed` … «con una dificultad superior a tu nivel»), así que **un principiante con
   peso corporal recibe un pino** (y lo mismo en `shoulder_raise`, cuyo afín es el empuje
   vertical). Probado en `test_bodyweight_vertical_push_relaxes_difficulty_and_warns`.
   Propuesta al experto: para principiantes, eliminar el slot o usar un afín horizontal antes
   de relajar más de 1 nivel de dificultad.
2. **Volumen alcanzable con plantillas de 6 slots**: con torso/pierna el pecho queda en 5–9
   series frente a 10–17 objetivo, y los brazos se pasan por el crédito indirecto de empujes y
   tirones (énfasis `arms` ⇒ hasta 27 frente a 16,5). Se avisa con `volume_out_of_range`;
   resolverlo exige más slots en `split-templates.yaml` o revisar créditos (experto).
3. **Fuerza, día pesado 1–4 reps** (`reps_shift: -2` sobre 3–6) y RIR = máx(día, semana):
   valores literales de `periodization.yaml`, a revisar.
4. **Sesiones muy cortas** (20–30 min) con calentamiento (6) + calma (5): se recortan accesorios
   y el finisher; se avisa (`slot_dropped`, `main_exercise_trimmed`, `time_budget_exceeded`).
5. **Suite con cobertura ~2 min** (1.890 casos + hypothesis); sin cobertura, 30–40 s.
6. **Golden** (1,9 MB) dependen del catálogo exportado: cualquier cambio de enriquecimiento o
   de `names_es.json` obliga a regenerarlos (comando arriba) y a revisar los `.md`.
7. **Carga de tablas por defecto** perezosa y cacheada (`default_tables()`), no al importar:
   importar el paquete no requiere `specs/`. El backend debe llamar a `load_tables(<ruta>)`
   al arrancar para fallar rápido y pasar `tables` al motor si `specs/` no está en
   `engine/../specs`.

## Peticiones a otros agentes

- **arquitecto**: resolver **CC-0003** (códigos `excluded_exercise`, `avoided_exercise`,
  `unknown_exercise`). Nota para `docs/TASKS.md`: F1-ENG-19 queda hecha con el catálogo real.
- **experto-entrenamiento** (F1b-EXP-04/05): revisar `specs/engine-rules.yaml` (sobre todo
  `difficulty`, `scoring.loadable_in_main`, `compound_secondary_groups`, límites de series) y
  los 12 snapshots `engine/tests/golden/*.md`; decidir los riesgos 1–3.
- **backend-api**: usar `generate/regenerate_day/swap_exercise/rebalance_after_edit/
  validate_plan` de `forja_engine`; mapear `pydantic.ValidationError` y
  `PlanOperationError` a 422; cargar `load_tables(ruta)` al arrancar; si se sube
  `ENGINE_VERSION`, ejecutar `uv lock --project backend`.
- **ingesta-datos**: sin cambios pedidos; cualquier cambio de `export-cards` ⇒ avisar para
  regenerar `engine/tests/fixtures/catalog.json` y los golden.
- **devops-despliegue**: la imagen del backend debe incluir `specs/` (incluido el nuevo
  `engine-rules.yaml`).

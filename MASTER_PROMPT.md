# PROMPT MASTER — FORJA · App web de entrenamiento autoalojada

> Documento fuente de verdad para construir **Forja**, una aplicación web de entrenamiento
> autoalojada, a partir del dataset `hasaneyldrm/exercises-dataset`. Lo ejecutan varios
> subagentes especializados coordinados por una sesión orquestadora (ver `ORCHESTRATION.md`).
> Cada subagente DEBE leer este documento completo antes de escribir una sola línea de código,
> y después las secciones marcadas como propias de su rol.

---

## 0. Cómo leer este documento

- **DEBE / NO DEBE** = requisito obligatorio. **DEBERÍA** = por defecto, desviarse solo con ADR.
- Todo lo que no esté especificado se decide mediante un **ADR** (`docs/adr/NNNN-titulo.md`,
  formato: Contexto · Decisión · Alternativas · Consecuencias) creado por el agente que decide.
- Los contratos compartidos viven en `contracts/` y `specs/`. **Ningún agente cambia un contrato
  en silencio**: propone el cambio en `docs/CONTRACT_CHANGES.md`, el arquitecto lo aprueba y
  se versiona.
- Idioma: **UI, documentación de usuario y comentarios de dominio en español**. Identificadores
  de código, nombres de tablas, rutas de API y mensajes de commit en **inglés**.
- Datos reales del dataset ya analizados: `docs/dataset-analysis.md`. No los redescubras,
  verifícalos con los tests de ingesta.

---

## 1. Visión y alcance

Forja es una PWA para uso personal/familiar en un servidor propio (Proxmox, contenedor LXC con
Docker, nginx como reverse proxy). Permite:

1. **Explorar la biblioteca** de 1.324 ejercicios con su GIF animado, miniatura, músculos,
   equipamiento e instrucciones paso a paso en español (y otros 9 idiomas).
2. **Generar rutinas automáticamente** según **enfoque/objetivo**, **días por semana**, **sexo
   de la persona**, nivel, equipamiento disponible, duración de sesión, énfasis muscular y
   limitaciones. Cada rutina especifica **ejercicios, series, repeticiones, RIR, tempo y
   descansos**, con calentamiento, vuelta a la calma, alternativas y periodización por semanas.
3. **Editar rutinas a mano** (añadir, quitar, reordenar, superseries, cambiar parámetros).
4. **Entrenar** con un reproductor de sesión: GIF del ejercicio, registro de series
   (peso/reps/RIR), temporizador de descanso, rendimiento anterior y sugerencia de progresión.
5. **Seguir el progreso**: historial, calendario, volumen semanal por músculo, récords, 1RM
   estimado, peso corporal.
6. **Opcionalmente, dieta**: cálculo de calorías y macros, plan de comidas semanal generado a
   partir de una base de alimentos, lista de la compra. Desactivable por usuario y globalmente.
7. **Exportar**: rutina a PDF, calendario a ICS, copia completa del usuario a JSON.

Fuera de alcance v1: apps nativas, pagos, red social, wearables, IA generativa en tiempo de
ejecución (todo el motor es determinista y offline).

---

## 2. Restricciones no negociables

### 2.1 Licencia de los medios (CRÍTICO)
El dataset tiene **dos licencias**:
- **Datos** (nombres, categorías, músculos, equipamiento, instrucciones y traducciones):
  **MIT** → se pueden usar, transformar y redistribuir conservando el aviso MIT.
- **Medios** (`images/*.jpg` y `videos/*.gif`): **© Gym visual**, redistribuidos en el repo
  con permiso escrito del titular, **no cubiertos por MIT**. Condiciones:
  - Resolución **180×180 únicamente**. NO se reescalan, recodifican, recortan, convierten a
    WebP/MP4 ni se les pone marca de agua. Se sirven **byte a byte tal cual**.
  - Toda vista que muestre un medio DEBE mostrar la atribución
    **«© Gym visual — https://gymvisual.com/»** (texto visible, enlace `rel="noopener"`).
  - Clonar el repo no concede licencia sobre los medios. La app se diseña para **uso privado
    autoalojado**. Por defecto los medios se sirven **solo a usuarios autenticados**
    (`MEDIA_REQUIRE_AUTH=true`, `auth_request` de nginx). Si el propietario quiere exponer la app
    públicamente, la documentación DEBE advertir que revise los términos de Gym visual
    (https://gymvisual.com/content/3-terms-and-conditions-of-use) y obtenga licencia propia.
  - La página «Acerca de / Créditos» DEBE incluir la licencia MIT del dataset, el aviso de medios
    y el commit SHA del dataset ingerido.
- Los medios **no se versionan en el repo de Forja**. Se obtienen en el despliegue desde el repo
  de origen en un **commit fijado** (`DATASET_COMMIT=7455efae41b330c265e7cd4b78dfa848e7ce5ebd`,
  2026-07-16) y se verifican con checksums SHA-256 generados por la ingesta.

### 2.2 Calidad
- **Producción desde el primer commit**: nada de `TODO`, `pass`, `NotImplementedError`,
  datos simulados en rutas reales, `any` en TypeScript ni `# type: ignore` sin justificación.
- Cobertura mínima: **backend ≥ 90 % líneas y ramas**, **motores de rutinas y nutrición = 100 %
  líneas y ≥ 95 % ramas**, **frontend ≥ 85 %**, más E2E de todos los flujos críticos (§13).
- Lint y tipos estrictos: `ruff` + `mypy --strict` (Python), `eslint` + `tsc --strict` (TS).
- Todo cambio de esquema pasa por migración Alembic reversible y probada (upgrade + downgrade).

### 2.3 Seguridad y salud
- La app no sustituye a profesionales. Aviso sanitario en onboarding, generador y dieta.
- Cuestionario de aptitud (tipo PAR-Q) en el onboarding: si alguna respuesta es «sí», se
  recomienda consultar a un profesional antes de empezar; no bloquea, pero queda registrado el
  aviso y se fuerza nivel «principiante» salvo que el usuario lo cambie explícitamente.
- Nutrición con **suelos de seguridad** (§8.5), sin planes para menores de 18 años, ni
  embarazo/lactancia (se deriva a profesional), ni déficits agresivos.

---

## 3. Datos de origen (resumen; detalle en `docs/dataset-analysis.md`)

- Repo: `https://github.com/hasaneyldrm/exercises-dataset` @ `7455efae41b3…`.
- `data/exercises.json`: **1.324** registros; `data/exercises.schema.json`: JSON Schema 2020-12.
- Campos: `id` ("0001"…), `name` (solo inglés), `category` = `body_part` (10 valores),
  `equipment` (28 valores), `target` (19), `muscle_group` (29), `secondary_muscles[]` (40),
  `instructions.{en,es,it,tr,ru,zh,hi,pl,ko,fr}` (texto), `instruction_steps.{lang}[]`
  (4–11 pasos), `media_id`, `image` (`images/<id>-<media_id>.jpg`, 12 MB total),
  `gif_url` (`videos/<id>-<media_id>.gif`, 126 MB total, 180×180, ~12 fotogramas),
  `attribution`, `created_at`.
- **Carencias que Forja DEBE resolver con enriquecimiento** (§6.3): no hay nombre en español,
  ni patrón de movimiento, ni compuesto/aislamiento, ni dificultad, ni marca de «ejercicio
  básico», ni rol (calentamiento/estiramiento/cardio).
- **Peculiaridades**: vocabulario muscular inconsistente (`traps`/`trapezius`,
  `delts`/`shoulders`/`deltoids`, `lats`/`latissimus dorsi`, `abs`/`abdominals`…), 40 variantes
  `v. 2`/`v. 3`, **33 ejercicios con sufijo `(male)`/`(female)`** (misma técnica, demostrador
  distinto), 5 variantes de cámara `(back pov)`/`(side pov)`, 6 nombres duplicados con distinto
  id, **mojibake** `в°` en lugar de `°` en 4 nombres (`sled 45в° …`), erratas en nombres
  (`revers`, `sitted`, `side bent`), 57 estiramientos, 29 de cardio, 2 de cuello.

---

## 4. Stack y arquitectura

### 4.1 Stack (fijado; cambiarlo requiere ADR aprobado)
| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, **FastAPI**, Pydantic v2, SQLAlchemy 2.x (async, `asyncpg`), Alembic, Uvicorn (workers vía Gunicorn) |
| Motores | Paquetes Python puros sin E/S: `forja_engine` (rutinas) y `forja_nutrition` (dieta). Solo dependen de la librería estándar, `pydantic` y `pyyaml` (+ `scipy` en nutrición) |
| BD | PostgreSQL 16 (extensiones `unaccent`, `pg_trgm`) |
| Frontend | React 18 + TypeScript + Vite, TanStack Router, TanStack Query, Zustand (estado de sesión de entreno), Tailwind CSS, Radix UI primitives, `dnd-kit`, Recharts, `vite-plugin-pwa` (Workbox), `idb` |
| Cliente API | Generado desde OpenAPI con `openapi-typescript` + `openapi-fetch` (nunca tipos escritos a mano) |
| i18n | `i18next` (UI en `es` por defecto y `en`); instrucciones de ejercicios en los 10 idiomas del dataset |
| PDF | WeasyPrint en backend (plantillas Jinja2) |
| Tests | pytest, pytest-asyncio, hypothesis, httpx, testcontainers-postgres · Vitest, Testing Library, MSW · Playwright |
| Infra | Docker Compose, nginx (estático + medios + proxy `/api`), Proxmox LXC (Debian 12, `nesting=1,keyctl=1`) |

### 4.2 Estructura del monorepo
```
forja/
├── CLAUDE.md                     # reglas del proyecto para agentes
├── MASTER_PROMPT.md  ORCHESTRATION.md
├── contracts/
│   ├── openapi.yaml              # contrato API (fuente de verdad, lo exporta FastAPI y se compara en CI)
│   └── domain.md                 # glosario y entidades
├── specs/                        # tablas de configuración del motor (YAML versionado)
├── docs/  adr/  dataset-analysis.md  TASKS.md  CONTRACT_CHANGES.md  handoffs/
├── backend/
│   ├── app/{api,core,db,models,schemas,services,repositories,security,pdf}/
│   ├── migrations/               # Alembic
│   ├── ingest/                   # pipeline de ingesta y enriquecimiento
│   └── tests/{unit,integration,contract}/
├── engine/forja_engine/          # motor de rutinas (puro) + tests/
├── nutrition/forja_nutrition/    # motor de nutrición (puro) + tests/ + data/foods.json
├── frontend/src/{routes,features,components,lib,i18n,styles,sw}/  + tests/ + e2e/
├── deploy/{docker-compose.yml,nginx/,lxc/,scripts/,backup/}
└── .github/workflows/ci.yml      # o .gitea/ si el propietario usa Gitea (ADR)
```

### 4.3 Diagrama lógico
```
Navegador (PWA) ──HTTPS──► nginx ─┬─► /            → SPA estática (frontend/dist)
                                  ├─► /media/*     → volumen de medios (auth_request opcional)
                                  └─► /api/*       → FastAPI (gunicorn+uvicorn) ──► PostgreSQL
                                                         ├─ forja_engine (rutinas)
                                                         └─ forja_nutrition (dieta)
```

---

## 5. Modelo de dominio y base de datos

Todas las tablas con `id` UUID v7 (salvo `exercise.id`, que conserva el id del dataset "0001"),
`created_at`/`updated_at` con zona horaria. Borrado lógico solo donde se indique.

### 5.1 Catálogo (solo escritura por ingesta/admin)
- `muscle` (`code` PK canónico, `name_es`, `name_en`, `region`: upper/lower/core/cardio/other).
- `equipment` (`code` PK, `name_es`, `name_en`, `group`: gym/home_basic/bodyweight/cardio_machine/other).
- `exercise`:
  `id` ("0001"), `media_id`, `name_en` (original), `name_es`, `display_name_en` (erratas
  corregidas), `slug`, `body_part`, `equipment_code` FK, `target_muscle` FK,
  `primary_group_muscle` FK (de `muscle_group`), `movement_pattern` (enum §6.3),
  `mechanic` (compound/isolation), `role` (main/accessory/core/cardio/mobility/warmup),
  `difficulty` (1–3), `is_staple` (bool), `laterality` (bilateral/unilateral),
  `demo_sex` (male/female/null, de los sufijos), `variant_group` (agrupa `v. 2`, `(male)`/`(female)`
  y duplicados), `load_type` (external/bodyweight/assisted/time), `thumb_path`, `gif_path`,
  `media_sha256_thumb`, `media_sha256_gif`, `source_commit`, `deprecated_at`, `search_vector` (tsvector
  `unaccent`, es+en), `enrichment_version`.
- `exercise_secondary_muscle` (`exercise_id`, `muscle_code`).
- `exercise_instruction` (`exercise_id`, `lang`, `text`, `steps` JSONB).
- `exercise_alternative` (`exercise_id`, `alt_id`, `score`) — precalculada en ingesta.

### 5.2 Usuarios y perfil
- `user` (`email` único citext, `password_hash` argon2id, `display_name`, `role` user/admin,
  `locale`, `units` metric/imperial, `is_active`, `last_login_at`).
- `session` (token opaco hasheado, `user_id`, `expires_at`, `user_agent`, `ip_hash`, `revoked_at`).
- `profile` (1:1 con user): `sex` (male/female/unspecified), `birth_date`, `height_cm`,
  `experience` (beginner/intermediate/advanced), `activity_level`, `equipment_profile`
  (preset + lista), `limitations` (músculos/patrones a evitar), `parq_answers` JSONB,
  `parq_flagged`, `diet_enabled`.
- `body_metric` (`user_id`, `date`, `weight_kg`, `body_fat_pct` opcional, `waist_cm` opcional).
- `favorite_exercise` (`user_id`, `exercise_id`).

### 5.3 Programas y sesiones
- `program` (rutina/mesociclo): `user_id`, `name`, `source` (generated/manual/imported),
  `generator_input` JSONB (entrada exacta), `generator_version`, `seed`, `goal`,
  `days_per_week`, `weeks`, `is_active` (máx. 1 activo por usuario), `archived_at`.
- `program_week` (`program_id`, `index`, `phase`: accumulation/intensification/deload).
- `program_day` (`week_id`, `index`, `name`, `focus` p. ej. «Tren superior A»,
  `estimated_minutes`).
- `program_block` (`day_id`, `order`, `kind`: warmup/main/superset/circuit/finisher/cooldown,
  `rounds`, `rest_between_rounds_s`).
- `program_exercise` (`block_id`, `order`, `exercise_id`, `sets`, `rep_min`, `rep_max`,
  `target_rir`, `tempo` ("3-1-1-0"), `rest_s`, `duration_s` (para isométricos/cardio),
  `load_hint`, `notes_es`, `alternatives` JSONB con ids).
- `workout_session` (`user_id`, `program_day_id` nullable, `started_at`, `finished_at`,
  `status` in_progress/completed/abandoned, `perceived_effort` 1–10, `notes`, `client_uuid`
  para idempotencia offline).
- `set_log` (`session_id`, `exercise_id`, `set_index`, `weight_kg`, `reps`, `rir`,
  `duration_s`, `is_warmup`, `completed_at`, `client_uuid` único).
- `personal_record` (materializado por trigger de servicio: mejor e1RM, mejor peso×reps,
  mejor volumen por ejercicio).

### 5.4 Nutrición (si `diet_enabled`)
- `food` (catálogo, ver §8.4), `nutrition_target` (kcal, proteína, grasa, carbohidratos,
  fibra, método, fecha, entrada JSONB), `meal_plan` (`user_id`, `week_start`, `diet_type`,
  `meals_per_day`, `input` JSONB, `seed`), `meal_plan_item` (`plan_id`, `day`, `meal`,
  `food_id`, `grams`), `shopping_list` (derivada, no persistida o cacheada).

### 5.5 Sistema
- `app_setting` (clave/valor: registro abierto, dieta global, `MEDIA_REQUIRE_AUTH` efectivo).
- `audit_log` (acciones de admin y de seguridad).
- `ingest_run` (commit, fecha, recuentos, checksums, resultado de validaciones).

Índices: GIN en `exercise.search_vector` y trigram en `name_es`/`name_en`; índices compuestos
en `set_log(session_id, exercise_id)`, `workout_session(user_id, started_at desc)`.

---

## 6. Pipeline de ingesta y enriquecimiento (`backend/ingest/`)

### 6.1 Obtención
1. `forja-ingest fetch --commit $DATASET_COMMIT` clona en modo sparse/shallow en un directorio
   temporal, hace checkout del commit exacto y verifica que `data/exercises.json` valida contra
   `data/exercises.schema.json` (librería `jsonschema`).
2. Copia `images/` → `$MEDIA_ROOT/thumbs/` y `videos/` → `$MEDIA_ROOT/gifs/` **sin modificar**,
   calcula SHA-256 de cada fichero y escribe `$MEDIA_ROOT/manifest.json`
   (id, ruta, bytes, sha256, ancho, alto). Verifica 180×180 con Pillow (solo lectura).
3. Copia `LICENSE` y `NOTICE.md` a `$MEDIA_ROOT/LICENSES/` (se muestran en Créditos).
4. Idempotente: si el commit y los checksums no cambian, no hace nada. Ejecución con
   `--dry-run` que muestra el diff (altas/bajas/cambios).

### 6.2 Normalización
- Vocabulario muscular y de equipamiento mapeado con `specs/muscle-normalization.yaml` y
  `specs/equipment-normalization.yaml`. **Todo valor sin mapear hace fallar la ingesta** (test).
- `display_name_en`: corrige erratas vía `specs/overrides/name-fixes.yaml` sin alterar `name_en`.
- Sufijos `(male)`/`(female)` → `demo_sex`; se retiran del nombre visible; ambos registros
  comparten `variant_group`.
- `v. 2`/`v. 3` → mismo `variant_group`, se muestra «variante 2».
- `(back pov)`/`(side pov)` → mismo `variant_group` que el ejercicio base; se muestran como
  «vista trasera/lateral» y el detalle ofrece conmutar entre ángulos de cámara.
- Mojibake `в°` → `°` en `display_name_en` (test que falla si queda algún carácter `в`).
- Duplicados de nombre con distinto id → mismo `variant_group`; se conservan ambos (el medio
  difiere). Nombre visible con sufijo «(variante B)».

### 6.3 Enriquecimiento (reglas deterministas + overrides revisados)
Motor de reglas en `backend/ingest/enrich.py` guiado por `specs/enrichment-rules.yaml`
(palabras clave por prioridad sobre `name_en`, `target`, `body_part`, `equipment`), con
`specs/overrides/enrichment-overrides.yaml` que prevalece. Salida por ejercicio:

- `movement_pattern` ∈ {`squat`, `lunge`, `hinge`, `horizontal_push`, `vertical_push`,
  `horizontal_pull`, `vertical_pull`, `elbow_flexion`, `elbow_extension`, `shoulder_raise`,
  `chest_fly`, `rear_delt`, `knee_extension`, `knee_flexion`, `hip_abduction`,
  `hip_adduction`, `glute_isolation`, `calf`, `core_flexion`, `core_anti_extension`,
  `core_rotation`, `core_lateral`, `shrug`, `forearm`, `neck`, `carry`, `plyometric`,
  `cardio`, `mobility`, `other`}.
- `mechanic`: compound si el patrón es multiarticular (squat, lunge, hinge, pushes, pulls,
  carry, plyometric) y el nombre no indica aislamiento (fly, raise, kickback, curl…).
- `role`: `mobility` si contiene `stretch`; `cardio` si `body_part == cardio`; `warmup` para
  movilidad dinámica y cardio ligero marcados en overrides; `core` para patrones core;
  `main` si compound y `is_staple`; resto `accessory`.
- `difficulty`: 1 = máquinas guiadas, poleas, bandas, asistidos, variantes «on knees»;
  2 = mancuernas, barra estándar, kettlebell básico, peso corporal estándar; 3 = unilaterales
  exigentes, gimnásticos (`pistol`, `muscle up`, `handstand`, `planche`, `maltese`,
  `front lever`, `l-pull-up`…), olímpicos.
- `laterality`: unilateral si `one arm`, `single leg`, `one leg`, `alternate`, `split`,
  `lunge`, `step-up`, `unilateral`.
- `load_type`: time si plank/hold/isométrico/cardio por tiempo; assisted si `assisted`;
  bodyweight si equipo `body weight`; resto external.
- `is_staple`: lista curada de ~120–160 ejercicios fundamentales en
  `specs/overrides/staples.yaml` (press banca, sentadilla, peso muerto rumano, dominadas,
  remo con barra/mancuerna, press militar, hip thrust, prensa, jalón, zancadas, etc.) cubriendo
  **todos los patrones principales × grupos de equipamiento** (gym, casa, peso corporal).

**Requisitos verificados por tests**: 100 % de ejercicios con patrón ≠ `other` salvo lista
explícita de excepciones justificadas; cada combinación patrón principal × grupo de
equipamiento tiene al menos 2 staples; informe `docs/enrichment-report.md` con distribución.

### 6.4 Nombres en español
- `specs/overrides/names_es.json` con los 1.324 nombres traducidos, generados por el agente de
  ingesta en lotes de 100 siguiendo el glosario `specs/glossary-es.yaml` y revisados por el
  agente experto en entrenamiento. Test: cobertura 100 %, sin duplicados no intencionados,
  términos del glosario aplicados de forma consistente.
- Las instrucciones en español se toman del dataset tal cual (`instructions.es`,
  `instruction_steps.es`).

### 6.5 Alternativas precalculadas
Para cada ejercicio, top 8 alternativas: mismo `movement_pattern` (peso 0,5), mismo
`target_muscle` (0,3), solapamiento de secundarios Jaccard (0,1), dificultad ±1 (0,1); se
excluyen el propio ejercicio y los de su `variant_group`; estiramientos solo alternan con
estiramientos.

### 6.6 Carga en BD
`forja-ingest load` hace upsert transaccional, registra `ingest_run`, recalcula
`search_vector` y alternativas. Nunca borra ejercicios referenciados por programas o logs:
los marca `deprecated` y el frontend los muestra con aviso.

---

## 7. Motor de rutinas (`engine/forja_engine/`)

Paquete **puro y determinista**: misma entrada + misma semilla + misma versión de tablas ⇒
mismo programa, byte a byte. No accede a BD ni red: recibe el catálogo enriquecido como lista
de `ExerciseCard` (DTO inmutable) y devuelve un `ProgramPlan`. Todas las constantes viven en
`specs/*.yaml` y se cargan y validan con Pydantic al importar (fallo rápido si el YAML es
inválido). La versión del motor (`ENGINE_VERSION`, semver) se guarda en cada programa.

### 7.1 Entrada (`GeneratorInput`)
| Campo | Tipo / valores | Notas |
|---|---|---|
| `goal` | `strength`, `hypertrophy`, `fat_loss`, `endurance`, `general_fitness`, `toning` | «toning» = recomposición: hipertrofia moderada + densidad + cardio |
| `days_per_week` | 1–7 | 7 ⇒ el 7.º día es movilidad/cardio suave (aviso de descanso) |
| `sex` | `male`, `female`, `unspecified` | ver §7.4 |
| `experience` | `beginner`, `intermediate`, `advanced` | PAR-Q marcado fuerza `beginner` salvo override |
| `session_minutes` | 20–120 (paso 5) | presupuesto de tiempo por sesión |
| `equipment` | preset (`full_gym`, `home_dumbbells`, `home_bands`, `bodyweight`, `custom`) + lista | filtra el catálogo |
| `emphasis` | `balanced`, `lower_glutes`, `upper_body`, `arms`, `back_posture`, `core` | redistribuye volumen |
| `avoid_muscles` / `avoid_patterns` | listas | lesiones/limitaciones; excluye y sustituye |
| `preferred_days` | lista de días de la semana (opcional) | para calendario e ICS |
| `weeks` | 4–8 (defecto 5 = 4 + descarga) | longitud del mesociclo |
| `include_warmup` / `include_cooldown` / `include_cardio_finisher` | bool | defecto según objetivo |
| `favorite_exercise_ids` / `excluded_exercise_ids` | listas | bonificación / exclusión |
| `seed` | int (opcional) | si falta se deriva de hash(entrada normalizada) |

### 7.2 Algoritmo (pipeline de 9 pasos; cada paso es una función pura testeada)
1. **Normalizar y validar** entrada (Pydantic). Aplicar reglas de seguridad: principiante
   con `days_per_week ≥ 6` ⇒ se mantiene pero con volumen repartido y aviso; 7 días ⇒ 1 día
   de recuperación activa obligatorio.
2. **Elegir split** con `specs/split-templates.yaml` (tabla días × experiencia; ver §7.3).
3. **Calcular volumen semanal objetivo** por grupo muscular (series efectivas) con
   `specs/volume-targets.yaml` según objetivo y experiencia; aplicar multiplicadores de
   `emphasis` (énfasis ×1,3–1,5 en los grupos destacados, ×0,8 en los demás, respetando
   mínimos de mantenimiento) y modificadores de sexo (§7.4).
4. **Repartir el volumen en días**: cada día del split tiene slots (`pattern`, `role`,
   `priority`). El volumen de cada grupo se reparte entre los días que lo entrenan,
   máx. 10 series efectivas por grupo y sesión (más allá, a otro día o se recorta).
   Series de compuestos cuentan 1,0 para el músculo objetivo y 0,5 para secundarios relevantes.
5. **Seleccionar ejercicios** por slot. Candidatos = catálogo filtrado por equipamiento,
   exclusiones, `avoid_*`, rol (`mobility`/`cardio` nunca en slots principales) y
   dificultad ≤ nivel (+1 permitido en accesorios para avanzados). Puntuación:
   - +40 patrón exacto del slot, +25 músculo objetivo del slot, +15 `is_staple` en slots
     `main`, +10 favorito, +5 variante con `demo_sex` = sexo del usuario (§7.4),
     −30 si ya usado esta semana en otro día (variedad), −15 si mismo `variant_group` ya
     usado, −10 si dificultad > nivel, −20 si unilateral en slot `main` de fuerza.
   - Desempate con PRNG `random.Random(seed)` sembrado por (seed, semana, día, slot).
   - Sin candidatos ⇒ relajar en orden: dificultad → staple → músculo objetivo → patrón
     afín (`specs/pattern-affinity.yaml`). Si aun así no hay, el slot se elimina y se
     registra `warning` en la salida (nunca excepción no controlada).
   - Cada `program_exercise` guarda hasta 3 alternativas válidas con el mismo filtro.
6. **Prescribir** series, rango de reps, RIR, tempo y descanso con `specs/prescription.yaml`
   (objetivo × rol × experiencia; ver §7.5).
7. **Ajustar al tiempo**: duración estimada = calentamiento + Σ(series × (tiempo bajo tensión
   estimado + descanso)) + transiciones (60 s por ejercicio, 30 s en superseries). Si excede
   `session_minutes` en más del 5 %: (a) agrupar accesorios antagonistas en superseries,
   (b) quitar 1 serie a accesorios, (c) eliminar slots de menor prioridad, (d) reducir
   descansos de accesorios hasta el mínimo de la tabla. Nunca tocar los `main` salvo último
   recurso, y reportarlo.
8. **Periodizar** con `specs/periodization.yaml`: semanas de acumulación (RIR 3→1, +1 serie
   por grupo y semana hasta el tope), semana final de descarga (50–60 % de series, RIR 4,
   mismas cargas o −10 %). Fuerza: ondulación diaria opcional (pesado/medio). Principiante:
   progresión lineal simple, sin ondulación.
9. **Componer salida** (`ProgramPlan`): semanas → días → bloques → ejercicios, con
   `estimated_minutes`, resumen de volumen semanal por grupo, `warnings[]`, `rationale_es[]`
   (explicaciones legibles: «Hemos elegido torso/pierna porque entrenas 4 días…»),
   `engine_version`, `tables_hash`, `seed`.

### 7.3 Splits por defecto (`specs/split-templates.yaml`)
| Días | Principiante | Intermedio | Avanzado |
|---|---|---|---|
| 1 | Full body | Full body | Full body |
| 2 | Full body A/B | Full body A/B | Torso/Pierna |
| 3 | Full body A/B/C | Full body A/B/C | Empuje/Tirón/Pierna |
| 4 | Torso/Pierna ×2 | Torso/Pierna ×2 | Torso/Pierna ×2 (fuerza/hipertrofia) |
| 5 | Torso/Pierna + Full body | Torso/Pierna + E/T/P | E/T/P + Torso/Pierna |
| 6 | E/T/P ×2 (volumen reducido) | E/T/P ×2 | E/T/P ×2 |
| 7 | E/T/P ×2 + Movilidad | ídem | ídem |

Énfasis `lower_glutes` en 4–6 días convierte un día de torso en «Glúteo e isquios» o añade
un bloque de glúteo; `upper_body`/`arms` añaden bloque de brazos. Objetivo `fat_loss`/`toning`
añade finisher cardio (10–15 min) por defecto; `endurance` usa circuitos.

### 7.4 Uso del sexo (explícito, configurable y nunca limitante)
El sexo **preselecciona valores por defecto**; el usuario puede cambiar cualquiera y el
wizard muestra qué se ha preseleccionado y por qué. Tabla `specs/sex-modifiers.yaml`:
- **Énfasis preseleccionado**: `female` ⇒ `lower_glutes`; `male` ⇒ `balanced`;
  `unspecified` ⇒ `balanced`. (Solo preselección en el wizard; editable.)
- **Tolerancia a la fatiga**: `female` ⇒ descansos de accesorios −15 % (con mínimo de tabla)
  y +1 rep al tope de rango en aislamiento; base en la mayor resistencia a la fatiga
  intra-sesión observada de media en mujeres. `male`/`unspecified` ⇒ sin cambio.
- **Demostrador**: si existen variantes `(male)`/`(female)`, se prefiere la del sexo del
  usuario (+5); `unspecified` ⇒ sin preferencia.
- **Nutrición**: selecciona fórmula de TMB (§8.2); `unspecified` ⇒ media de ambas.
- Prohibido: excluir ejercicios o grupos musculares por sexo, o limitar cargas por sexo.

### 7.5 Prescripción (`specs/prescription.yaml`, valores de referencia)
| Objetivo | Rol | Series | Reps | RIR | Descanso (s) | Tempo |
|---|---|---|---|---|---|---|
| strength | main | 4–5 | 3–6 | 1–3 | 180–300 | 2-1-X-0 |
| strength | accessory | 3 | 6–10 | 2 | 90–120 | 2-0-1-0 |
| hypertrophy | main | 3–4 | 6–10 | 1–2 | 120–180 | 3-0-1-0 |
| hypertrophy | accessory | 3 | 10–15 | 1–2 | 60–90 | 2-0-1-1 |
| fat_loss / toning | main | 3 | 8–12 | 2 | 90–120 | 2-0-1-0 |
| fat_loss / toning | accessory | 2–3 | 12–15 | 2 | 45–75 (superseries) | 2-0-1-0 |
| endurance | todos | 2–3 rondas | 15–25 | 2–3 | 30–60 | 1-0-1-0 |
| general_fitness | main | 3 | 8–12 | 3 | 90–120 | 2-0-1-0 |
| general_fitness | accessory | 2–3 | 10–15 | 2–3 | 60–90 | 2-0-1-0 |
| todos | core | 2–3 | 10–20 o 20–45 s | 2 | 45–60 | controlado |
| todos | warmup | 1–2 | 8–12 / 30–60 s | — | 0–30 | — |
| todos | cooldown (estiramientos) | 1–2 | 30–45 s por lado | — | 0 | — |

Principiantes: RIR +1 sobre la tabla y series en el mínimo del rango.

### 7.6 Progresión dentro de la app (`forja_engine.progression`)
- **Doble progresión**: al completar todas las series en el tope del rango con RIR ≥ objetivo,
  sugerir +2,5 kg (tren inferior compuesto +5 kg; mancuernas al siguiente par disponible;
  peso corporal: +reps o variante más difícil del mismo patrón).
- Fallo del mínimo del rango 2 sesiones seguidas ⇒ sugerir −5–10 % o mantener.
- e1RM con **Epley** (`w·(1+r/30)`) para reps ≤ 10; con RIR, reps efectivas = reps + RIR.
- Calentamiento de aproximación para `main` de fuerza: 40 %×8, 60 %×5, 80 %×2 del peso de
  trabajo (redondeado a la carga disponible, calculadora de discos 1,25–25 kg).
- Sugerencias puramente informativas: el usuario siempre confirma.

### 7.7 Operaciones adicionales del motor
- `regenerate_day(plan, week, day, seed)`, `swap_exercise(plan, slot, exclude_ids)`,
  `rebalance_after_edit(plan)` (recalcula volumen y avisos tras edición manual),
  `validate_plan(plan)` (reglas: ≤ 10 series efectivas/grupo/sesión, descanso ≥ mínimo,
  cada día ≥ 1 ejercicio, sin ejercicios `mobility` en bloques `main`).

### 7.8 Tests obligatorios del motor
- Unitarios por paso con tablas parametrizadas (todas las combinaciones objetivo × días ×
  experiencia × sexo × preset de equipamiento = 6×7×3×3×5 = 1.890 casos, ejecutados como
  test parametrizado rápido con catálogo fijo de fixture).
- **Propiedades (hypothesis)**: determinismo; toda salida pasa `validate_plan`; tiempo
  estimado ≤ presupuesto × 1,05 o warning; nunca aparece un ejercicio excluido ni un
  músculo/patrón evitado; ningún equipamiento no disponible; volumen por grupo dentro de ±15 %
  del objetivo o warning.
- **Snapshots** (golden files) de 12 perfiles representativos, revisados por el experto.

---

## 8. Motor de nutrición (`nutrition/forja_nutrition/`) — opcional

### 8.1 Entrada
Sexo, edad, altura, peso, nivel de actividad diaria (sedentario, ligero, moderado, alto),
días de entrenamiento (del programa activo), objetivo nutricional (`lose`, `maintain`, `gain`,
`recomp`), ritmo (`gentle`, `standard`), tipo de dieta (`omnivore`, `pescatarian`,
`vegetarian`, `vegan`), comidas/día (3–5), exclusiones de alimentos y alérgenos declarados
(gluten, lactosa, frutos secos, huevo, pescado, marisco, soja), preferencias (no me gusta X).

### 8.2 Cálculos
- **TMB Mifflin-St Jeor**: hombre `10·kg + 6,25·cm − 5·edad + 5`; mujer `… − 161`;
  `unspecified` ⇒ media de ambas.
- **GET** = TMB × factor (sedentario 1,2 · ligero 1,375 · moderado 1,55 · alto 1,725), con
  el factor elegido a partir de actividad diaria + días de entreno (tabla en
  `specs/nutrition.yaml`).
- **Ajuste por objetivo**: `lose` −15 % (`gentle` −10 %), tope −500 kcal/día; `gain` +10 %
  (`gentle` +5 %); `recomp` −5 % a 0; `maintain` 0.
- **Macros**: proteína 1,6–2,2 g/kg (1,8 por defecto; 2,0–2,2 en `lose`/`recomp`); grasa
  ≥ 0,8 g/kg y ≥ 20 % kcal; carbohidratos = resto; fibra 14 g/1.000 kcal.

### 8.3 Plan de comidas
- Plantillas de comida (desayuno, media mañana, comida, merienda, cena) con estructura
  mediterránea (fuente de proteína + hidrato + verdura/fruta + grasa saludable).
- Selección de alimentos por plantilla con PRNG sembrado + penalización de repetición semanal.
- Cálculo de gramos por **mínimos cuadrados no negativos acotados** (`scipy.optimize.lsq_linear`)
  para acercar kcal y macros diarios al objetivo (tolerancia ±5 % kcal, ±10 % macros),
  redondeo a porciones razonables (5 g, unidades para huevos/frutas) y re-verificación.
- Lista de la compra semanal agregada por categoría de supermercado.
- Intercambio de alimento dentro de la misma categoría conservando macros de la comida.

### 8.4 Base de alimentos (`nutrition/forja_nutrition/data/foods.json`)
~200 alimentos habituales en España con valores por 100 g (kcal, proteína, grasa,
carbohidratos, fibra), categoría, tipo de dieta compatible, alérgenos, porción típica.
Fuente: **USDA FoodData Central** (dominio público/CC0), anotando el `fdc_id` de cada
alimento, con nombres en español. Test: cada alimento cumple
`|kcal − (4P + 4C + 9G)| ≤ 12 %` (o justificación por alcohol/fibra en metadata).

### 8.5 Suelos y bloqueos de seguridad
- Menor de 18 años, embarazo o lactancia declarados ⇒ no se genera plan; mensaje de
  derivación a profesional.
- kcal objetivo nunca por debajo de `max(TMB, 1.200 mujer / 1.500 hombre / 1.350 unspecified)`.
- IMC < 18,5 con objetivo `lose` ⇒ se bloquea `lose` y se ofrece `maintain`.
- Sin ayunos extremos, sin menos de 3 comidas, sin «detox». Aviso sanitario visible.
- La app no muestra calorías de forma punitiva (sin rojos de «te has pasado»); tono neutro.

### 8.6 Tests
100 % líneas; propiedades: suelos siempre respetados, macros suman kcal ±2 %, ningún
alimento excluido/alérgeno aparece, plan reproducible con semilla.

---

## 9. API (FastAPI, prefijo `/api/v1`)

Convenciones: JSON, `snake_case`, errores RFC 9457 (`application/problem+json`), paginación
por cursor (`?cursor=&limit=` máx. 100), `ETag` en catálogo, idempotencia con cabecera
`Idempotency-Key` en POST de sesiones/series, fechas ISO 8601 UTC. `contracts/openapi.yaml`
es el contrato; test de contrato en CI compara el esquema exportado con el versionado.

| Área | Endpoints |
|---|---|
| Salud | `GET /health` (vivo), `GET /ready` (BD + medios) |
| Auth | `POST /auth/register` (si habilitado; el primer usuario es admin), `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/password`, `GET /auth/check` (para `auth_request` de nginx, 204/401) |
| Perfil | `GET/PUT /profile`, `PUT /profile/parq`, `GET/POST/DELETE /body-metrics` |
| Catálogo | `GET /exercises?q=&body_part=&target=&muscle=&equipment=&pattern=&mechanic=&difficulty=&role=&favorites=&cursor=&limit=`, `GET /exercises/{id}` (con instrucciones en `?lang=`), `GET /exercises/{id}/alternatives`, `GET /catalog/facets` (recuentos por filtro), `PUT/DELETE /exercises/{id}/favorite` |
| Generador | `POST /generator/preview` (no persiste; devuelve `ProgramPlan`), `POST /programs` (desde plan o manual), `POST /programs/{id}/regenerate-day`, `POST /programs/{id}/swap` |
| Programas | `GET /programs`, `GET/PATCH/DELETE /programs/{id}`, `POST /programs/{id}/activate`, `POST /programs/{id}/duplicate`, `PUT /programs/{id}/days/{day_id}` (edición completa de un día con validación del motor), `GET /programs/{id}/export.pdf`, `GET /programs/{id}/calendar.ics` |
| Entreno | `POST /sessions` (desde día de programa o libre), `GET /sessions?from=&to=`, `GET/PATCH /sessions/{id}`, `POST /sessions/{id}/sets`, `PATCH/DELETE /sessions/{id}/sets/{set_id}`, `POST /sessions/{id}/finish`, `POST /sync` (lote offline idempotente por `client_uuid`) |
| Progreso | `GET /stats/overview`, `GET /stats/volume?weeks=`, `GET /stats/exercise/{id}` (serie temporal e1RM, mejor serie), `GET /records` |
| Sugerencias | `GET /sessions/next` (próximo día + cargas sugeridas por progresión) |
| Nutrición | `GET/PUT /nutrition/settings`, `POST /nutrition/targets/calculate`, `POST /nutrition/plans` (genera), `GET /nutrition/plans/{id}`, `POST /nutrition/plans/{id}/swap`, `GET /nutrition/plans/{id}/shopping-list`, `GET /foods?q=` |
| Datos | `GET /me/export` (JSON completo), `POST /me/import`, `DELETE /me` (borrado de cuenta con confirmación de contraseña) |
| Admin | `GET/PUT /admin/settings`, `GET /admin/users`, `PATCH /admin/users/{id}`, `POST /admin/ingest` (lanza ingesta en tarea de fondo), `GET /admin/ingest/runs` |

Rendimiento: `GET /exercises` p95 < 80 ms con 1.324 filas; `POST /generator/preview`
p95 < 400 ms (catálogo cacheado en memoria por proceso, invalidado tras ingesta).

---

## 10. Frontend (PWA)

### 10.1 Dirección de diseño
- Concepto **«Forja»**: taller industrial cálido. Modo oscuro por defecto (carbón `#16181B`,
  superficies `#1F2226`/`#2A2E33`), acento **brasa** `#FF6A2B` con degradado a `#FFB23F` solo
  en acciones primarias y récords; modo claro disponible (hueso `#F4F1EC`, tinta `#1B1D20`).
  Semánticos: éxito `#3FB57A`, aviso `#E8B03A`, error `#E5484D`. Contraste AA mínimo.
- Tipografía **autoalojada** (sin CDNs, necesario para PWA offline y privacidad):
  titulares «Archivo» condensada/expandida en pesos 700–800, texto «Inter» o «Atkinson
  Hyperlegible» (ADR), números tabulares para series y cronómetros.
- Mobile-first (360–430 px) con layout de 2–3 columnas en ≥ 1024 px. Objetivos táctiles
  ≥ 48 px en el reproductor; uso con una mano; navegación inferior en móvil
  (Hoy · Rutinas · Biblioteca · Progreso · Perfil), lateral en escritorio.
- Los medios se muestran a **180 px CSS máximo**, dentro de una «placa» con fondo neutro,
  **con la atribución debajo**, `loading="lazy"`, `decoding="async"`, `width`/`height`
  explícitos. Listados usan la miniatura JPG; el GIF solo en detalle y reproductor (y al
  pasar el cursor/mantener pulsado en tarjetas). `prefers-reduced-motion` ⇒ muestra JPG con
  botón «reproducir animación».
- Microinteracciones sobrias (Framer Motion opcional vía ADR): tick al completar serie,
  anillo de progreso del descanso, confeti discreto solo en récord personal.

### 10.2 Pantallas
1. **Onboarding** (4 pasos): cuenta → datos básicos (sexo, fecha de nacimiento, altura,
   peso, experiencia) → PAR-Q → equipamiento y limitaciones. Opción «activar dieta».
2. **Hoy**: sesión del día del programa activo (o «descanso»), botón «Empezar», resumen
   semanal (sesiones hechas/planificadas, volumen), último récord, peso corporal rápido.
3. **Generador (wizard)**: objetivo (tarjetas con explicación) → días/semana y días
   preferidos → sexo (preseleccionado del perfil, se explica qué ajusta) → nivel, duración,
   equipamiento → énfasis y limitaciones → **vista previa** del programa (semana tipo con
   GIFs, series×reps, descansos, minutos estimados, volumen por músculo en gráfico de
   barras, `rationale_es` y `warnings`) → acciones: regenerar con otra semilla, regenerar un
   día, cambiar ejercicio (sheet con alternativas), guardar y activar.
4. **Editor de rutina**: días en pestañas; bloques y ejercicios arrastrables (`dnd-kit`,
   accesible por teclado); crear superserie/circuito; editar series, reps, RIR, tempo,
   descanso, notas; buscador de ejercicios lateral con filtros; validación en vivo con
   avisos del motor (`rebalance_after_edit`); deshacer/rehacer.
5. **Reproductor de sesión**: GIF grande (180 px en placa), nombre, serie actual/total,
   objetivo (reps, RIR, peso sugerido), rendimiento de la última vez, teclado numérico
   propio para peso/reps, botón «Serie hecha» → **temporizador de descanso** (anillo,
   +15 s / −15 s / saltar, vibración y sonido al terminar, notificación si la app está en
   segundo plano), calentamiento de aproximación y calculadora de discos, vista de
   instrucciones paso a paso, cambiar ejercicio en caliente, notas. **Wake Lock** activo.
   Estado persistido en IndexedDB: se sobrevive a recargas y cierres; funciona offline y
   sincroniza con `/sync` al recuperar conexión.
6. **Resumen de sesión**: duración, volumen, series, récords, esfuerzo percibido (1–10).
7. **Biblioteca**: búsqueda instantánea tolerante a acentos y en ES/EN, chips de filtro
   (zona, músculo, equipamiento, patrón, dificultad, favoritos), cuadrícula virtualizada
   (`@tanstack/react-virtual`), mapa muscular SVG clicable (frontal/posterior) como filtro.
   **Detalle**: GIF, músculos (objetivo, secundarios resaltados en el mapa), equipamiento,
   pasos numerados en el idioma elegido (selector con los 10 idiomas), alternativas,
   historial personal y «añadir a rutina».
8. **Progreso**: calendario tipo mapa de calor, gráficas de volumen semanal por grupo,
   e1RM por ejercicio, récords, peso corporal con media móvil de 7 días.
9. **Nutrición** (si activada): objetivo diario (kcal y macros en anillos neutros), plan
   semanal por días/comidas, intercambio de alimentos, lista de la compra marcable,
   ajustes y avisos de seguridad.
10. **Perfil y ajustes**: datos, unidades (kg/lb, cm/in), idioma, tema, sonidos, descansos
    por defecto, exportar/importar/eliminar cuenta, sesiones activas, **Créditos y
    licencias** (MIT del dataset + aviso de Gym visual + commit SHA).
11. **Admin**: usuarios, registro abierto/cerrado, dieta global, ingesta (lanzar, ver
    ejecuciones, diff), salud del sistema.

### 10.3 PWA y offline
- Manifest con iconos maskable, `display: standalone`, `theme_color` carbón.
- Service worker (Workbox): app shell precacheado; `/api/v1/exercises*` stale-while-revalidate;
  miniaturas cache-first con límite (1.400 entradas); GIFs cache-first bajo demanda
  (límite 300 MB configurable) + botón «Descargar biblioteca para uso offline» que precachea
  miniaturas y GIFs del programa activo.
- Cola offline de escrituras (sesiones/series) en IndexedDB con reintento exponencial y
  resolución por `client_uuid`.

### 10.4 Accesibilidad e i18n
WCAG 2.2 AA: foco visible, orden lógico, `aria-live` para el temporizador, textos
alternativos de GIF = nombre del ejercicio, controles con etiqueta, sin información solo por
color. i18n completo (`es` por defecto, `en`), formateo de números/fechas con `Intl`.

### 10.5 Rendimiento
Lighthouse móvil ≥ 90 en Rendimiento, Accesibilidad, Buenas prácticas y PWA; JS inicial
< 200 KB gzip (code-splitting por ruta; Recharts y editor en chunks diferidos); LCP < 2,5 s
en red 4G simulada.

---

## 11. Seguridad y privacidad

- Contraseñas **argon2id** (`argon2-cffi`, parámetros OWASP), política mínima 10 caracteres
  + comprobación contra lista local de contraseñas comunes.
- Sesiones con token opaco aleatorio (32 bytes), guardado hasheado; cookie `__Host-forja_session`
  `HttpOnly; Secure; SameSite=Lax`; expiración deslizante 30 días; revocación desde ajustes.
- CSRF: doble envío (cookie + cabecera `X-CSRF-Token`) en métodos no seguros.
- Rate limiting (login, registro, generador) en la app y `limit_req` en nginx.
- Cabeceras: CSP estricta (`default-src 'self'`; `img-src 'self' data: blob:`; sin inline
  scripts), HSTS, `X-Content-Type-Options`, `Referrer-Policy: same-origin`,
  `Permissions-Policy` mínima.
- Autorización por propietario en todas las rutas de usuario (tests que intentan acceder a
  recursos de otro usuario ⇒ 404).
- Validación Pydantic en toda entrada; límites de tamaño de cuerpo; importación JSON validada
  contra esquema y con límite de tamaño.
- Datos de salud (PAR-Q, peso, dieta) se tratan como sensibles: nunca en logs, borrables,
  exportables. Logs estructurados JSON sin PII (hash de IP).
- Dependencias: `pip-audit`, `npm audit --omit=dev`, Trivy sobre imágenes en CI; imágenes
  sin root, sistema de ficheros de solo lectura donde sea posible.

---

## 12. Despliegue (Proxmox LXC + Docker + nginx)

### 12.1 Contenedores (`deploy/docker-compose.yml`)
- `db`: `postgres:16-alpine`, volumen `pgdata`, healthcheck, sin puerto publicado.
- `api`: imagen multi-stage (builder con `uv`, runtime `python:3.12-slim`, usuario no root),
  `gunicorn -k uvicorn.workers.UvicornWorker`, `alembic upgrade head` en `entrypoint` con
  bloqueo consultivo, healthcheck `/api/v1/ready`.
- `web`: nginx que sirve `frontend/dist`, `/media` desde volumen `media` (solo lectura) y
  proxifica `/api`. Config en `deploy/nginx/forja.conf` con: gzip/brotli para estáticos,
  `Cache-Control: public, max-age=31536000, immutable` para `/assets` y `/media` (los nombres
  llevan hash/`media_id`), `auth_request /api/v1/auth/check` en `/media` cuando
  `MEDIA_REQUIRE_AUTH=true`, `limit_req`, cabeceras de seguridad, `client_max_body_size 5m`.
- `ingest`: servicio de un solo uso (`profiles: ["tools"]`) que ejecuta `forja-ingest fetch
  && forja-ingest load`.
- Red interna; solo `web` publica puerto (por defecto `8080`) para el nginx/reverse proxy
  existente del propietario, que termina TLS. Documentar también la variante en la que el
  nginx de Forja termina TLS directamente.

### 12.2 LXC en Proxmox (`deploy/lxc/`)
- `README.md` paso a paso: crear CT Debian 12 (2 vCPU, 2–4 GB RAM, 12 GB disco + volumen de
  datos), `features: nesting=1,keyctl=1`, instalar Docker Engine y compose plugin, clonar,
  `cp .env.example .env`, `make bootstrap` (genera secretos, ejecuta ingesta, crea admin).
- Bloque de ejemplo para el reverse proxy nginx externo (server block con `proxy_pass`,
  cabeceras `X-Forwarded-*`, websockets no necesarios, `client_max_body_size`).

### 12.3 Operación
- `Makefile`: `bootstrap`, `up`, `down`, `logs`, `migrate`, `ingest`, `backup`, `restore`,
  `create-admin`, `test`, `lint`.
- Copias: `deploy/backup/backup.sh` con `pg_dump -Fc` diario y rotación (7 diarias, 4
  semanales), más script de restauración probado en CI con una BD efímera. Los medios se
  regeneran con la ingesta (no requieren copia).
- Configuración solo por variables de entorno (`.env.example` completo y comentado):
  `DATABASE_URL`, `SECRET_KEY`, `PUBLIC_BASE_URL`, `MEDIA_ROOT`, `MEDIA_REQUIRE_AUTH`,
  `DATASET_REPO`, `DATASET_COMMIT`, `REGISTRATION_OPEN`, `DIET_FEATURE_ENABLED`,
  `DEFAULT_LOCALE`, `LOG_LEVEL`, `GUNICORN_WORKERS`.
- Observabilidad: logs JSON a stdout, `/metrics` Prometheus opcional (flag), request id
  propagado.

---

## 13. Testing y calidad

| Nivel | Herramientas | Alcance mínimo |
|---|---|---|
| Unit motor | pytest + hypothesis | 100 % líneas, ≥ 95 % ramas, propiedades de §7.8 |
| Unit nutrición | pytest + hypothesis | 100 % líneas, propiedades de §8.6 |
| Ingesta | pytest sobre fixture de 60 ejercicios reales + test de integración con el dataset completo (marcado `slow`) | vocabularios 100 % mapeados, nombres ES 100 %, checksums |
| Backend | pytest-asyncio + httpx + testcontainers | ≥ 90 %; autorización cruzada; migraciones up/down; contrato OpenAPI |
| Frontend | Vitest + Testing Library + MSW | ≥ 85 %; wizard, editor, reproductor (máquina de estados), cola offline |
| E2E | Playwright (Chromium + WebKit móvil) contra `docker compose` | onboarding → generar → activar → entrenar sesión completa con descanso → ver progreso; modo offline en reproductor; dieta; exportar PDF/ICS; admin ingesta |
| A11y | `@axe-core/playwright` | 0 violaciones serias/críticas en todas las pantallas |
| Rendimiento | Lighthouse CI | umbrales de §10.5 |
| Seguridad | pip-audit, npm audit, Trivy, tests de cabeceras y CSRF | sin vulnerabilidades altas/críticas |

CI (`.github/workflows/ci.yml`): lint → tipos → unit → integración → build de imágenes →
E2E → Lighthouse → informe de cobertura; falla por debajo de umbrales.

---

## 14. Ejecución multiagente (resumen; detalle en `ORCHESTRATION.md`)

| Fase | Agentes | Entregable / puerta |
|---|---|---|
| 0 · Fundaciones | `arquitecto` | Monorepo, `contracts/openapi.yaml`, `contracts/domain.md`, ADRs, `docs/TASKS.md`, CI esqueleto verde. **Puerta**: el orquestador revisa contratos |
| 1 · Núcleo (paralelo) | `ingesta-datos`, `motor-rutinas`, `motor-nutricion`, `frontend-ui` (sistema de diseño + shell + mocks MSW desde OpenAPI) | Ingesta completa con informes; motores con cobertura objetivo; shell navegable |
| 1b · Revisión de dominio | `experto-entrenamiento` | Aprueba enriquecimiento, staples, nombres ES, tablas YAML y snapshots |
| 2 · Integración (paralelo) | `backend-api`, `frontend-ui` (features contra MSW → API real) | API completa con tests; pantallas completas |
| 3 · Endurecimiento (paralelo) | `devops-despliegue`, `qa-tests`, `revisor-seguridad` | Compose + nginx + LXC + backups; E2E/a11y/Lighthouse; informe de seguridad sin altos |
| 4 · Cierre | orquestador + `qa-tests` | Checklist de §15 completo, `CHANGELOG.md`, `docs/USER_GUIDE.md` |

Protocolo de traspaso: cada agente termina escribiendo `docs/handoffs/<fase>-<agente>.md`
(qué hizo, decisiones, cómo probarlo, riesgos, qué necesita de otros) y actualizando
`docs/TASKS.md`.

---

## 15. Definition of Done global

- [ ] `make bootstrap && make up` en un LXC limpio deja la app operativa con los 1.324
      ejercicios, sus 1.324 GIF y 1.324 miniaturas verificados por checksum.
- [ ] Atribución de Gym visual visible en toda vista con medios; medios servidos sin
      modificar y tras autenticación por defecto; Créditos con licencias y SHA.
- [ ] Generador produce programas válidos para las 1.890 combinaciones de §7.8 y los 12
      snapshots aprobados por el experto.
- [ ] Flujo completo E2E en móvil y escritorio, incluido offline en el reproductor.
- [ ] Dieta desactivable, con suelos de seguridad probados.
- [ ] Umbrales de cobertura, lint, tipos, a11y, Lighthouse y seguridad en verde en CI.
- [ ] Sin `TODO`/placeholders (`grep` en CI), sin secretos en el repo.
- [ ] Documentación: `README.md`, `docs/USER_GUIDE.md` (ES), `deploy/lxc/README.md`,
      ADRs, `CHANGELOG.md`.

---

## 16. Glosario
- **RIR**: repeticiones en reserva. **e1RM**: 1RM estimado. **Serie efectiva**: serie a
  RIR ≤ 4. **Mesociclo**: bloque de 4–8 semanas con descarga final. **Staple**: ejercicio
  fundamental preferido para slots principales. **Slot**: hueco de un día definido por patrón
  y rol. **Split**: reparto de grupos musculares por días. **E/T/P**: empuje/tirón/pierna.

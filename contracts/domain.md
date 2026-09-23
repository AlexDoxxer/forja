# Modelo de dominio de Forja · contrato v1.0.0

> Contrato compartido entre `ingesta-datos`, `motor-rutinas`, `motor-nutricion`,
> `backend-api` y `frontend-ui`. Fuente: MASTER_PROMPT §5–§9. Cambios **solo** vía
> `docs/CONTRACT_CHANGES.md` con aprobación del arquitecto (ADR 0002). La forma JSON exacta
> de cada DTO está en `contracts/openapi.yaml` (`components/schemas`), que es el esquema
> normativo; este documento fija además tipos Python, invariantes, tablas y la API pública de
> los motores.

## 1. Convenciones

| Tema | Regla |
|---|---|
| Identificadores | UUID v7 (`uuid.UUID`, texto en JSON) en todas las tablas, salvo `exercise.id`, que conserva el id del dataset (`"0001"`, `^[0-9]{4}$`), y `food.id`, slug `^[a-z0-9]+(?:_[a-z0-9]+)*$`. |
| Tiempo | `created_at`/`updated_at` `timestamptz` en todas las tablas; JSON en ISO 8601 UTC (`2026-09-22T17:05:00Z`). Fechas de calendario como `date` (`2026-09-22`). La semana empieza en lunes. |
| Unidades | Siempre métricas en BD, API y motores: kg, cm, segundos, kcal, gramos. La conversión a imperial es solo de presentación (frontend). |
| Índices | `index`, `order`, `day_index`, `week_index` empiezan en **0**. La UI muestra `+1`. `set_index` empieza en 1 (numeración de series visible). |
| Textos | Campos con sufijo `_es` en español. Códigos y enumeraciones en inglés `snake_case`. |
| Semillas | Enteros `0 ≤ seed ≤ 2^53−1` (seguros en JavaScript). |
| Inmutabilidad | Los DTOs de los motores son modelos Pydantic v2 `frozen=True`, `extra="forbid"`; las secuencias son `tuple[...]`. |
| Dinero, PII | No hay datos de pago. Datos de salud (PAR-Q, peso, embarazo/lactancia, limitaciones) son sensibles: nunca en logs, siempre exportables y borrables. |

Tipos Python usados abajo: `ExerciseId = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}$")]`,
`FoodId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=64)]`,
`Seed = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]`, `Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]`.

## 2. Glosario

- **RIR**: repeticiones en reserva. **Serie efectiva**: serie a RIR ≤ 4.
- **e1RM**: 1RM estimado con Epley `w·(1 + r/30)` para reps efectivas (reps + RIR) ≤ 10.
- **Mesociclo**: bloque de 4–8 semanas con descarga final. **Split**: reparto de días.
- **Slot**: hueco de un día del split definido por patrón, rol, grupo y prioridad.
- **Staple**: ejercicio fundamental preferido para slots `main`.
- **Variant group**: agrupa `v. N`, `(male)`/`(female)`, `(back pov)`/`(side pov)` y nombres duplicados.
- **E/T/P**: empuje / tirón / pierna.

## 3. Enumeraciones

Todas son `StrEnum` en Python y `enum` en OpenAPI con el mismo nombre de esquema.

| Enumeración | Valores (etiqueta ES) | Notas |
|---|---|---|
| `Sex` | `male` (hombre), `female` (mujer), `unspecified` (prefiero no indicarlo) | Solo preselección y ajustes finos (§7.4, `specs/sex-modifiers.yaml`). Nunca excluye ejercicios ni limita cargas. |
| `Experience` | `beginner` (principiante), `intermediate` (intermedio), `advanced` (avanzado) | PAR-Q marcado ⇒ `beginner` salvo cambio explícito. |
| `Goal` | `strength` (fuerza), `hypertrophy` (hipertrofia), `fat_loss` (pérdida de grasa), `endurance` (resistencia), `general_fitness` (forma general), `toning` (tonificación/recomposición) | |
| `Emphasis` | `balanced` (equilibrado), `lower_glutes` (tren inferior y glúteo), `upper_body` (tren superior), `arms` (brazos), `back_posture` (espalda y postura), `core` (core) | |
| `EquipmentPreset` | `full_gym` (gimnasio completo), `home_dumbbells` (casa con mancuernas), `home_bands` (casa con bandas), `bodyweight` (peso corporal), `custom` (personalizado) | Resolución en `specs/equipment-normalization.yaml#presets`. |
| `EquipmentCode` | `bodyweight`, `dumbbell`, `cable`, `barbell`, `ez_bar`, `trap_bar`, `machine`, `smith`, `sled`, `assisted`, `band`, `kettlebell`, `weighted`, `stability_ball`, `medicine_ball`, `bosu`, `rope`, `roller`, `ab_wheel`, `hammer`, `tire`, `arm_ergometer`, `skierg`, `bike`, `elliptical`, `stepmill` | 26 códigos; nombres ES en `specs/equipment-normalization.yaml`. |
| `EquipmentGroup` | `gym`, `home_basic`, `bodyweight`, `cardio_machine`, `other` | |
| `MuscleCode` | `chest`, `lats`, `upper_back`, `traps`, `lower_back`, `shoulders`, `rear_delts`, `rotator_cuff`, `serratus`, `biceps`, `triceps`, `forearms`, `abs`, `obliques`, `hip_flexors`, `glutes`, `quads`, `hamstrings`, `adductors`, `abductors`, `calves`, `lower_leg`, `neck`, `cardio` | 24 códigos canónicos de `specs/muscle-normalization.yaml#canonical`. |
| `MuscleRegion` | `upper`, `lower`, `core`, `cardio`, `other` | |
| `VolumeGroup` | `chest`, `back`, `shoulders`, `arms`, `quads`, `hamstrings`, `glutes`, `calves`, `core` | Grupos que computan volumen (`specs/volume-targets.yaml#groups`). |
| `MuscleGroup` | `VolumeGroup` ∪ {`legs_other`, `other`, `cardio`} | Grupo de un slot; los tres extra no computan volumen. |
| `BodyPart` | `upper_arms`, `upper_legs`, `back`, `waist`, `chest`, `shoulders`, `lower_legs`, `lower_arms`, `cardio`, `neck` | `body_part` del dataset con espacios → `_`. |
| `MovementPattern` | `squat`, `lunge`, `hinge`, `horizontal_push`, `vertical_push`, `horizontal_pull`, `vertical_pull`, `elbow_flexion`, `elbow_extension`, `shoulder_raise`, `chest_fly`, `rear_delt`, `knee_extension`, `knee_flexion`, `hip_abduction`, `hip_adduction`, `glute_isolation`, `calf`, `core_flexion`, `core_anti_extension`, `core_rotation`, `core_lateral`, `shrug`, `forearm`, `neck`, `carry`, `plyometric`, `cardio`, `mobility`, `other` | 30 valores (§6.3). Patrones principales: `squat`, `lunge`, `hinge`, `horizontal_push`, `vertical_push`, `horizontal_pull`, `vertical_pull`. |
| `Mechanic` | `compound` (multiarticular), `isolation` (aislamiento) | |
| `ExerciseRole` | `main`, `accessory`, `core`, `cardio`, `mobility`, `warmup` | También rol de slot. `mobility`/`cardio` nunca en slots `main`. |
| `Difficulty` | `1` (básico), `2` (estándar), `3` (exigente) | `int` 1–3. |
| `Laterality` | `bilateral`, `unilateral` | |
| `DemoSex` | `male`, `female` | Sexo del demostrador del medio; `null` si no hay sufijo. |
| `LoadType` | `external` (carga externa), `bodyweight` (peso corporal), `assisted` (asistido), `time` (por tiempo) | |
| `VariantKind` | `version` (`v. N`), `demonstrator` (`(male)`/`(female)`), `camera_angle` (`(back pov)`/`(side pov)`), `duplicate` (mismo nombre, otro id) | |
| `UserRole` | `user`, `admin` | El primer usuario registrado es `admin`. |
| `Units` | `metric`, `imperial` | |
| `Locale` | `es`, `en` | Idioma de la UI. |
| `InstructionLang` | `en`, `es`, `it`, `tr`, `ru`, `zh`, `hi`, `pl`, `ko`, `fr` | Idiomas de instrucciones del dataset. |
| `ActivityLevel` | `sedentary` (sedentario), `light` (ligero), `moderate` (moderado), `high` (alto) | |
| `ThemePreference` | `dark`, `light`, `system` | |
| `Weekday` | `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` | |
| `ProgramSource` | `generated`, `manual`, `imported` | |
| `WeekPhase` | `accumulation` (acumulación), `intensification` (intensificación), `deload` (descarga) | `intensification` se reserva para ondulación de fuerza (§7.2 paso 8). |
| `BlockKind` | `warmup`, `main`, `superset`, `circuit`, `finisher`, `cooldown` | |
| `SessionStatus` | `in_progress`, `completed`, `abandoned` | |
| `RecordKind` | `e1rm`, `heaviest_set` (mejor peso×reps), `volume` (mayor volumen en una sesión) | |
| `SuggestionKind` | `first_time`, `increase_load`, `increase_reps`, `harder_variant`, `hold`, `decrease_load` | §7.6. |
| `PlanWarningCode` | `beginner_high_frequency`, `recovery_day_enforced`, `slot_relaxed`, `slot_dropped`, `time_budget_exceeded`, `main_exercise_trimmed`, `volume_out_of_range`, `session_group_cap`, `rest_below_minimum`, `empty_day`, `mobility_in_main_block`, `equipment_insufficient`, `avoided_muscle_substituted`, `deprecated_exercise` | Códigos estables; el texto va en `message_es`. |
| `NutritionGoal` | `lose` (perder grasa), `maintain` (mantener), `gain` (ganar), `recomp` (recomposición) | |
| `NutritionPace` | `gentle` (suave), `standard` (estándar) | |
| `DietType` | `omnivore`, `pescatarian`, `vegetarian`, `vegan` | |
| `Allergen` | `gluten`, `lactose`, `tree_nuts` (frutos secos), `egg`, `fish`, `shellfish` (marisco), `soy` | |
| `MealSlot` | `breakfast` (desayuno), `mid_morning` (media mañana), `lunch` (comida), `snack` (merienda), `dinner` (cena) | Plantillas en `specs/nutrition.yaml#meal_templates`. |
| `FoodCategory` | `fruits`, `vegetables`, `legumes`, `grains`, `bakery`, `dairy`, `eggs`, `meat`, `fish_seafood`, `plant_protein`, `nuts_seeds`, `fats_oils`, `condiments`, `beverages` | Orden = orden de la lista de la compra. |
| `FoodMacroRole` | `protein`, `carb`, `produce`, `fat` | Papel en la plantilla mediterránea. |
| `BmrMethod` | `mifflin_male`, `mifflin_female`, `mifflin_average` | `unspecified` ⇒ media. |
| `NutritionBlockReason` | `under_18`, `pregnant`, `breastfeeding`, `missing_profile_data` | Bloqueo total: no se genera plan. |
| `NutritionNoticeCode` | `health_disclaimer`, `kcal_floor_applied`, `deficit_capped`, `lose_blocked_low_bmi`, `protein_clamped`, `fat_floor_applied`, `tolerance_not_met`, `swap_macros_adjusted` | Avisos no bloqueantes. |
| `IngestStatus` | `queued`, `running`, `succeeded`, `failed` | |
| `SyncResultStatus` | `applied`, `duplicate`, `superseded`, `rejected` | ADR 0006. |

## 4. Entidades (PostgreSQL 16)

Todas las tablas tienen `created_at timestamptz not null default now()` y
`updated_at timestamptz not null` (actualizado por la aplicación) salvo donde se indique.
Tipos: `uuid` (v7 generado en aplicación), `text`, `citext`, `int`, `numeric(p,s)`, `bool`,
`jsonb`, `date`, `timestamptz`, `tsvector`. Enumeraciones como `text` con `CHECK` (no tipos
`ENUM` de PostgreSQL, para migraciones reversibles sencillas).

### 4.1 Catálogo (escritura solo por ingesta/admin)

**`muscle`** — `code text PK` (MuscleCode) · `name_es text` · `name_en text` · `region text` (MuscleRegion) · `volume_group text null` (MuscleGroup de `specs/muscle-normalization.yaml#canonical.group`).

**`equipment`** — `code text PK` (EquipmentCode) · `name_es text` · `name_en text` · `group text` (EquipmentGroup).

**`exercise`**
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `text PK` | `^[0-9]{4}$` del dataset |
| `media_id` | `text` | |
| `name_en` | `text` | original, intacto |
| `display_name_en` | `text` | erratas y mojibake corregidos, sin sufijos de variante |
| `name_es` | `text` | de `specs/overrides/names_es.json` |
| `slug` | `text unique` | |
| `body_part` | `text` | BodyPart |
| `equipment_code` | `text FK equipment` | |
| `target_muscle` | `text FK muscle` | |
| `primary_group_muscle` | `text FK muscle` | de `muscle_group` |
| `movement_pattern` | `text` | MovementPattern |
| `mechanic` | `text` | Mechanic |
| `role` | `text` | ExerciseRole |
| `difficulty` | `smallint` | 1–3 |
| `is_staple` | `bool` | |
| `laterality` | `text` | Laterality |
| `demo_sex` | `text null` | DemoSex |
| `variant_group` | `text` | índice |
| `variant_kind` | `text null` | VariantKind (null en el ejercicio base) |
| `variant_label_es` | `text null` | «variante 2», «vista trasera», «(variante B)» |
| `load_type` | `text` | LoadType |
| `thumb_path`, `gif_path` | `text` | relativos a `MEDIA_ROOT` (`thumbs/<id>-<media_id>.jpg`, `gifs/<id>-<media_id>.gif`) |
| `media_sha256_thumb`, `media_sha256_gif` | `char(64)` | |
| `source_commit` | `char(40)` | |
| `deprecated_at` | `timestamptz null` | nunca se borran ejercicios referenciados |
| `search_vector` | `tsvector` | `unaccent`, pesos A=`name_es`/`display_name_en`, B=músculos/equipo ES/EN |
| `enrichment_version` | `int` | versión de `specs/enrichment-rules.yaml` |

Índices: GIN(`search_vector`), GIN trigram (`name_es gin_trgm_ops`), GIN trigram (`display_name_en gin_trgm_ops`), btree(`movement_pattern`), btree(`equipment_code`), btree(`target_muscle`), btree(`variant_group`).

**`exercise_secondary_muscle`** — PK(`exercise_id`, `muscle_code`).
**`exercise_instruction`** — PK(`exercise_id`, `lang`) · `text text` · `steps jsonb` (array de strings, 4–11 elementos).
**`exercise_alternative`** — PK(`exercise_id`, `alt_id`) · `score numeric(4,3)` · `rank smallint` (1–8). Precalculada en ingesta (§6.5).

### 4.2 Usuarios y perfil

**`user`** — `id uuid PK` · `email citext unique` · `password_hash text` (argon2id) · `display_name text` · `role text` (UserRole) · `locale text` (Locale) · `units text` (Units) · `is_active bool` · `last_login_at timestamptz null`.

**`session`** (sesión de autenticación) — `id uuid PK` · `user_id FK user on delete cascade` · `token_hash char(64) unique` (SHA-256 del token opaco) · `expires_at timestamptz` · `last_seen_at timestamptz` · `user_agent text null` (≤ 256) · `ip_hash char(64) null` (HMAC-SHA-256 con `SECRET_KEY`) · `revoked_at timestamptz null`. Índice (`user_id`, `revoked_at`).

**`profile`** (1:1, PK = `user_id`) — `sex text` · `birth_date date null` · `height_cm numeric(5,1) null` · `experience text` · `activity_level text` · `equipment_profile jsonb` (EquipmentSelection) · `limitations jsonb` (Limitations) · `parq_answers jsonb null` (ParqAnswers) · `parq_flagged bool` · `parq_completed_at timestamptz null` · `diet_enabled bool` · `preferences jsonb` (Preferences).

**`body_metric`** — `id uuid PK` · `user_id FK` · `date date` · `weight_kg numeric(5,2)` · `body_fat_pct numeric(4,1) null` · `waist_cm numeric(5,1) null`. Único (`user_id`, `date`).

**`favorite_exercise`** — PK(`user_id`, `exercise_id`).

### 4.3 Programas y sesiones

**`program`** — `id uuid PK` · `user_id FK` · `name text` · `source text` (ProgramSource) · `generator_input jsonb null` (GeneratorInput normalizado) · `generator_version text null` · `tables_hash char(64) null` · `seed bigint null` · `goal text null` · `days_per_week smallint` · `weeks smallint` · `is_active bool` · `archived_at timestamptz null` · `weekly_volume jsonb` (GroupVolume[]) · `warnings jsonb` (PlanWarning[]) · `rationale_es jsonb` (string[]). Índice único parcial (`user_id`) `WHERE is_active` (máx. 1 activo).

**`program_week`** — `id uuid PK` · `program_id FK cascade` · `index smallint` · `phase text` (WeekPhase) · `target_rir smallint` · `volume_ratio numeric(3,2)`. Único (`program_id`, `index`).

**`program_day`** — `id uuid PK` · `week_id FK cascade` · `index smallint` · `template text null` · `name text` · `focus text null` · `weekday text null` · `is_recovery bool` · `estimated_minutes smallint`. Único (`week_id`, `index`).

**`program_block`** — `id uuid PK` · `day_id FK cascade` · `order smallint` · `kind text` (BlockKind) · `rounds smallint` · `rest_between_rounds_s smallint null`.

**`program_exercise`** — `id uuid PK` · `block_id FK cascade` · `order smallint` · `exercise_id FK exercise` · `slot jsonb null` (SlotRef) · `sets smallint` · `rep_min smallint null` · `rep_max smallint null` · `target_rir smallint null` · `tempo text null` · `rest_s smallint` · `duration_s int null` · `per_side bool` · `load_hint text null` · `notes_es text null` · `alternatives jsonb` (ExerciseId[] ≤ 3). CHECK (`rep_min` y `rep_max` no nulos) OR (`duration_s` no nulo); CHECK `rep_min ≤ rep_max`.

**`workout_session`** — `id uuid PK` · `user_id FK` · `client_uuid uuid` · `program_id uuid null FK on delete set null` · `program_day_id uuid null FK on delete set null` · `name text` · `started_at timestamptz` · `finished_at timestamptz null` · `status text` (SessionStatus) · `perceived_effort smallint null` (1–10) · `notes text null` · `client_updated_at timestamptz` (resolución de conflictos, ADR 0006). Único (`user_id`, `client_uuid`). Índice (`user_id`, `started_at desc`).

**`set_log`** — `id uuid PK` · `session_id FK cascade` · `exercise_id FK exercise` · `program_exercise_id uuid null FK on delete set null` · `set_index smallint` · `weight_kg numeric(6,2) null` · `reps smallint null` · `rir smallint null` · `duration_s int null` · `is_warmup bool` · `completed_at timestamptz` · `client_uuid uuid` · `client_updated_at timestamptz` · `deleted_at timestamptz null` (tombstone para `/sync`). Único (`client_uuid`). Índice (`session_id`, `exercise_id`).

**`personal_record`** — `id uuid PK` · `user_id FK` · `exercise_id FK` · `kind text` (RecordKind) · `value numeric(8,2)` · `weight_kg numeric(6,2) null` · `reps smallint null` · `achieved_at timestamptz` · `session_id FK cascade` · `set_id uuid null FK on delete set null`. Único (`user_id`, `exercise_id`, `kind`). Mantenido por el servicio al registrar/editar/borrar series.

**`idempotency_key`** — PK(`user_id`, `key`) · `request_hash char(64)` · `status_code smallint` · `response jsonb` · `expires_at timestamptz` (24 h). Soporta la cabecera `Idempotency-Key`.

### 4.4 Nutrición

**`nutrition_settings`** (1:1, PK = `user_id`) — `goal text` · `pace text` · `diet_type text` · `meals_per_day smallint` (3–5) · `allergens jsonb` · `excluded_food_ids jsonb` · `disliked_food_ids jsonb` · `pregnant bool` · `breastfeeding bool`. (Ampliación de §5.4: los ajustes de §8.1 necesitan persistencia.)

**`food`** — espejo de `foods.json` cargado al arrancar/migrar: `id text PK` · `name_es text` · `category text` · `fdc_id int` · `per_100g jsonb` (MacroTotals) · `diet_types jsonb` · `allergens jsonb` · `macro_role text` · `typical_portion_g numeric(6,1)` · `unit_grams numeric(6,1) null` · `unit_name_es text null`. Índice trigram en `name_es` (búsqueda `GET /foods`).

**`nutrition_target`** — `id uuid PK` · `user_id FK` · `calculated_at timestamptz` · `input jsonb` (NutritionInput) · `result jsonb` (NutritionTarget) · columnas desnormalizadas `kcal`, `protein_g`, `fat_g`, `carbs_g`, `fiber_g` `numeric(7,1) null` y `method text`.

**`meal_plan`** — `id uuid PK` · `user_id FK` · `week_start date` · `diet_type text` · `meals_per_day smallint` · `input jsonb` (NutritionInput) · `seed bigint` · `nutrition_version text` · `foods_hash char(64)` · `target jsonb` (NutritionTarget) · `notices jsonb`.

**`meal_plan_item`** — `id uuid PK` · `plan_id FK cascade` · `day smallint` (0–6) · `meal text` (MealSlot) · `position smallint` · `food_id FK food` · `grams numeric(6,1)` · `units smallint null`.

`shopping_list` no se persiste: se deriva del plan en cada petición.

### 4.5 Sistema

**`app_setting`** — `key text PK` · `value jsonb`. Claves: `registration_open` (bool), `diet_feature_enabled` (bool). `MEDIA_REQUIRE_AUTH` es solo de entorno (se expone como efectivo, solo lectura).
**`audit_log`** — `id uuid PK` · `actor_user_id uuid null` · `action text` (p. ej. `admin.settings.update`, `auth.login.failed`, `user.delete`) · `target text null` · `details jsonb` (sin datos de salud ni contraseñas) · `ip_hash char(64) null` · `created_at`. Sin `updated_at` (solo inserción).
**`ingest_run`** — `id uuid PK` · `commit char(40)` · `status text` (IngestStatus) · `dry_run bool` · `triggered_by uuid null` · `started_at`, `finished_at` `timestamptz null` · `counts jsonb` (IngestCounts) · `diff jsonb` (IngestDiff) · `checksums_sha256 char(64)` (hash del `manifest.json`) · `errors jsonb` · `warnings jsonb`.

## 5. DTOs del motor de rutinas (`forja_engine.models`)

Modelos Pydantic v2 `frozen=True, extra="forbid"`. Serializan exactamente a los esquemas
OpenAPI homónimos.

### 5.1 `ExerciseCard` (catálogo de entrada, lo exporta `forja-ingest export-cards`)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | `ExerciseId` | |
| `name_es` | `str` | |
| `display_name_en` | `str` | |
| `variant_group` | `str` | |
| `body_part` | `BodyPart` | |
| `equipment_code` | `EquipmentCode` | |
| `equipment_group` | `EquipmentGroup` | |
| `target_muscle` | `MuscleCode` | |
| `primary_group_muscle` | `MuscleCode` | |
| `secondary_muscles` | `tuple[MuscleCode, ...]` | sin duplicados, orden estable |
| `movement_pattern` | `MovementPattern` | |
| `mechanic` | `Mechanic` | |
| `role` | `ExerciseRole` | |
| `difficulty` | `int` (1–3) | |
| `is_staple` | `bool` | |
| `laterality` | `Laterality` | |
| `load_type` | `LoadType` | |
| `demo_sex` | `DemoSex \| None` | |
| `deprecated` | `bool` | los `deprecated` nunca se seleccionan en planes nuevos |

El catálogo es `tuple[ExerciseCard, ...]` ordenada por `id`; el fixture congelado vive en
`engine/tests/fixtures/catalog.json` (lista JSON de `ExerciseCard`).

### 5.2 `EquipmentSelection`, `GeneratorInput`
`EquipmentSelection`: `preset: EquipmentPreset`, `items: tuple[EquipmentCode, ...]`
(con `custom`, mínimo 1; con otro preset, vacío en la entrada y resuelto en la salida).

| Campo | Tipo | Defecto | Invariantes |
|---|---|---|---|
| `goal` | `Goal` | — | |
| `days_per_week` | `int` | — | 1–7 |
| `sex` | `Sex` | — | |
| `experience` | `Experience` | — | |
| `session_minutes` | `int` | — | 20–120, múltiplo de 5 |
| `equipment` | `EquipmentSelection` | — | |
| `emphasis` | `Emphasis` | `balanced` | el wizard preselecciona según `specs/sex-modifiers.yaml` |
| `avoid_muscles` | `tuple[MuscleCode, ...]` | `()` | sin duplicados |
| `avoid_patterns` | `tuple[MovementPattern, ...]` | `()` | sin duplicados |
| `preferred_days` | `tuple[Weekday, ...]` | `()` | vacía o longitud = `days_per_week`, sin duplicados |
| `weeks` | `int` | `5` | 4–8, incluye descarga |
| `include_warmup` | `bool \| None` | `None` | `None` ⇒ defecto por objetivo |
| `include_cooldown` | `bool \| None` | `None` | ídem |
| `include_cardio_finisher` | `bool \| None` | `None` | ídem (`fat_loss`/`toning` ⇒ sí) |
| `favorite_exercise_ids` | `tuple[ExerciseId, ...]` | `()` | ≤ 200 |
| `excluded_exercise_ids` | `tuple[ExerciseId, ...]` | `()` | ≤ 500 |
| `seed` | `Seed \| None` | `None` | `None` ⇒ derivada de SHA-256 de la entrada normalizada (JSON canónico) |

La **entrada normalizada** (`ProgramPlan.input`) tiene todos los defectos resueltos
(`include_*` a `bool`, `equipment.items` resuelto y ordenado, listas ordenadas) y `seed`
no nulo.

### 5.3 `ProgramPlan` y anidados

`ExercisePrescription`
| Campo | Tipo | Invariantes |
|---|---|---|
| `exercise_id` | `ExerciseId` | existe en el catálogo y no está excluido |
| `sets` | `int` | 1–10 |
| `rep_min`, `rep_max` | `int \| None` | 1–100, `rep_min ≤ rep_max` |
| `duration_s` | `int \| None` | 5–3600; exactamente uno de {rango de reps, `duration_s`} informado |
| `per_side` | `bool` | |
| `target_rir` | `int \| None` | 0–5; `None` en calentamiento/estiramientos |
| `tempo` | `str \| None` | `^[0-9X]-[0-9X]-[0-9X]-[0-9X]$` |
| `rest_s` | `int` | 0–600, ≥ `specs/prescription.yaml#min_rest_s` según rol |
| `load_hint` | `str \| None` | ES, ≤ 200 |
| `notes_es` | `str \| None` | ≤ 500 |
| `alternatives` | `tuple[ExerciseId, ...]` | ≤ 3, mismo filtro que la selección |

`SlotRef`: `slot_index: int ≥ 0`, `pattern: MovementPattern`, `role: ExerciseRole`,
`group: MuscleGroup`, `priority: int` (1–3).

`PlanExercise` = `ExercisePrescription` + `order: int ≥ 0` + `slot: SlotRef | None`
(`None` en calentamiento, vuelta a la calma y finisher).

`PlanBlock`: `order: int`, `kind: BlockKind`, `rounds: int` (1–10; 1 salvo superserie/circuito),
`rest_between_rounds_s: int | None`, `exercises: tuple[PlanExercise, ...]` (≥ 1; superserie ⇒ 2–3).

`GroupSets`: `group: VolumeGroup`, `sets: float` (0–10, series efectivas del día).

`PlanDay`: `index: int` (0–6), `template: str`, `name_es: str`, `focus_es: str`,
`weekday: Weekday | None`, `is_recovery: bool`, `estimated_minutes: int`,
`blocks: tuple[PlanBlock, ...]`, `volume: tuple[GroupSets, ...]`.

`PlanWeek`: `index: int` (0–7), `phase: WeekPhase`, `target_rir: int`, `volume_ratio: float`,
`days: tuple[PlanDay, ...]` (longitud = `days_per_week`).

`GroupVolume`: `group: VolumeGroup`, `target_min: float`, `target_max: float`,
`planned_sets: float` (semana tipo, compuestos 1,0 al objetivo y 0,5 a secundarios relevantes).

`PlanWarning`: `code: PlanWarningCode`, `message_es: str`, `week_index: int | None`,
`day_index: int | None`, `exercise_id: ExerciseId | None`.

`SlotAddress`: `week_index`, `day_index`, `block_order`, `exercise_order` (todos `int ≥ 0`).

`ProgramPlan`
| Campo | Tipo | Notas |
|---|---|---|
| `engine_version` | `str` | `forja_engine.ENGINE_VERSION` |
| `tables_hash` | `Sha256` | SHA-256 del contenido canónico de los YAML cargados |
| `seed` | `Seed` | semilla efectiva |
| `input` | `GeneratorInput` | normalizada |
| `split` | `tuple[str, ...]` | claves de `day_templates`, longitud = `days_per_week` |
| `weeks` | `tuple[PlanWeek, ...]` | longitud = `input.weeks`; la última es `deload` |
| `weekly_volume` | `tuple[GroupVolume, ...]` | un elemento por `VolumeGroup` |
| `warnings` | `tuple[PlanWarning, ...]` | |
| `rationale_es` | `tuple[str, ...]` | frases completas en español |

**Invariantes de `validate_plan`** (violación ⇒ `PlanWarning` en la lista de violaciones y,
en la API, `422 plan_invalid`): ≤ 10 series efectivas por `VolumeGroup` y sesión; `rest_s` ≥
mínimo de la tabla para su rol; cada día ≥ 1 ejercicio; ningún ejercicio `mobility` en
bloques `main`; ningún ejercicio excluido, evitado (músculo objetivo o patrón) ni con
equipamiento no disponible; ningún `deprecated` en planes nuevos.

### 5.4 Progresión (`forja_engine.progression`)
- `PerformedSet`: `weight_kg: float | None`, `reps: int | None`, `rir: int | None`, `duration_s: int | None`, `is_warmup: bool`.
- `ExerciseHistoryEntry`: `session_date: date`, `sets: tuple[PerformedSet, ...]`.
- `WarmupSet`: `percent: float`, `reps: int`, `weight_kg: float`, `plates_per_side_kg: tuple[float, ...]`.
- `ProgressionSuggestion`: `kind: SuggestionKind`, `suggested_weight_kg: float | None`, `suggested_rep_min: int | None`, `suggested_rep_max: int | None`, `suggested_exercise_id: ExerciseId | None`, `plates_per_side_kg: tuple[float, ...]`, `reason_es: str`, `warmup_sets: tuple[WarmupSet, ...]`.

La API compone `LoadSuggestion` = `ProgressionSuggestion` + `program_exercise_id`,
`exercise_id` y `last_performance`.

### 5.5 API pública del motor
```python
generate(input: GeneratorInput, catalog: Sequence[ExerciseCard], tables: Tables | None = None) -> ProgramPlan
regenerate_day(plan: ProgramPlan, catalog: Sequence[ExerciseCard], day_index: int, seed: int | None) -> ProgramPlan
swap_exercise(plan: ProgramPlan, catalog: Sequence[ExerciseCard], address: SlotAddress,
              exclude_ids: Collection[str], replacement_id: str | None, apply_to_all_weeks: bool) -> ProgramPlan
rebalance_after_edit(plan: ProgramPlan, catalog: Sequence[ExerciseCard]) -> ProgramPlan
validate_plan(plan: ProgramPlan, catalog: Sequence[ExerciseCard]) -> tuple[PlanWarning, ...]  # violaciones duras
progression.suggest(prescription: ExercisePrescription, card: ExerciseCard,
                    history: Sequence[ExerciseHistoryEntry], catalog: Sequence[ExerciseCard]) -> ProgressionSuggestion
progression.estimate_1rm(weight_kg: float, reps: int, rir: int = 0) -> float | None   # Epley, reps efectivas ≤ 10
progression.warmup_ramp(work_weight_kg: float, load_type: LoadType, equipment: EquipmentCode) -> tuple[WarmupSet, ...]
```
`Tables` es el modelo validado de todos los YAML de `specs/` (`forja_engine.tables.load_tables(path)`).
Con `tables=None` se usan las tablas cargadas desde la ruta por defecto (el directorio `specs/`
del repositorio, que la imagen del backend copia); el motor no lee variables de entorno. Ninguna función lanza excepciones por falta de candidatos:
degrada y avisa. Entradas inválidas ⇒ `pydantic.ValidationError`.

## 6. DTOs del motor de nutrición (`forja_nutrition.models`)

### 6.1 `NutritionInput`
| Campo | Tipo | Invariantes |
|---|---|---|
| `sex` | `Sex` | |
| `age_years` | `int` | 0–120 (< 18 ⇒ bloqueo) |
| `height_cm` | `float` | 100–250 |
| `weight_kg` | `float` | 20–400 |
| `activity_level` | `ActivityLevel` | |
| `training_days_per_week` | `int` | 0–7 (del programa activo; 0 si no hay) |
| `goal` | `NutritionGoal` | |
| `pace` | `NutritionPace` | |
| `diet_type` | `DietType` | |
| `meals_per_day` | `int` | 3–5 |
| `allergens` | `tuple[Allergen, ...]` | |
| `excluded_food_ids` | `tuple[FoodId, ...]` | |
| `disliked_food_ids` | `tuple[FoodId, ...]` | penalizados, no excluidos |
| `pregnant`, `breastfeeding` | `bool` | ⇒ bloqueo |
| `seed` | `Seed \| None` | `None` ⇒ derivada de la entrada |

El backend calcula `age_years` a partir de `birth_date` y la fecha de la petición (el motor
no lee el reloj) y usa la última `body_metric` como `weight_kg`. Si faltan fecha de
nacimiento, altura o peso ⇒ `NutritionBlock(reason_code=missing_profile_data)`.

### 6.2 Salidas
- `MacroTotals`: `kcal`, `protein_g`, `fat_g`, `carbs_g`, `fiber_g` (`float ≥ 0`).
- `NutritionBlock`: `reason_code: NutritionBlockReason`, `message_es: str` (derivación a profesional, tono neutro).
- `NutritionNotice`: `code: NutritionNoticeCode`, `message_es: str`.
- `NutritionTarget`: `method: BmrMethod`, `age_years: int`, `bmr_kcal`, `activity_factor` (1,0–1,9), `tdee_kcal`, `requested_goal`, `effective_goal`, `pace`, `target_kcal | None`, `protein_g | None`, `fat_g | None`, `carbs_g | None`, `fiber_g | None`, `blocked: bool`, `block: NutritionBlock | None`, `notices: tuple[NutritionNotice, ...]` (siempre incluye `health_disclaimer`). Invariantes: si `blocked`, todas las cifras objetivo son `None`; si no, `target_kcal ≥ max(bmr_kcal, suelo por sexo)` (1.200 / 1.500 / 1.350), `|4P + 4C + 9G − kcal| ≤ 2 %`, déficit ≤ 500 kcal.
- `MealItem`: `food_id`, `name_es`, `grams: float` (múltiplo de 5 salvo unidades), `units: int | None`, `nutrients: MacroTotals`.
- `Meal`: `slot: MealSlot`, `items: tuple[MealItem, ...]` (≥ 1), `totals: MacroTotals`.
- `MacroDeviation`: `kcal`, `protein`, `fat`, `carbs` (`float`, relativo: 0,03 = +3 %).
- `MealPlanDay`: `day_index` (0–6), `date`, `meals` (longitud = `meals_per_day`), `totals`, `deviation`.
- `MealPlan`: `nutrition_version`, `foods_hash: Sha256`, `seed: Seed`, `week_start: date` (lunes), `diet_type`, `meals_per_day`, `target: NutritionTarget`, `days` (7), `notices`. Invariantes: ningún alimento excluido o con alérgeno declarado; todos compatibles con `diet_type`; `|deviation.kcal| ≤ 0,05` y macros ≤ 0,10 o aviso `tolerance_not_met`.
- `ShoppingItem`: `food_id`, `name_es`, `total_grams`, `units | None`; `ShoppingCategory`: `category`, `label_es`, `items`; `ShoppingList`: `week_start`, `categories` (orden de `FoodCategory`).
- `Food` (registro de `foods.json`): `id: FoodId`, `name_es`, `category: FoodCategory`, `fdc_id: int`, `per_100g: MacroTotals`, `diet_types: tuple[DietType, ...]`, `allergens: tuple[Allergen, ...]`, `macro_role: FoodMacroRole`, `typical_portion_g: float`, `unit_grams: float | None`, `unit_name_es: str | None`, `energy_note: str | None` (justificación si `|kcal − (4P+4C+9G)| > 12 %`).

### 6.3 API pública del motor de nutrición
```python
calculate_target(input: NutritionInput) -> NutritionTarget
plan_week(input: NutritionInput, week_start: date) -> MealPlanOutcome   # plan xor block
swap_food(plan: MealPlan, input: NutritionInput, day_index: int, meal: MealSlot,
          food_id: str, replacement_food_id: str | None) -> MealPlan
shopping_list(plan: MealPlan) -> ShoppingList
load_foods() -> tuple[Food, ...]   # lee forja_nutrition/data/foods.json empaquetado
```
`MealPlanOutcome`: `plan: MealPlan | None`, `block: NutritionBlock | None` (exactamente uno
informado). La API responde `422 nutrition_blocked` con `block` si no hay plan.

## 7. Correspondencia API ↔ dominio

| Esquema OpenAPI | Origen |
|---|---|
| `GeneratorInput`, `ProgramPlan`, `PlanWeek`, `PlanDay`, `PlanBlock`, `PlanExercise`, `ExercisePrescription`, `SlotRef`, `SlotAddress`, `GroupVolume`, `GroupSets`, `PlanWarning`, `ExerciseCard` | `forja_engine.models` (idénticos) |
| `ProgramDetail`, `ProgramWeek`, `ProgramDay`, `ProgramBlock`, `ProgramExercise` | Tablas §4.3; `ProgramExercise` = `ExercisePrescription` + `id` + `order` |
| `LoadSuggestion`, `WarmupSet` | `ProgressionSuggestion` + datos de sesión |
| `NutritionInput`, `NutritionTarget`, `NutritionBlock`, `NutritionNotice`, `MealPlan`, `MealPlanDay`, `Meal`, `MealItem`, `MacroTotals`, `MacroDeviation`, `ShoppingList`, `Food` | `forja_nutrition.models` (idénticos; `ShoppingList` de la API añade `plan_id`) |
| `NutritionTargetRecord`, `MealPlanResource` | fila de `nutrition_target` / `meal_plan` + DTO del motor |
| `ExerciseSummary`, `ExerciseDetail`, `ExerciseMedia`, `MediaAttribution` | Tabla `exercise` + URLs de medios (`/media/thumbs/…`, `/media/gifs/…`) + atribución fija |
| `Profile`, `ProfileFields`, `ParqAnswers`, `BodyMetric` | Tablas `user` + `profile` + `body_metric` |
| `WorkoutSession*`, `SetLog*`, `Sync*`, `PersonalRecord` | Tablas §4.3 |
| `AdminSettings`, `AdminUser`, `IngestRun` | `app_setting`, `user`, `ingest_run` |

## 8. Versionado

- Este contrato es la versión **1.0.0** (`info.version` de `openapi.yaml`); el orquestador
  lo congela con la etiqueta `contracts-v1`.
- Cambios compatibles (campo opcional nuevo, valor de enumeración nuevo en una salida,
  endpoint nuevo) ⇒ versión menor. Incompatibles ⇒ versión mayor y ADR.
- Toda propuesta se registra en `docs/CONTRACT_CHANGES.md`; al aprobarla, el arquitecto
  actualiza este documento, `openapi.yaml` y los tests de contrato en el mismo commit.

# Tablero de tareas de Forja

> Mantenido por el arquitecto y el orquestador (ADR 0002). Cada agente actualiza el **estado**
> de sus tareas al entregar; solo arquitecto y orquestador crean o reasignan tareas.
> Estados: `hecha` · `en curso` · `pendiente` · `bloqueada`. Las dependencias se refieren a
> IDs de este tablero. Los criterios de aceptación son verificables con un comando o un
> artefacto concreto. Referencias `§` = `MASTER_PROMPT.md`.

## Resumen de fases y puertas

| Fase | Agentes | Puerta |
|---|---|---|
| 0 · Fundaciones | arquitecto | `make lint typecheck test` verde; OpenAPI válido y con §9 al 100 %; este tablero completo; contratos congelados (`contracts-v1`) |
| 1 · Núcleo | ingesta-datos, motor-rutinas, motor-nutricion, frontend-ui | ver criterios de salida de cada sección |
| 1b · Revisión de dominio | experto-entrenamiento | 0 BLOQUEANTES; CAMBIOS aplicados y re-verificados |
| 2 · Integración | backend-api, frontend-ui | flujo manual registrarse → generar → activar → entrenar → progreso con `docker compose` de desarrollo |
| 3 · Endurecimiento | devops-despliegue, qa-tests, revisor-seguridad | 0 hallazgos altos/críticos; E2E, axe y Lighthouse verdes; bootstrap en LXC limpio reproducible |
| 4 · Cierre | orquestador, qa-tests | §15 completo en `docs/DOD_REPORT.md`; `CHANGELOG.md`, `docs/USER_GUIDE.md`, tag `v1.0.0` |

---

## Fase 0 · Fundaciones — `arquitecto`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F0-ARQ-01 | Esqueleto del monorepo según §4.2 | Existen `backend/app/{api,core,db,models,schemas,services,repositories,security,pdf}`, `backend/{migrations,ingest,tests/{unit,integration,contract}}`, `engine/forja_engine`, `nutrition/forja_nutrition`, `frontend/src/{routes,features,components,lib,i18n,styles,sw}`, `frontend/{tests,e2e}`, `deploy/{nginx,lxc,scripts,backup}`, `contracts/`, `docs/{adr,handoffs}` | — | hecha |
| F0-ARQ-02 | Paquetes Python con uv, ruff, mypy `--strict`, pytest y umbrales (§2.2) | `make lint-python typecheck-python test-engine test-nutrition test-backend` en verde | F0-ARQ-01 | hecha |
| F0-ARQ-03 | Frontend con Vite, TS estricto, ESLint, Vitest (85 %) y Playwright | `make lint-frontend typecheck-frontend test-frontend e2e` en verde | F0-ARQ-01 | hecha |
| F0-ARQ-04 | `contracts/openapi.yaml` (OpenAPI 3.1) con todos los endpoints de §9 | `make lint-contracts` OK; `backend/tests/contract` en verde (cobertura exacta de §9 + ampliaciones de ADR 0009, ejemplos válidos) | — | hecha |
| F0-ARQ-05 | `contracts/domain.md` | Entidades de §5, enumeraciones y DTOs `GeneratorInput`, `ExerciseCard`, `ProgramPlan`, `NutritionInput`, `MealPlan` con campos, tipos e invariantes | F0-ARQ-04 | hecha |
| F0-ARQ-06 | ADRs 0001–0010 | `docs/adr/` con formato Contexto · Decisión · Alternativas · Consecuencias | — | hecha |
| F0-ARQ-07 | CI `.github/workflows/ci.yml` con los trabajos de §13 | `actionlint` sin errores; cada trabajo ejecuta comprobaciones reales | F0-ARQ-02, F0-ARQ-03 | hecha |
| F0-ARQ-08 | `.env.example` completo, `README.md`, este tablero y `docs/CONTRACT_CHANGES.md` | `backend/tests/unit/test_env_example.py` en verde | F0-ARQ-02 | hecha |
| F0-ORQ-01 | Revisar y congelar contratos | Tag `contracts-v1` sobre el merge de `f0/arquitecto` | F0-ARQ-04, F0-ARQ-05 | hecha |

### Tareas recurrentes del arquitecto

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| ARQ-R1 | Resolver propuestas de `docs/CONTRACT_CHANGES.md` | Cada propuesta con resolución (aprobada/rechazada + motivo) en ≤ 1 ciclo de orquestación; si se aprueba, `openapi.yaml`, `domain.md` y test de contrato actualizados en el mismo commit y `info.version` incrementada | — | en curso |
| ARQ-R2 | Mantener la matriz de propiedad (ADR 0002) y los objetivos de calidad del Makefile/CI | Ningún handoff reporta conflicto de zona sin resolver | — | en curso |

---

## Fase 1 · Núcleo

### `ingesta-datos` (§2.1, §3, §5.1, §6) — handoff `docs/handoffs/f1-ingesta-datos.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F1-ING-01 | CLI `forja-ingest` (Typer) con `fetch`, `enrich`, `load`, `report`, `verify`, `export-cards`, todos con `--dry-run` | `uv run forja-ingest --help` lista los 6 subcomandos; entrada `[project.scripts]` añadida a `backend/pyproject.toml` (zona compartida, ADR 0002) | F0-ORQ-01 | hecha |
| F1-ING-02 | `fetch`: clon superficial en `DATASET_COMMIT`, validación `jsonschema` contra `data/exercises.schema.json` | Test con repo git local de fixture: commit exacto, esquema válido; esquema inválido ⇒ error | F1-ING-01 | hecha |
| F1-ING-03 | Copia byte a byte de medios, `manifest.json` (id, ruta, bytes, SHA-256, ancho, alto), verificación 180×180, copia de `LICENSE`/`NOTICE.md` a `$MEDIA_ROOT/LICENSES/`, idempotencia | Test: SHA-256 de origen = destino; segunda ejecución sin cambios no escribe; imagen ≠ 180×180 ⇒ error | F1-ING-02 | hecha |
| F1-ING-04 | Normalización de músculos y equipamiento con `specs/*-normalization.yaml` | Test: valor sin mapear ⇒ fallo; 100 % de los valores de `docs/dataset-analysis.md` mapeados | F1-ING-01 | hecha |
| F1-ING-05 | `display_name_en`, sufijos `(male)`/`(female)`, `v. N`, `(back pov)`/`(side pov)`, duplicados y mojibake → `variant_group`, `variant_kind`, `variant_label_es`, `demo_sex` | Tests sobre la fixture de 60 ejercicios; ningún `display_name_en` contiene `в`; 33 con `demo_sex`, 40 `v. N`, 6 duplicados agrupados | F1-ING-04 | hecha |
| F1-ING-06 | Motor de reglas `enrich.py` + overrides (patrón, mecánica, rol, dificultad, lateralidad, `load_type`) | Informe con 0 `other` sin justificar (lista explícita de excepciones) | F1-ING-05 | hecha |
| F1-ING-07 | Ampliar `specs/overrides/staples.yaml` a 120–160 | Test: ≥ 2 staples por patrón principal × grupo de equipamiento aplicable (gym/home_basic/bodyweight) | F1-ING-06 | hecha |
| F1-ING-08 | `docs/enrichment-report.md` (distribuciones, matriz de staples, excepciones) | Generado por `forja-ingest report`; reproducible | F1-ING-07 | hecha |
| F1-ING-09 | `specs/overrides/names_es.json` (1.324 nombres, 14 lotes de ≤ 100) con glosario | Test: cobertura 100 %, sin duplicados no intencionados, términos del glosario consistentes; dudosos en `docs/names-es-review.md` | F1-ING-05 | hecha |
| F1-ING-10 | Alternativas top 8 (§6.5) | Tests: pesos 0,5/0,3/0,1/0,1; excluye propio `variant_group`; estiramientos solo con estiramientos | F1-ING-06 | hecha |
| F1-ING-11 | Modelos de catálogo (si backend-api no los tiene) y `load` transaccional con `ingest_run`, `search_vector`, `deprecated_at` | Test de integración (testcontainers): 1.324 filas, recarga idempotente, ejercicio referenciado nunca se borra | F1-ING-10, F1-ING-09 | hecha |
| F1-ING-12 | `export-cards` → JSON de `ExerciseCard[]` validado con `contracts/openapi.yaml#ExerciseCard` | Fichero válido; entregado a motor-rutinas para `engine/tests/fixtures/catalog.json` | F1-ING-11 | hecha |
| F1-ING-13 | Test `slow` con el dataset completo que verifica las cifras de `docs/dataset-analysis.md` | `pytest -m slow` en verde: 1.324 registros, 2.648 medios verificados | F1-ING-03, F1-ING-11 | hecha |
| F1-ING-14 | Cobertura ≥ 95 % del paquete `ingest` y handoff | `pytest --cov=ingest` ≥ 95 %; `docs/handoffs/F1-ingesta.md` | F1-ING-01…13 | hecha |

**Salida**: `forja-ingest fetch && forja-ingest load` en BD limpia ⇒ 1.324 ejercicios, 2.648 medios verificados, 0 errores.

### `motor-rutinas` (§7) — handoff `docs/handoffs/f1-motor-rutinas.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F1-ENG-01 | `tables.py`: carga y validación Pydantic de todos los YAML, `tables_hash` | YAML inválido o referencia rota (patrón/plantilla inexistente) ⇒ error al cargar; hash estable | F0-ORQ-01 | hecha |
| F1-ENG-02 | `models.py`: DTOs `frozen` de `contracts/domain.md` §5 | Test: `model_json_schema()` compatible con los esquemas de `contracts/openapi.yaml` | F0-ORQ-01 | hecha |
| F1-ENG-03 | Catálogo de fixture ≥ 150 `ExerciseCard` realistas (todos los patrones y equipamientos) | `engine/tests/fixtures/catalog.json` valida contra `ExerciseCard` | F1-ENG-02 | hecha |
| F1-ENG-04 | Paso 1 `normalize.py` (seguridad, semilla derivada) | Tests parametrizados; misma entrada ⇒ misma semilla | F1-ENG-02 | hecha |
| F1-ENG-05 | Paso 2 `split.py` + sustituciones por énfasis | Tabla §7.3 verificada para 7 días × 3 niveles | F1-ENG-01 | hecha |
| F1-ENG-06 | Paso 3 `volume.py` (objetivo, énfasis, sexo, suelos) | Tests por objetivo × nivel × énfasis | F1-ENG-01 | hecha |
| F1-ENG-07 | Paso 4 `allocate.py` (≤ 10 series/grupo/sesión, créditos 1,0/0,5) | Propiedad: nunca > 10 | F1-ENG-05, F1-ENG-06 | hecha |
| F1-ENG-08 | Paso 5 `select.py` (puntuación, PRNG, relajación, alternativas) | Tests de cada término de puntuación y de la cadena de relajación; nunca excepción | F1-ENG-03, F1-ENG-07 | hecha |
| F1-ENG-09 | Paso 6 `prescribe.py` (§7.5, principiantes, modificadores de sexo) | Tabla §7.5 reproducida en tests | F1-ENG-08 | hecha |
| F1-ENG-10 | Paso 7 `timefit.py` (a–d, nunca tocar `main` salvo último recurso) | Propiedad: tiempo ≤ presupuesto × 1,05 o warning | F1-ENG-09 | hecha |
| F1-ENG-11 | Paso 8 `periodize.py` (acumulación, descarga, ondulación) | Tests por nivel y objetivo | F1-ENG-09 | hecha |
| F1-ENG-12 | Paso 9 `compose.py` + `generate()` con `rationale_es` y `warnings` | Salida valida contra `ProgramPlan`; determinismo byte a byte | F1-ENG-04…11 | hecha |
| F1-ENG-13 | `progression.py` (§7.6: doble progresión, e1RM, aproximación, discos) | Tests con casos límite (reps > 10, peso corporal, mancuernas) | F1-ENG-02 | hecha |
| F1-ENG-14 | `ops.py`: `regenerate_day`, `swap_exercise`, `rebalance_after_edit`, `validate_plan` | Tests por operación; `validate_plan` detecta cada regla de §7.7 | F1-ENG-12 | hecha |
| F1-ENG-15 | 1.890 combinaciones parametrizadas | `pytest` las ejecuta en < 60 s | F1-ENG-12 | hecha |
| F1-ENG-16 | Propiedades hypothesis de §7.8 | Determinismo, `validate_plan`, tiempo, exclusiones, equipamiento, volumen ±15 % | F1-ENG-14 | hecha |
| F1-ENG-17 | 12 snapshots golden + `engine/tests/golden/README.md` | Perfiles descritos; revisión del experto (F1b-EXP-05) | F1-ENG-12 | hecha |
| F1-ENG-18 | Benchmark `generate` < 150 ms p95 con catálogo completo | `pytest-benchmark` | F1-ENG-12, F1-ING-12 | hecha |
| F1-ENG-19 | Regenerar fixture con `forja-ingest export-cards` y actualizar snapshots | Tests verdes con el catálogo real exportado | F1-ING-12, F1-ENG-17 | hecha |
| F1-ENG-20 | Cobertura 100 % líneas / ≥ 95 % ramas y handoff con 3 perfiles legibles | `make test-engine` verde; handoff | todas las anteriores | hecha |

### `motor-nutricion` (§8) — handoff `docs/handoffs/F1-motor-nutricion.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F1-NUT-01 | `models.py` + carga validada de `specs/nutrition.yaml` | DTOs de `contracts/domain.md` §6; YAML inválido ⇒ error | F0-ORQ-01 | hecha |
| F1-NUT-02 | `energy.py`: TMB Mifflin (male/female/average), GET con ajuste por días, objetivo | Tests con valores calculados a mano | F1-NUT-01 | hecha |
| F1-NUT-03 | `macros.py`: proteína, grasa (suelos), carbohidratos, fibra | Propiedad: macros suman kcal ±2 % | F1-NUT-02 | hecha |
| F1-NUT-04 | `safety.py`: bloqueos y suelos de §8.5 como resultado tipado | Propiedad: suelos siempre respetados; < 18, embarazo, lactancia ⇒ `NutritionBlock` | F1-NUT-02 | hecha |
| F1-NUT-05 | `data/foods.json` (~200 alimentos USDA FDC con `fdc_id`, ES, categoría, dietas, alérgenos, porción) | Test: `|kcal − (4P+4C+9G)| ≤ 12 %` o `energy_note`; fecha de consulta documentada | F1-NUT-01 | hecha |
| F1-NUT-06 | `planner.py`: plantillas, selección sembrada, `lsq_linear`, redondeo, re-verificación | Tolerancias ±5 % kcal / ±10 % macros o aviso; reproducible con semilla | F1-NUT-03, F1-NUT-05 | hecha |
| F1-NUT-07 | `shopping.py` | Agregado por categoría en orden de `FoodCategory` | F1-NUT-06 | hecha |
| F1-NUT-08 | `swap.py` | Misma categoría y macros de la comida conservados (±10 %) | F1-NUT-06 | hecha |
| F1-NUT-09 | Propiedades §8.6 y 6 snapshots (incl. vegano con alergia a frutos secos y usuaria en `lose` cerca del suelo) | `make test-nutrition` verde (100 %/95 %) | F1-NUT-04…08 | hecha |
| F1-NUT-10 | Handoff con 2 planes de ejemplo legibles | `docs/handoffs/F1-motor-nutricion.md` | F1-NUT-09 | hecha |

### `frontend-ui` · Fase 1 (§10) — handoff `docs/handoffs/F1-frontend.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F1-FE-01 | Dependencias de §4.1 y `npm run gen:api` (`openapi-typescript` → `src/lib/api/schema.d.ts`) + cliente `openapi-fetch` con middleware CSRF (ADR 0003) | Tipos generados sin `any`; test del middleware (cabecera en métodos no seguros) | F0-ORQ-01 | hecha |
| F1-FE-02 | Mocks MSW generados de los ejemplos de `contracts/openapi.yaml` | Handlers para todas las operaciones; tests de componentes los usan | F1-FE-01 | hecha |
| F1-FE-03 | Tokens de diseño «Forja» (§10.1) y tipografía autoalojada (ADR 0007) | Contraste AA verificado en test; fuentes servidas desde `/assets` | F0-ORQ-01 | hecha |
| F1-FE-04 | Componentes base sobre Radix (Button, Sheet, Dialog, Tabs, Select, Slider, Toast, NumberPad) | Tests con Testing Library + axe sin violaciones | F1-FE-03 | hecha (f2/frontend-a) |
| F1-FE-05 | `ExerciseMedia` único + regla ESLint que prohíbe `<img>` de medios fuera de él | Test que falla sin atribución «© Gym visual — https://gymvisual.com/»; máx. 180 px; `prefers-reduced-motion` | F1-FE-03 | hecha |
| F1-FE-06 | Shell: TanStack Router, navegación inferior (móvil) y lateral (escritorio) | Navegación entre las 5 secciones con MSW | F1-FE-04 | hecha |
| F1-FE-07 | i18n `es` (defecto) y `en` con `Intl` | Sin cadenas sin traducir (test) | F1-FE-06 | hecha |
| F1-FE-08 | Handoff con capturas móvil/escritorio, claro/oscuro | `docs/handoffs/F1-frontend.md`; `make test-frontend` ≥ 85 % | F1-FE-01…07 | hecha (handoff en `docs/handoffs/f1-frontend-ui.md`; capturas se entregan con F2 junto al resto de pantallas, ver handoff) |

---

## Fase 1b · Revisión de dominio — `experto-entrenamiento`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F1b-EXP-01 | Revisión del enriquecimiento (100 aleatorios + staples) | `docs/reviews/enrichment-review.md` con veredicto por ítem | F1-ING-08 | hecha |
| F1b-EXP-02 | Revisión de staples por nivel y equipamiento | `docs/reviews/staples-review.md` | F1-ING-07 | hecha |
| F1b-EXP-03 | Revisión de nombres ES (dudosos + 150 muestreados) | `docs/reviews/names-es-review.md` | F1-ING-09 | hecha |
| F1b-EXP-04 | Revisión de tablas `specs/*.yaml` | `docs/reviews/tables-review.md` con diffs propuestos | — | hecha |
| F1b-EXP-05 | Revisión de los 12 snapshots | `docs/reviews/snapshots-review.md` | F1-ENG-17 | hecha |
| F1b-EXP-06 | Revisión de planes de comida y suelos | `docs/reviews/nutrition-review.md` | F1-NUT-10 | hecha |
| F1b-FIX | Aplicar CAMBIOS por los propietarios y re-verificar | 0 BLOQUEANTES; re-revisión aprobada | F1b-EXP-01…06 | hecha |

---

## Fase 2 · Integración

### `backend-api` (§5, §9, §11) — handoff `docs/handoffs/f2-backend-api.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F2-BE-01 | App factory, errores RFC 9457 centralizados, `X-Request-ID`, logs JSON sin PII | Tests de formato de error para 401/403/404/409/413/422/429 | F0-ORQ-01 | hecha |
| F2-BE-02 | Modelos SQLAlchemy de `contracts/domain.md` §4 y migración inicial Alembic con `unaccent`/`pg_trgm` e índices | Test de migraciones upgrade → downgrade → upgrade en testcontainers | F2-BE-01, F1-ING-11 | hecha |
| F2-BE-03 | Auth (ADR 0003): registro, login, logout, me, password, check, csrf, sesiones activas | Tests: rotación, expiración deslizante, revocación, tiempo constante, CSRF en toda escritura | F2-BE-02 | hecha |
| F2-BE-04 | Rate limiting y cabeceras de seguridad (CSP, HSTS…) | Tests de 429 con `Retry-After` y de cabeceras | F2-BE-03 | hecha |
| F2-BE-05 | Perfil, PAR-Q (fuerza `beginner`) y métricas corporales | Tests felices, validación, acceso cruzado ⇒ 404 | F2-BE-03 | hecha |
| F2-BE-06 | Catálogo: listado con filtros y búsqueda sin acentos, detalle con `lang`, alternativas, facetas, favoritos, `ETag`/304 | `GET /exercises` p95 < 80 ms con 1.324 filas (`pytest-benchmark`) | F2-BE-02, F1-ING-11 | hecha |
| F2-BE-07 | Caché en memoria de `ExerciseCard[]` por proceso, invalidada tras ingesta | Test de invalidación | F2-BE-06 | hecha |
| F2-BE-08 | Generador (`preview`, `preview/regenerate-day`, `preview/swap`) y persistencia de programas | `POST /generator/preview` p95 < 400 ms; plan persistido = plan previsualizado | F2-BE-07, F1-ENG-20 | hecha |
| F2-BE-09 | Programas: listar, detalle, patch, delete, activar (máx. 1), duplicar, regenerar día, swap, `PUT days/{day_id}` con `validate_plan` | `422 plan_invalid` con `violations`; tests por operación | F2-BE-08 | hecha |
| F2-BE-10 | PDF (WeasyPrint, atribución en cada página, `url_fetcher` local) e ICS (RFC 5545) | Test: texto de atribución presente en cada página del PDF; ICS válido | F2-BE-09 | hecha |
| F2-BE-11 | Sesiones y series con `Idempotency-Key` (tabla `idempotency_key`) | Tests de repetición, clave reutilizada (422) y concurrente (409) | F2-BE-09 | hecha |
| F2-BE-12 | `POST /sync` (ADR 0006) | Tests: `applied`/`duplicate`/`superseded`/`rejected`, tombstones, lote parcial | F2-BE-11 | hecha |
| F2-BE-13 | Récords, estadísticas y `GET /sessions/next` con progresión del motor | Sin N+1 (conteo de consultas en test) | F2-BE-11, F1-ENG-13 | hecha |
| F2-BE-14 | Nutrición tras `diet_enabled` y `DIET_FEATURE_ENABLED` | `403 diet_disabled`; `422 nutrition_blocked` | F2-BE-05, F1-NUT-10 | hecha |
| F2-BE-15 | Exportar/importar/borrar cuenta | Round-trip export → import idempotente; borrado completo verificado | F2-BE-13, F2-BE-14 | hecha |
| F2-BE-16 | Admin (ajustes, usuarios, ingesta en segundo plano) + `audit_log`; `GET /about`, `/health`, `/ready` | No se puede degradar al último admin (409) | F2-BE-03, F1-ING-11 | hecha |
| F2-BE-17 | Test de contrato: esquema exportado por FastAPI = `contracts/openapi.yaml` | `backend/tests/contract` compara ambos y falla ante cualquier diferencia | F2-BE-01…16 | hecha |
| F2-BE-18 | Autorización cruzada en todas las rutas de usuario | Test que recorre todas las operaciones con ids de otro usuario ⇒ 404 | F2-BE-17 | hecha |
| F2-BE-19 | `make seed-demo` (solo desarrollo) y colección `httpie`/`curl` | Documentado en el handoff | F2-BE-17 | hecha |
| F2-BE-20 | Cobertura ≥ 90 % líneas y ramas y handoff | `make test-backend` verde | todas | hecha |

### `frontend-ui` · Fase 2 (§10.2) — handoff `docs/handoffs/F2-frontend.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F2-FE-01 | Onboarding 4 pasos con PAR-Q y aviso sanitario | Tests del flujo con PAR-Q marcado y sin marcar | F1-FE-08 | hecha (f2/frontend-a) |
| F2-FE-02 | Hoy (sesión del día, resumen semanal, récord, peso rápido) | Estados `scheduled`/`rest_day`/`no_active_program` | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-03 | Generador (wizard) con vista previa, `rationale_es`, gráfico de volumen, regenerar/cambiar/guardar | Tests del wizard; preselección por sexo explicada | F1-FE-08 | hecha (f2/frontend-a) |
| F2-FE-04 | Editor (dnd-kit accesible, superseries, validación en vivo, deshacer/rehacer) | Tests de teclado y de deshacer | F2-FE-03 | hecha (f2/frontend-a) |
| F2-FE-05 | Reproductor: máquina de estados, temporizador por marcas de tiempo, Wake Lock, vibración, notificación, IndexedDB | Tests: reanudar tras recarga, reloj simulado | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-06 | Cola offline + `/sync` (ADR 0006) | Test offline → online con reintentos | F2-FE-05 | hecho (f2/frontend-b) |
| F2-FE-07 | Resumen de sesión | Récords y esfuerzo percibido | F2-FE-05 | hecho (f2/frontend-b) |
| F2-FE-08 | Biblioteca virtualizada con búsqueda sin acentos y mapa muscular SVG | 1.324 elementos fluidos | F1-FE-08 | hecha (f2/frontend-a) |
| F2-FE-09 | Detalle (10 idiomas, ángulo de cámara, alternativas, historial) | Test de conmutadores | F2-FE-08 | hecha (f2/frontend-a) |
| F2-FE-10 | Progreso (calendario, volumen, e1RM, récords, peso con media de 7 días) | Recharts en chunk diferido | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-11 | Nutrición (anillos neutros, plan, intercambio, lista de la compra, avisos) | Sin colores punitivos (revisión) | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-12 | Perfil, ajustes, sesiones activas, exportar/importar/borrar, Créditos (`GET /about`) | Créditos con MIT, aviso de Gym visual y SHA | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-13 | Admin | Usuarios, registro, dieta global, ingesta | F1-FE-08 | hecho (f2/frontend-b) |
| F2-FE-14 | PWA: manifest, Workbox según §10.3, descarga de biblioteca | SW controla la página; arranque offline | F2-FE-05 | hecho (f2/frontend-b) |
| F2-FE-15 | Presupuesto de rendimiento (JS inicial < 200 KB gzip) | Informe del build en el handoff | F2-FE-01…14 | hecha |
| F2-FE-16 | Cambio de MSW a API real | Flujo de la puerta 2 contra `docker compose` de desarrollo | F2-BE-17 | hecho (f2/frontend-integration) |
| F2-FE-17 | Cobertura ≥ 85 % y capturas de todas las pantallas | `make test-frontend` verde; handoff | todas | hecha |

---

## Fase 3 · Endurecimiento

### `devops-despliegue` (§12) — handoff `docs/handoffs/f3-devops.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F3-OPS-01 | `deploy/docker/api.Dockerfile` multi-stage (uv → `python:3.12-slim`, no root, HEALTHCHECK, incluye `specs/`) | Imagen sin compiladores; `/api/v1/ready` responde 200 | F2-BE-20 | hecha |
| F3-OPS-02 | Imagen `web` (`nginx-unprivileged:1.27-alpine`, no root) con `frontend/dist` | Sirve la SPA con fallback | F2-FE-17 | hecha |
| F3-OPS-03 | `deploy/docker-compose.yml` (§12.1) | `docker compose config` válido; `read_only`, límites, healthchecks, perfil `tools` | F3-OPS-01, F3-OPS-02 | hecha |
| F3-OPS-04 | `deploy/nginx/forja.conf.template` con `auth_request` condicionado, CSP, caché, `limit_req` | `/media` 401 sin sesión y 200 con sesión | F3-OPS-03 | hecha |
| F3-OPS-05 | Objetivos de operación del `Makefile` (`bootstrap`, `up`, `down`, `logs`, `migrate`, `ingest`, `backup`, `restore`, `create-admin`) | `make bootstrap && make up` en LXC limpio | F3-OPS-03 | hecha |
| F3-OPS-06 | `deploy/lxc/README.md` + bloques de nginx externo (TLS fuera y dentro) | Reproducible por un tercero | F3-OPS-05 | hecha |
| F3-OPS-07 | `deploy/backup/` con rotación 7+4 y `restore.sh` probado en CI | Trabajo de CI de restauración verde | F3-OPS-03 | hecha |
| F3-OPS-08 | CI: build de imágenes y Trivy (falla en HIGH/CRITICAL corregibles) | Trabajos añadidos a `ci.yml` | F3-OPS-01, F3-OPS-02 | hecha |

### `qa-tests` (§13) — handoff `docs/handoffs/F3-qa.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F3-QA-01 | E2E Playwright de todos los flujos de su definición contra `docker compose` | Chromium escritorio + WebKit iPhone verdes | F3-OPS-03, F2-FE-16 | hecha |
| F3-QA-02 | `@axe-core/playwright` en todas las pantallas | 0 violaciones serias/críticas | F3-QA-01 | hecha |
| F3-QA-03 | Lighthouse CI con umbrales §10.5 sobre el despliegue y comprobaciones PWA en Playwright (ADR 0010) | Rendimiento/Accesibilidad/Buenas prácticas ≥ 90; manifest, SW y arranque offline verificados | F3-QA-01 | hecha |
| F3-QA-04 | Test de licencia en el DOM (atribución y ≤ 180 px en toda vista con medios) | Falla si falta en cualquier pantalla | F3-QA-01 | hecha |
| F3-QA-05 | Ampliar la comprobación de marcadores prohibidos a tests y documentación de usuario si procede | `make lint-placeholders` cubre `backend/tests`, `engine/tests`, `nutrition/tests`, `frontend/e2e`, `frontend/tests`, `README.md` y (vía `wildcard`, en cuanto existan) `CHANGELOG.md`/`docs/USER_GUIDE.md`; ejecutado en verde el 2026-09-28, sin coincidencias reales ni excepciones necesarias (ver comentario junto a `PLACEHOLDER_PATHS` en el `Makefile`) | F0-ARQ-07 | hecha |
| F3-QA-06 | E2E contra compose en CI (`E2E_BASE_URL`) | Trabajo `e2e` usa el despliegue | F3-QA-01, F3-OPS-08 | hecha |

### `revisor-seguridad` (§11) — `docs/SECURITY_REVIEW.md`

| ID | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|
| F3-SEC-01 | Auditoría completa (auth, CSRF, autorización cruzada, entrada, WeasyPrint, nginx, Docker, privacidad, licencia, dependencias) | Informe con severidad, reproducción y propietario por hallazgo | F2-BE-20, F2-FE-17, F3-OPS-04 | hecha |
| F3-SEC-02 | Re-revisión tras correcciones | 0 altos/críticos | F3-SEC-01 | hecha |

---

## Fase 4 · Cierre

| ID | Agente | Tarea | Criterio de aceptación | Depende de | Estado |
|---|---|---|---|---|---|
| F4-FE-01 | frontend-ui | Pulido visual: CTA primaria con degradado brasa en cada pantalla, iconos en `AppNav` y cabeceras de tarjeta, más respiro y estados vacíos intencionados | `docs/handoffs/f4-visual-polish.md`; lint/tsc/build en verde; tests 196/196 (cobertura de ramas global sigue por debajo del umbral, preexistente — ver handoff) | Fase 2 | hecha (rama `f4/visual-polish`, sin fusionar) |
| F4-QA-01 | qa-tests | Auditoría de §15 punto por punto | `docs/DOD_REPORT.md` con evidencia; lo que falle, tarea nueva aquí | Fase 3 | pendiente |
| F4-ORQ-01 | orquestador | `CHANGELOG.md` y `docs/USER_GUIDE.md` (ES, con capturas) | Revisados | F4-QA-01 | pendiente |
| F4-ORQ-02 | orquestador | README definitivo y tag `v1.0.0` | Tag creado sobre `main` verde | F4-ORQ-01 | pendiente |

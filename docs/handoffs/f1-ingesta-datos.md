# Handoff · Fase 1 · ingesta-datos

Rama: `f1/ingesta-datos` (sin fusionar). Fechas: 2026-09-23 → 2026-09-25.

## Resumen

MASTER_PROMPT §6 completo en `backend/ingest/` como CLI `forja-ingest` (Typer) con seis
subcomandos idempotentes y `--dry-run`:

| Comando | Qué hace |
|---|---|
| `fetch` | `git fetch --depth 1` del SHA exacto (`DATASET_COMMIT`), valida `data/exercises.json` con su JSON Schema 2020-12, copia **byte a byte** 1.324 JPG + 1.324 GIF a `$MEDIA_ROOT/{thumbs,gifs}`, comprueba 180×180 con Pillow en solo lectura, escribe `manifest.json` (id, tipo, ruta, bytes, SHA-256, ancho, alto; sin marcas de tiempo), copia `LICENSE` y `NOTICE.md` a `$MEDIA_ROOT/LICENSES/` y los datos a `$MEDIA_ROOT/source/`. Si el commit y los checksums coinciden no clona ni escribe nada; `--dry-run` muestra altas/bajas/cambios. |
| `enrich` | Normaliza + enriquece y falla si hay `other` sin justificar o celdas de staples incompletas. |
| `report` | Genera `docs/enrichment-report.md` (reproducible, sin marcas de tiempo). |
| `verify` | Re-verifica SHA-256 y 180×180 de todos los medios y los requisitos del catálogo. |
| `load` | Upsert transaccional en PostgreSQL, `ingest_run` (también fallidas y dry-run), `search_vector` (`unaccent`, pesos A/B), alternativas; nunca borra: marca `deprecated_at` y reactiva si vuelve. `--create-schema` crea extensiones y tablas si faltan (hasta que exista la migración Alembic). |
| `export-cards` | Vuelca `ExerciseCard[]` (orden por id) para `engine/tests/fixtures/catalog.json`. |

Resultados sobre el dataset real @ `7455efae…`: 1.324 ejercicios, **2.648/2.648 medios
verificados**, vocabulario 100 % mapeado, **1.324/1.324 nombres ES** con 0 incidencias de
glosario, 8 `other` (todos justificados), 144 staples (73 `main`) y ≥ 2 staples en las 21
celdas patrón principal × {gym, home_basic, bodyweight}.

## Ficheros tocados

| Zona | Ficheros |
|---|---|
| `backend/ingest/` (propia) | `domain.py`, `specs.py`, `source.py`, `normalize.py`, `enrich.py`, `names.py`, `alternatives.py`, `catalog.py`, `media.py`, `report.py`, `load.py`, `cli.py`; `tests/` (conftest + 9 módulos); `tests/fixtures/{exercises.json (60 registros reales), dataset-index.json (1.324 sin instrucciones), exercises.schema.json, LICENSE}` |
| `specs/overrides/` (propia) | `enrichment-overrides.yaml` (v2: 30 reglas prioritarias, palabras clave, `other_justified`, 34 overrides por id), `staples.yaml` (v2, 144 ids), `name-fixes.yaml`, `names_es.json` (nuevo), `names-es-exceptions.yaml` (nuevo) |
| `docs/` (propia) | `enrichment-report.md`, `names-es-review.md`, este handoff |
| Zona compartida (ADR 0002) | `backend/app/models/catalog.py` (nuevo: `Base`, `Muscle`, `Equipment`, `Exercise`, `ExerciseSecondaryMuscle`, `ExerciseInstruction`, `ExerciseAlternative`, `IngestRun`) → pasa a `backend-api`; `backend/pyproject.toml` (`[project.scripts] forja-ingest`; sin dependencias nuevas, `uv lock --check` OK) |
| Coordinación | `docs/TASKS.md` (F1-ING-01…14 → `hecha`), `docs/CONTRACT_CHANGES.md` (CC-0001) |

No se tocó `contracts/`, `specs/*.yaml` de la raíz ni ningún medio (no se versiona ninguno).

## Decisiones (y ADRs)

Sin ADR nuevo; decisiones de detalle:

1. **`specs/enrichment-rules.yaml` no se modifica** (ADR 0002 asigna `specs/*.yaml` a
   `motor-rutinas`). Las mejoras van en `specs/overrides/enrichment-overrides.yaml` v2, que
   añade `pattern_rules` evaluadas antes que las base, `keywords` (dificultad, lateralidad,
   tipo de carga, aislamiento, `warmup_name_any`) y `other_justified`. Ver petición al
   orquestador.
2. **Coincidencia de palabras clave** sobre el nombre visible (erratas corregidas, sin
   sufijos) rodeado de espacios: un espacio en la clave es límite de palabra (evita
   «throw down» ⇒ remo, «outstretched» ⇒ estiramiento, «hanging» ⇒ por tiempo).
3. **Variantes** agrupadas por slug del nombre base (une «close-grip»/«close grip»);
   duplicados ⇒ `duplicate` «(variante B)»; `v. N` ⇒ «variante N»; cámara ⇒ «vista
   trasera/lateral»; `(male)/(female)` ⇒ `demonstrator` «demostración masculina/femenina».
   `display_name_en` y `name_es` no llevan sufijos. `slug` = `slug(nombre)-id` (único).
4. **1759 «single leg squat (pistol) male»**: el dataset omite los paréntesis; se corrige en
   `name-fixes.yaml` ⇒ `demo_sex = male`. Por eso hay **34** ejercicios con `demo_sex`
   (33 sufijos del análisis + este).
5. **Staples**: la semilla tenía dos errores de datos (0860 es patada de tríceps, 0003 es un
   crunch bicicleta) y se sustituyeron. `vertical_push × bodyweight` solo tiene 2 candidatos
   en el dataset (0471 flexión en pino, 3302 pino), ambos dificultad 3.
6. **Rol `warmup`** mediante `keywords.warmup_name_any` (movilidad dinámica y cardio ligero,
   §6.3) y 7 overrides por id (manguito rotador, rotadores de cadera, tabla de equilibrio).
7. **Mecánica**: literal de §6.3 (compuesto solo en patrones multiarticulares): press cerrado,
   fondos y flexiones de tríceps quedan como `elbow_extension`/`isolation`.
8. **Alternativas**: solo candidatos que comparten patrón o músculo objetivo (score > 0,3);
   `numeric(4,3)`; estiramientos (`role = mobility`) solo con estiramientos; desempate por id.
9. **Datos en el volumen**: `fetch` guarda `exercises.json` y su esquema en
   `$MEDIA_ROOT/source/` para que `load`/`verify` funcionen sin red.
10. **`load`**: una transacción de catálogo; `ingest_run` se crea antes (`running`) y se
    cierra `succeeded`/`failed` (error resumido). Inserciones en lotes de 500 filas (límite
    de parámetros de asyncpg). UUID v7 propio (RFC 9562).
11. **`exercise_secondary_muscle.position`**: columna añadida para conservar el orden estable
    que exige `ExerciseCard` ⇒ propuesta **CC-0001** en `docs/CONTRACT_CHANGES.md`.

## Cómo verificar (comandos exactos)

```bash
cd <worktree> && export PATH=$HOME/.local/bin:$HOME/.local/npm10/bin:$PATH
make install
make lint typecheck test                      # exit 0 (Docker para testcontainers)
cd backend
uv run --locked pytest ingest/tests -m "not slow" --cov=ingest --cov-branch
uv run --locked pytest -m slow --cov-fail-under=0   # red: descarga el dataset (~140 MB)
# Flujo real
export MEDIA_ROOT=/tmp/forja-media DATABASE_URL=postgresql+asyncpg://u:p@host/db
uv run forja-ingest fetch && uv run forja-ingest fetch     # updated / unchanged
uv run forja-ingest verify                                 # 2648/2648 medios verificados
uv run forja-ingest load --create-schema && uv run forja-ingest load --dry-run
uv run forja-ingest report --dry-run                       # «ya está al día»
uv run forja-ingest export-cards --output ../engine/tests/fixtures/catalog.json
```

## Métricas

| Comando | Resultado |
|---|---|
| `make lint typecheck test` | exit 0 (ruff, ESLint, OpenAPI, marcadores, mypy --strict, tsc, todos los tests) |
| Backend (`-m "not slow"`) | 521 passed; líneas 99,59 %, ramas 98,34 % (gate 90/90 OK) |
| Paquete `ingest` | 127 tests rápidos (+4 `slow`); **líneas 99,55 %, ramas 98,32 %** (≥ 95 %) |
| `pytest -m slow` (GitHub real) | 4 passed en 45 s: cifras de `dataset-analysis.md`, 2.648 medios, fixtures = dataset real, carga completa en PostgreSQL |
| `forja-ingest load` (1.324) | ~5 s; recarga idempotente `=1324`; 10.557 alternativas |
| Enriquecimiento | 8 `other` justificados; 144 staples; 21/21 celdas ≥ 2 |

## Riesgos/pendientes

1. **Revisión de dominio** (F1b): patrones, staples y nombres ES dudosos
   (`docs/names-es-review.md`, 31 casos) pendientes de `experto-entrenamiento`.
2. **CC-0001** (`position`) pendiente del arquitecto; si se rechaza hay que quitar la
   columna del modelo y del loader.
3. **Migración Alembic** del catálogo aún no existe: `load --create-schema` crea las tablas
   con `metadata.create_all`. `backend-api` debe escribir la migración equivalente (F2-BE-02).
4. `$MEDIA_ROOT/source/` contiene `exercises.json` (MIT): nginx debe servir solo
   `thumbs/`, `gifs/` (y `LICENSES/` si procede).
5. El test `slow` necesita red (o `DATASET_REPO=file://<espejo>`).
6. `vertical_push × bodyweight` se cubre con dos ejercicios de dificultad 3: para
   principiantes sin equipo el motor tendrá que relajar la dificultad o usar afinidad.

## Peticiones a otros agentes

- **orquestador / arquitecto**: resolver CC-0001; decidir si `specs/enrichment-rules.yaml`
  pasa a propiedad de `ingesta-datos` (hoy solo lo lee la ingesta) para fusionar ahí las
  reglas de `enrichment-overrides.yaml`.
- **backend-api**: adoptar `backend/app/models/catalog.py` (ahora de su propiedad), crear la
  migración Alembic equivalente (con `unaccent`, `pg_trgm`, índices GIN/trigram) y mover
  `Base` a `app/db` si lo prefiere; la caché de `ExerciseCard` debe ordenar
  `secondary_muscles` por `position`.
- **motor-rutinas**: regenerar `engine/tests/fixtures/catalog.json` con
  `forja-ingest export-cards --output ../engine/tests/fixtures/catalog.json` (F1-ENG-19);
  roles `warmup` y `mobility` presentes; `deprecated=false` en todo el catálogo.
- **devops-despliegue**: servicio `ingest` = `forja-ingest fetch && forja-ingest load`
  (añadir `--create-schema` solo hasta que exista la migración); la imagen debe incluir
  `specs/` (o `FORJA_SPECS_DIR`) y `git`; nginx no debe exponer `$MEDIA_ROOT/source/`.
- **experto-entrenamiento**: revisar `docs/enrichment-report.md`, `specs/overrides/staples.yaml`
  y `docs/names-es-review.md` (F1b-EXP-01…03).

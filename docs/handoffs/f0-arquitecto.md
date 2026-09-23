# Handoff · Fase 0 · arquitecto

Rama: `f0/arquitecto` (desde `main`, sin fusionar). Fecha: 2026-09-23.

## Resumen

Fundaciones de Forja completas:

- **Monorepo** según MASTER_PROMPT §4.2 con tres proyectos uv independientes (`engine`,
  `nutrition`, `backend`) en Python 3.12 y un frontend Vite + React 18 + TypeScript estricto.
  Cada paquete tiene ruff, mypy `--strict`, pytest y umbrales de cobertura (§2.2). El
  frontend tiene ESLint (typescript-eslint `strictTypeChecked` + jsx-a11y), Vitest 4 con
  umbral del 85 %, Playwright (Chromium escritorio + WebKit móvil) y Lighthouse CI.
- **Contratos**: `contracts/openapi.yaml` (OpenAPI 3.1, 1.0.0: 59 rutas, 71 operaciones,
  186 esquemas) cubre el 100 % de §9 más 7 ampliaciones justificadas (ADR 0009), con
  RFC 9457, cookie + CSRF, paginación por cursor, `ETag`, `Idempotency-Key` y ejemplos en
  español. `contracts/domain.md` define entidades (tablas), 46 enumeraciones, los DTOs de
  ambos motores con tipos e invariantes y la API pública de los motores.
- **Test de contrato** (`backend/tests/contract/test_openapi_contract.py`): valida el
  esquema, exige exactamente los endpoints de §9 + ampliaciones aprobadas, comprueba
  convenciones (CSRF en escrituras, problem+json, cursor, `Idempotency-Key`, `ETag`,
  atribución de medios) y valida **todos** los ejemplos contra sus esquemas (los usará MSW).
- **ADRs 0001–0010**, **CI** de §13 (8 trabajos encadenados, todos con comprobaciones reales),
  **tablero** `docs/TASKS.md` de todas las fases, `docs/CONTRACT_CHANGES.md`,
  `.env.example` completo (verificado contra `Settings` por test) y `README.md` provisional.
- Código de producción mínimo y real: `app.core.config.Settings` (configuración por entorno de
  §12.3 con fallo rápido), `ENGINE_VERSION`/`NUTRITION_VERSION`, `scripts/coverage_gate.py`
  y la página raíz de la SPA. No hay lógica de negocio.

### Árbol creado
```
.github/workflows/ci.yml
.env.example  .gitignore  .python-version  Makefile  README.md  ruff.toml
contracts/{openapi.yaml,domain.md}
docs/{TASKS.md,CONTRACT_CHANGES.md}  docs/adr/{README.md,0001…0010}  docs/handoffs/f0-arquitecto.md
scripts/coverage_gate.py
backend/{pyproject.toml,uv.lock,README.md}
backend/app/{api,core,db,models,schemas,services,repositories,security,pdf}/__init__.py  backend/app/core/config.py
backend/migrations/versions/  backend/ingest/{__init__.py,tests/fixtures/}
backend/tests/{unit,integration,contract}/
engine/{pyproject.toml,uv.lock,README.md}  engine/forja_engine/{__init__.py,py.typed}  engine/tests/
nutrition/{pyproject.toml,uv.lock,README.md}  nutrition/forja_nutrition/{__init__.py,py.typed,data/}  nutrition/tests/
frontend/{package.json,package-lock.json,index.html,vite.config.ts,playwright.config.ts,eslint.config.js,lighthouserc.json,tsconfig.json,tsconfig.node.json}
frontend/src/{main.tsx,App.tsx,styles/global.css,routes,features,components,lib,i18n,sw}/  frontend/tests/  frontend/e2e/smoke.spec.ts
deploy/{nginx,lxc,scripts,backup}/
```

## Ficheros tocados

Todos nuevos salvo `README.md` (sustituido por el README provisional del proyecto; el
contenido del kit sigue descrito en `ORCHESTRATION.md`). No se ha modificado
`MASTER_PROMPT.md`, `ORCHESTRATION.md`, `CLAUDE.md`, `specs/` ni `.claude/`.

| Zona | Ficheros |
|---|---|
| Raíz | `.env.example`, `.gitignore`, `.python-version`, `Makefile`, `README.md`, `ruff.toml` |
| Contratos | `contracts/openapi.yaml`, `contracts/domain.md` |
| Docs | `docs/TASKS.md`, `docs/CONTRACT_CHANGES.md`, `docs/adr/*.md`, `docs/handoffs/f0-arquitecto.md` |
| CI | `.github/workflows/ci.yml`, `frontend/lighthouserc.json` |
| Python | `engine/**`, `nutrition/**`, `backend/**` (esqueleto, `app/core/config.py`, tests unit/integración/contrato), `scripts/coverage_gate.py` |
| Frontend | `frontend/**` (configuración, `src/main.tsx`, `src/App.tsx`, `src/styles/global.css`, tests, `e2e/smoke.spec.ts`) |
| Deploy | `deploy/{nginx,lxc,scripts,backup}/.gitkeep` |

Commits (Conventional Commits, en inglés):
```
878661d chore: scaffold python packages with uv, ruff, mypy and pytest
95ee5a4 chore: scaffold frontend with vite, strict typescript, eslint, vitest and playwright
c5f2a56 build: add root makefile with lint, typecheck and test targets
174d904 feat(contracts): add OpenAPI 3.1 contract covering all API endpoints
d75b8a6 docs(contracts): add domain model with entities, enums and engine DTOs
4108315 docs(adr): add initial architecture decision records 0001-0010
6377b4f ci: add github actions pipeline with lint, types, tests, build, e2e and lighthouse
b22f4a8 docs: add complete env example and provisional project readme
d51ed10 docs: add task board for all phases and contract change log
9fc9c8c chore: add deploy directory skeleton
(+ este handoff)
```

## Decisiones (y ADRs)

| ADR | Decisión clave |
|---|---|
| 0001 | Stack de §4.1 con versiones mínimas; Vitest 4.1.11 (Vitest 3 tenía un aviso moderado; Vitest 5 exige Node 22) |
| 0002 | Matriz de propiedad de directorios y zonas compartidas (`backend/pyproject.toml`, `catalog.py`, `ci.yml`, `TASKS.md`) |
| 0003 | Sesión opaca en cookie `__Host-forja_session`, CSRF de doble envío (`__Host-forja_csrf` + `X-CSRF-Token`, también en login/registro), `GET /auth/csrf`, `REGISTRATION_OPEN=false` por defecto |
| 0004 | Medios fuera del repo, copia byte a byte, `manifest.json` con SHA-256, `auth_request`, `media.attribution` en toda respuesta con medios |
| 0005 | Motores como paquetes puros con venv propio (la pureza la garantiza el entorno), tablas YAML con `tables_hash` |
| 0006 | Offline: IndexedDB + `client_uuid` + `Idempotency-Key` + `/sync` por lotes, «última escritura gana» por `updated_at`, tombstones |
| 0007 | Archivo (titulares) + **Inter** (texto; cifras tabulares `tnum`), autoalojadas con `@fontsource-variable` |
| 0008 | Proyectos uv independientes (no workspace) y npm ≥ 10 (npm 9 de Debian falla en `npm install`, `npm ci` sí funciona) |
| 0009 | Convenciones de API y ampliaciones de §9: `/auth/csrf`, `/auth/sessions`, `/auth/sessions/{id}`, `/about`, `/generator/preview/regenerate-day`, `/generator/preview/swap`, `GET /nutrition/plans`; `DELETE /body-metrics/{metric_id}` |
| 0010 | GitHub Actions; umbrales separados de líneas/ramas con `scripts/coverage_gate.py`; la categoría PWA ya no existe en Lighthouse 12 ⇒ comprobaciones PWA equivalentes en Playwright (Fase 3) |

Otras decisiones recogidas en `contracts/domain.md`: índices desde 0 (`set_index` desde 1),
unidades siempre métricas, semillas ≤ 2^53−1, enumeraciones como `text` + `CHECK`, tablas
añadidas `nutrition_settings` e `idempotency_key`, `set_log.deleted_at` (tombstone) y
`client_updated_at` para la sincronización.

## Cómo verificar (comandos exactos)

```bash
cd /root/forja-kit && git checkout f0/arquitecto
export PATH=$HOME/.local/bin:$PATH          # uv
make install                                # uv sync --locked ×3 + npm ci
make lint typecheck test; echo "exit $?"    # esperado: exit 0 (requiere Docker para integración)
make e2e                                    # requiere: (cd frontend && npx playwright install --with-deps chromium webkit)
make build                                  # wheels + bundle del frontend
uv run --locked --project backend openapi-spec-validator contracts/openapi.yaml
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest   # CI sin errores
(cd frontend && npm run build && npx --yes @lhci/cli@0.14.0 autorun) # Lighthouse (CHROME_PATH si no hay Chrome)
```

Resultados obtenidos en esta rama:

| Comando | Resultado |
|---|---|
| `make lint typecheck test` | **exit 0** |
| `make lint-contracts` | `contracts/openapi.yaml: OK` |
| `make e2e` | 2 passed (chromium-desktop, webkit-mobile) |
| `make build` | exit 0 (bundle 46,2 KB gzip) |
| `actionlint` | exit 0, sin avisos |
| Lighthouse CI local | todas las aserciones (≥ 0,9) superadas |
| `npx openapi-typescript@7 contracts/openapi.yaml` + `tsc --strict` | genera 5.230 líneas de tipos sin errores |
| `npm audit` | 0 vulnerabilidades |

## Métricas

| Paquete | Tests | Cobertura líneas | Cobertura ramas | Umbral |
|---|---|---|---|---|
| engine | 2 | 100 % | 100 % | 100 % / 95 % |
| nutrition | 2 | 100 % | 100 % | 100 % / 95 % |
| backend (unit + contrato + integración) | 395 | 100 % | 100 % | 90 % / 90 % |
| frontend (Vitest) | 3 | 100 % | 100 % | 85 % |
| E2E (Playwright) | 2 | — | — | — |

Contrato: 59 rutas, 71 operaciones (64 de §9 + 7 ampliaciones), 186 esquemas; 228
comprobaciones de ejemplo contra esquema (ejemplos de esquemas, cuerpos, respuestas y
parámetros, incluidas las respuestas de error compartidas en cada operación).

## Riesgos/pendientes

1. **Congelar contratos**: el orquestador debe revisar y etiquetar `contracts-v1` (F0-ORQ-01).
2. **CI no ejecutada en GitHub**: validada con `actionlint` y reproduciendo cada paso en
   local; la primera ejecución real ocurrirá al subir la rama/PR.
3. **npm 9 del sistema**: `npm install` (añadir dependencias) falla con un error interno de
   npm 9; usar npm ≥ 10 (`npm install --prefix ~/.local/npm10 npm@10` y anteponer
   `~/.local/npm10/node_modules/.bin` al `PATH`). `npm ci` y `npm run` funcionan con npm 9.
4. **Playwright local** necesita `npx playwright install --with-deps chromium webkit`
   (instala librerías del sistema con apt); ya hecho en este entorno.
5. **Lighthouse PWA**: la categoría desapareció en Lighthouse 12; se sustituye por
   comprobaciones en Playwright (ADR 0010, tarea F3-QA-03). El orquestador debe aceptar esta
   interpretación de §10.5.
6. **Ampliaciones del contrato** (ADR 0009) y la interpretación de `DELETE /body-metrics`
   necesitan el visto bueno del orquestador al congelar.
7. **Ejemplos del contrato**: los `media_id` de las rutas de medios y los UUID son
   ilustrativos; los ids de ejercicio (`0043`) proceden de los staples reales.
8. Las decisiones de detalle de la tabla `exercise` (`variant_kind`, `variant_label_es`) y de
   nutrición (`nutrition_settings`) amplían §5 y deben respetarse en los modelos de Fase 2.

## Peticiones a otros agentes

- **orquestador**: revisar `contracts/` y ADR 0009, crear el tag `contracts-v1` tras fusionar
  (F0-ORQ-01); confirmar la interpretación de Lighthouse PWA (ADR 0010).
- **ingesta-datos**: usar los códigos de `contracts/domain.md` §3 (p. ej. `BodyPart` en
  `snake_case`, `VariantKind`) y validar `export-cards` contra `ExerciseCard` del contrato;
  puede añadir `[project.scripts] forja-ingest` y sus dependencias a `backend/pyproject.toml`
  (ADR 0002). Cobertura del paquete `ingest` ≥ 95 % (ya incluido en `--cov=ingest`).
- **motor-rutinas / motor-nutricion**: implementar los DTOs y la API pública exactamente como
  `contracts/domain.md` §5–§6; cualquier campo o código de aviso nuevo pasa por
  `docs/CONTRACT_CHANGES.md`. `make test-engine` / `make test-nutrition` aplican el umbral
  100 % líneas y ≥ 95 % ramas.
- **frontend-ui**: generar el cliente con `openapi-typescript` (verificado compatible) y los
  mocks MSW de los ejemplos; sustituir `src/App.tsx` por el shell; fuentes según ADR 0007;
  CSRF según ADR 0003; usar npm ≥ 10 para añadir dependencias.
- **backend-api**: partir de `app/core/config.py` (`Settings`), implementar el esquema de
  `contracts/domain.md` §4 y añadir al test de contrato la comparación con el OpenAPI
  exportado (F2-BE-17). Mantener `test_env_example.py` al añadir variables.
- **devops-despliegue**: `deploy/docker-compose.yml` y objetivos de operación del `Makefile`
  (sección reservada en su cabecera); la imagen del backend debe incluir `specs/`; variables
  de compose ya documentadas en `.env.example` (`POSTGRES_*`, `WEB_PORT`).
- **qa-tests**: ampliar `frontend/e2e/` (hoy solo un smoke) y apuntar E2E/Lighthouse al
  despliegue en Fase 3 (`E2E_BASE_URL`).

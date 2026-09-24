# Handoff · Fase 1 · frontend-ui

Rama: `f1/frontend-ui` (desde `main` en `contracts-v1`, sin fusionar). Fecha: 2026-09-24.

## Resumen

Fundaciones de la Fase 1 de `frontend-ui` completas, sobre el esqueleto de `f0/arquitecto`:

- **Cliente API** tipado generado desde `contracts/openapi.yaml` con `openapi-typescript` +
  `openapi-fetch` (`npm run gen:api` → `src/lib/api/schema.d.ts`, 5.233 líneas, nunca a mano),
  envuelto en `src/lib/api/client.ts` con middleware CSRF de doble envío (ADR 0003: cabecera
  `X-CSRF-Token` desde la cookie `__Host-forja_csrf` en todo método no seguro) y `unwrapApi`/
  `ApiError` para no repetir `{data, error}` en cada hook.
- **Mocks MSW generados del contrato**: `scripts/generate-msw-handlers.js` (`npm run gen:mocks`)
  parsea `contracts/openapi.yaml` y crea un handler por operación (71) a partir de la primera
  respuesta 2xx: reutiliza el `example` de la operación/esquema si existe, y si no, sintetiza uno
  recorriendo el JSON Schema (`$ref`, `allOf`, `oneOf`/`anyOf`, `enum`/`const`, formatos
  conocidos). Salida en `src/mocks/handlers.generated.ts`; `src/mocks/{handlers,server,browser}.ts`
  la envuelven para Vitest (`msw/node`) y para el navegador (`msw/browser`, con
  `public/mockServiceWorker.js`).
- **Sistema de diseño «Forja»**: `src/styles/tokens.css` (colores oscuro/claro, acento «brasa»
  con degradado, semánticos con variante de texto AA por tema, espaciado, radios, sombras,
  tipografía) y tipografía autoalojada Archivo + Inter (`@fontsource-variable`, ADR 0007, sin
  CDNs, empaquetada por Vite en `/assets` con hash).
- **`ExerciseMedia`**: único componente autorizado para medios de ejercicio. Máximo 180 px CSS
  (ancho/alto explícitos + `style` inline como defensa adicional), `loading="lazy"`,
  `decoding="async"`, atribución «© Gym visual — https://gymvisual.com/» obligatoria con
  `rel="noopener"` — si el medio no trae la atribución exacta, **lanza** en vez de omitirla.
  Respeta `prefers-reduced-motion` (fuerza miniatura + botón «Reproducir animación»; un clic
  explícito siempre reproduce, incluso con movimiento reducido). Regla ESLint
  (`no-restricted-syntax`) que prohíbe `<img>` fuera de este fichero.
- **Shell**: TanStack Router (rutas por código), navegación única (`AppNav`) que se reposiciona
  por CSS: barra inferior en móvil, carril lateral en escritorio (`MASTER_PROMPT` §10.1). Cinco
  secciones — Hoy, Rutinas, Biblioteca, Progreso, Perfil — cada una con una pantalla real que
  consulta la API generada vía TanStack Query contra los mocks MSW (nada de contenido estático
  de relleno): `/stats/overview`, `/programs`, `/exercises`, `/stats/volume`, `/about`
  (créditos: MIT del dataset, aviso de Gym visual, commit SHA, aviso sanitario).
- **i18n**: `i18next` + `react-i18next`, `es` por defecto y único fallback, `en` como segundo
  idioma; recursos con pluralización (`_one`/`_other`); test estructural que compara las claves
  de `es` y `en` para que no diverjan.

## Ficheros tocados

Todo dentro de `frontend/` (ADR 0002); no se ha tocado `frontend/e2e/` (zona de `qa-tests`).

| Área | Ficheros |
|---|---|
| Dependencias/scripts | `frontend/package.json`, `package-lock.json`, `scripts/generate-msw-handlers.js`, `public/mockServiceWorker.js` |
| Cliente API | `src/lib/api/client.ts`, `src/lib/api/schema.d.ts` (generado) |
| Mocks MSW | `src/mocks/{handlers.generated.ts (generado), handlers.ts, server.ts, browser.ts}` |
| Diseño | `src/styles/tokens.css`, `src/styles/global.css`, `src/lib/theme.ts` |
| `ExerciseMedia` | `src/components/ExerciseMedia.tsx`, `ExerciseMedia.module.css` |
| Shell | `src/App.tsx`, `src/main.tsx`, `src/routes/{router.tsx, RootLayout.tsx, RootLayout.module.css, TodayRoute.tsx, ProgramsRoute.tsx, LibraryRoute.tsx, ProgressRoute.tsx, ProfileRoute.tsx}`, `src/components/{AppNav.tsx, AppNav.module.css, QueryState.tsx}` |
| Datos por pantalla | `src/features/{today,programs,library,progress,profile}/use*.ts` |
| i18n | `src/i18n/{index.ts, resources.ts}` |
| Utilidades | `src/lib/{cx.ts, queryClient.ts, useReducedMotion.ts}` |
| Config | `eslint.config.js`, `tsconfig.json`, `vite.config.ts` |
| Tests | `tests/{App,main,design-tokens,i18n}.test.tsx`, `tests/lib/api-client.test.ts`, `tests/components/ExerciseMedia.test.tsx`, `tests/routes/{TodayRoute,ProgramsRoute,LibraryRoute,ProgressRoute,ProfileRoute}.test.tsx`, `tests/routes/renderWithQuery.tsx`, `tests/setup.ts` |
| Tablero | `docs/TASKS.md` (estado de F1-FE-01…08) |

Commits (Conventional Commits, en inglés) en `f1/frontend-ui`:
```
d22d44b chore(frontend): add API codegen and MSW dependencies
c907f5c feat(frontend): generate MSW mocks from the OpenAPI contract
2f9f82f feat(frontend): add typed API client with CSRF middleware
e67d08c feat(frontend): add Forja design tokens and self-hosted fonts
5dcd28a feat(frontend): add i18n resources for es/en
f5b3185 feat(frontend): add ExerciseMedia, the only component for exercise media
e67e2ef feat(frontend): add app shell with TanStack Router and navigation
7b1a294 fix(frontend): make the API client and test env work together
(+ este handoff y docs/TASKS.md)
```

## Decisiones (y ADRs)

No se ha creado ningún ADR nuevo; se han seguido los existentes (0002, 0003, 0007, 0008, 0009).
Decisiones locales documentadas en el propio código:

- **`fetch` envuelto en el cliente API** (`client.ts`): `openapi-fetch` resuelve
  `globalThis.fetch` **una sola vez**, al crear el cliente (parámetro por defecto). Cualquier
  herramienta que parchee `fetch` global después (MSW en los tests, o un interceptor en
  producción) no tendría efecto. Se pasa `fetch: (request) => globalThis.fetch(request)` para
  que cada petición lea la referencia vigente.
- **`baseUrl` absoluta** (`window.location.origin + "/api/v1"`, con `"/api/v1"` como
  alternativa fuera de un navegador): el `Request` del Fetch API solo resuelve rutas relativas
  frente a un documento; en Node (tests) no hay documento y una base relativa lanza
  `Invalid URL`. En el navegador real el resultado es idéntico (mismo origen tras nginx, §4.3).
- **Generador de mocks propio** (`scripts/generate-msw-handlers.js`) en vez de una librería de
  terceros: 71 operaciones, comportamiento predecible y auditable, sin dependencia adicional.
  Se ejecuta como *pre-hook* de npm (`predev`/`prebuild`/`prelint`/`pretypecheck`/`pretest`)
  para que el esquema y los mocks estén siempre regenerados desde el contrato vigente.
- **Rutas por código** (no *file-based routing* con generación de `routeTree.gen.ts`): para
  cinco rutas planas de Fase 1, evita un paso de generación adicional; se puede migrar a
  file-based cuando el árbol de rutas crezca en Fase 2 sin romper la API pública de las pantallas.
- **`ExerciseMedia` sin previsualización al pasar el cursor** (Fase 1): el «pasar el cursor o
  mantener pulsado en tarjetas» de §10.1 no tiene equivalente de teclado sin más trabajo de
  interacción; se ha preferido no enviar un patrón inaccesible y dejarlo para la pantalla
  Biblioteca de la Fase 2 (F2-FE-08), donde si se puede dar foco/teclado además de ratón.
- **Sin librería de componentes Radix en esta entrega** (ver Riesgos): el encargo recibido para
  esta iteración de Fase 1 (tokens, fuentes, shell, i18n, cliente API, mocks, `ExerciseMedia`)
  no incluía la librería de componentes base; no se ha construido para no exceder el alcance
  pedido. F1-FE-04 queda pendiente en el tablero con esta nota.

## Cómo verificar

```bash
export PATH=$HOME/.local/bin:$HOME/.local/npm10/node_modules/.bin:$PATH   # npm 10 (ADR 0008)
cd frontend
npm run gen                    # gen:api + gen:mocks (también se ejecuta solo, ver package.json)
npm run lint                   # ESLint, 0 avisos
npm run typecheck              # tsc --strict (app + tests + config de Vite)
npm run test                   # Vitest + cobertura
npm run build                  # tsc --noEmit + vite build
npm run dev                    # arranca con MSW activo en el navegador (abrir http://localhost:5173)
```
Desde la raíz del repo, `make lint-frontend typecheck-frontend test-frontend` y `make build`
ejecutan exactamente lo anterior (los objetivos del `Makefile` son zona del arquitecto; no se
han tocado, solo se han verificado en verde).

Comprobación manual de la regla ESLint (`<img>` fuera de `ExerciseMedia.tsx`): se creó un
fichero de prueba con un `<img>` suelto en `src/components/`, `npx eslint` lo marcó con
`no-restricted-syntax` citando MASTER_PROMPT §2.1/ADR 0004, y se borró después (no queda en el
repo).

## Métricas

| Comando | Resultado |
|---|---|
| `npm run lint` | 0 errores / 0 avisos |
| `npm run typecheck` (app + tests + config Vite) | 0 errores |
| `npm run test` | **44/44 tests verdes**, 11 ficheros |
| Cobertura (Vitest v8) | líneas 95,86 % · ramas 92,95 % · funciones 96,29 % · sentencias 95,89 % (umbral 85 %, `vite.config.ts`) |
| `npm run build` | JS inicial `index-*.js` **103,69 KB gzip** (< 200 KB, §10.5); CSS 2,21 KB gzip; fuentes fuera del JS inicial (paquetes woff2 de Archivo/Inter, 15–133 KB cada uno, cacheables aparte) |
| `make build` (raíz) | exit 0 (wheels de `engine`/`nutrition`/`backend` + build de frontend) |
| `make lint-placeholders` | sin marcadores prohibidos |
| Mocks MSW generados | 71 handlers (1 por operación del contrato), reproducibles con `npm run gen:mocks` |

Nota de cobertura: se excluyen de la medición `src/lib/api/schema.d.ts` (tipos generados),
`src/mocks/handlers.generated.ts` (datos de ejemplo generados, no lógica) y `src/mocks/browser.ts`
(arranque de un Service Worker real, que por diseño nunca se ejecuta en jsdom). El resto del
código de aplicación se mide sin excepciones.

## Riesgos/pendientes

1. **F1-FE-04 (componentes base sobre Radix) no está hecho.** El encargo explícito de esta
   entrega (tokens, fuentes, shell, i18n, cliente API, mocks, `ExerciseMedia`) no lo incluía;
   se ha priorizado no exceder el alcance pedido. Lo necesitará la Fase 2 (wizard, editor,
   reproductor, NumberPad…): recomiendo encargarlo explícitamente al inicio de F2-frontend-ui,
   con axe-core en los tests de cada componente (regla del rol).
2. **`frontend/e2e/smoke.spec.ts` (zona de `qa-tests`) ha quedado desactualizado.** Comprobado
   ejecutándolo: `npm run build && npm run preview` sirve el nuevo shell, pero el test espera
   `<h1>Forja</h1>` y ahora el encabezado de la ruta «Hoy» es `<h1>Hoy</h1>` (el nombre «Forja»
   solo está como nombre accesible del `<nav>`). Además, en el build de producción (`preview`)
   no arranca MSW a propósito (solo se activa en desarrollo con soporte real de Service
   Worker), así que las peticiones a `/api/v1/*` fallan por falta de backend — eso ya se
   esperaba y lo resolverá la Fase 3 apuntando `E2E_BASE_URL` al despliegue con
   `docker compose`. No he tocado este fichero (ADR 0002); ver petición a `qa-tests` abajo.
3. **Presupuesto de rendimiento sin *code-splitting* por ruta todavía.** El bundle actual
   (103,69 KB gzip) está muy por debajo del límite de 200 KB con una sola ruta cargada de forma
   eager por página, así que no ha sido necesario dividirlo aún. Recharts, `dnd-kit` y el editor
   de rutinas (Fase 2) sí deberán ir en *chunks* diferidos por ruta antes de acercarse al
   límite; dejo la pauta ya establecida en `src/routes/router.tsx` (una ruta = un componente)
   para introducir `React.lazy` por ruta sin reestructurar nada.
4. **Créditos (`ProfileRoute`) solo cubre lo que expone `GET /about`.** Ajustes, unidades,
   idioma, tema, exportar/importar/borrar cuenta, sesiones activas, etc. (resto de §10.2.10)
   son Fase 2 (F2-FE-12).
5. **`i18next` inicializado como efecto secundario del módulo** (`src/i18n/index.ts`, importado
   por `App.tsx`); es intencionado (recursos embebidos, sin backend de traducciones, por lo que
   la inicialización es síncrona en la práctica) pero cualquier test que renderice componentes
   con `useTranslation()` fuera del árbol de `App` debe importar `"../../src/i18n"` primero,
   como hacen `tests/components/ExerciseMedia.test.tsx` y `tests/routes/*.test.tsx`.

## Peticiones a otros agentes

- **qa-tests**: actualizar `frontend/e2e/smoke.spec.ts` al nuevo shell — por ejemplo, comprobar
  `page.getByRole("navigation", { name: "Forja" })` en vez de un `<h1>Forja</h1>`, y/o el
  encabezado `<h1>Hoy</h1>` de la ruta inicial. Cuando ampliéis `frontend/e2e/` en la Fase 3,
  el arranque de MSW en producción no está disponible a propósito (solo desarrollo); los E2E
  reales necesitarán `docker compose` con `backend-api` (`E2E_BASE_URL`), como ya prevé
  `playwright.config.ts`.
- **backend-api**: el cliente y los mocks están generados 1:1 desde `contracts/openapi.yaml`
  vigente (`contracts-v1`); cualquier cambio de contrato en Fase 2 solo requiere
  `npm run gen` (ya encadenado como *pre-hook* de `dev`/`build`/`lint`/`typecheck`/`test`) para
  que el frontend quede sincronizado sin tocar código a mano.
- **orquestador**: F1-FE-04 (componentes Radix) ha quedado fuera de esta entrega por alcance
  explícito del encargo recibido; si se necesita antes de empezar la Fase 2, indíquenlo como
  tarea propia.

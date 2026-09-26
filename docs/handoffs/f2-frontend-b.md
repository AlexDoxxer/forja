# Handoff · Fase 2 · frontend-ui (parte B)

Rama: `f2/frontend-b` (con `main` fusionado: contrato 1.1.0 y parte A). Sin fusionar a `main`. Modo rápido: solo Vitest, lint y tsc; sin E2E, Lighthouse ni capturas.

## Resumen

- **Hoy**: sesión del día (`scheduled` / `rest_day` / `no_active_program` / `program_completed`), «Empezar» (crea la sesión en IndexedDB y encola su alta), «Continuar sesión», resumen semanal, último récord, peso corporal rápido (`POST /body-metrics`) y cambios pendientes de sincronizar.
- **Reproductor** (`features/session/`): máquina de estados con reductor puro (`exercising → resting → finished → completed`), placa de medio con `ExerciseMedia` (atribución), teclado numérico propio, RIR, anillo de descanso por marcas de tiempo (±15 s, saltar, `aria-live`), vibración, sonido (Web Audio), notificación en segundo plano, calentamiento de aproximación con discos por lado, instrucciones paso a paso, cambio en caliente (alternativas del backend), deshacer, Wake Lock, estado persistido en IndexedDB (`idb`) y recuperado tras recarga, cola offline (`session_upsert`/`set_upsert`/`set_delete`), `/sync` en lotes de 500, reintento exponencial 1 s → 5 min con jitter, Background Sync donde exista, corrección de reloj con `server_time`, UUID v7.
- **Resumen de sesión**: totales locales al instante (offline) y récords del servidor vía `POST /sessions/{id}/finish` (idempotente) cuando la sesión ya está sincronizada.
- **Progreso**: mapa de calor de 26 semanas, volumen semanal por grupo, e1RM por ejercicio, récords, peso con media móvil de 7 días. Recharts en chunk diferido (`ProgressCharts`); cada gráfica tiene su tabla de datos.
- **Nutrición** (`/nutricion`): anillos en tono neutro (sin rojo/verde), aviso de seguridad permanente, objetivo bloqueado como nota informativa, `tolerance_not_met` informativo (nunca error), plan semanal por días/comidas, intercambio de alimentos (automático o buscado), lista de la compra marcable (guardada en IndexedDB), ajustes y recálculo.
- **Perfil**: unidades, idioma, tema (oscuro/claro/sistema), sonidos, vibración, descanso por defecto, exportar/importar/eliminar cuenta, sesiones activas (revocar), «Descargar biblioteca» para uso offline, cerrar sesión y Créditos y licencias (MIT, Gym visual, SHA).
- **Admin** (`/admin`): registro abierto/cerrado, dieta global, usuarios (rol, activo, búsqueda), ingesta (simulación/real, ejecuciones con conteos, diff, errores, sondeo mientras corre).
- **Auth** (encargo extra): `/login`, guarda de sesión en `RootLayout` (`AuthGate`): 401 en `GET /auth/me` → `/login`; sin `onboarding_completed` → `/onboarding`. `/login` y `/onboarding` son públicas (el alta se hace en el paso 1 del onboarding). Un error de red/5xx no expulsa: ofrece reintentar.
- **PWA**: `manifest.webmanifest` (standalone, tema carbón, iconos SVG/PNG/maskable), service worker Workbox (`src/sw/sw.ts` con `vite-plugin-pwa` injectManifest): shell precacheado, `/api/v1/exercises*` SWR, miniaturas cache-first (1.400), GIFs cache-first con tope en bytes (300 MB, `VITE_GIF_CACHE_MB`), `PRECACHE_MEDIA`, evento `sync`. El resto de `/api/v1` no se cachea.

## Ficheros tocados

Todo en `frontend/` (más `docs/TASKS.md` y este handoff).
- Nuevos: `src/features/{session,progress,nutrition,profile,admin,auth,shared}/`, `src/sw/{sw,cachePolicy,library,register}.ts`, `src/routes/{NutritionRoute,AdminRoute}.tsx`, `public/manifest.webmanifest`, `public/icons/*`.
- Reescritos (pantallas propias): `src/features/today/*`, `src/routes/{TodayRoute,ProgressRoute,ProfileRoute}.tsx`.
- Compartidos con el shell, cambios mínimos: `src/routes/router.tsx` (rutas), `src/routes/RootLayout.tsx` (guarda), `src/main.tsx` (`bootPwa`), `index.html` (manifest), `vite.config.ts` (plugin PWA, exclusión de cobertura de `sw.ts`), `package.json`/lock (idb, workbox-*, vite-plugin-pwa, fake-indexeddb, user-event), `tests/setup.ts` (`fake-indexeddb/auto`).
- Tests: `tests/features/**`, `tests/routes/{Today,Progress,Profile}Route.test.tsx`.

## Decisiones

- Las cadenas de la parte B se registran con `registerBundle` (`features/shared/i18nB.ts`) en vez de editar `i18n/resources.ts`, para no chocar con la parte A; test de paridad es/en incluido.
- La calculadora de discos **no** se reimplementa: se muestran `plates_per_side_kg` y `warmup_sets` que calcula el backend (regla: sin lógica del motor en el cliente). Con un peso distinto del sugerido no hay desglose de discos.
- Superseries/circuitos se aplanan en orden en el reproductor (sin rondas).
- La media móvil de 7 días del gráfico de peso es presentación calculada en cliente; el resumen «Hoy» usa la del servidor.
- Rutas nutrición/admin/login cargadas bajo demanda; Recharts diferido.
- Tema y idioma siguen usando `localStorage` (convenience, ya existente); los datos de entreno solo IndexedDB.

## Cómo verificar

```bash
export PATH=$HOME/.local/bin:$HOME/.local/npm10/node_modules/.bin:$PATH
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Métricas

- Lint 0 avisos, `tsc` 0 errores, **191 tests verdes** (23 ficheros).
- Cobertura (con la parte A fusionada): sentencias 93,1 % · ramas 85,1 % · funciones 91,1 % · líneas 95,1 % (umbral 85 %).
- Build: JS inicial `index-*.js` **147,9 KB gzip** (< 200 KB); `ProgressCharts` (Recharts) chunk diferido; `sw.js` 8,8 KB gzip; precache de 20+ entradas.

## Riesgos/pendientes

- Sin E2E, Lighthouse ni capturas (modo rápido); el SW y Wake Lock/vibración/notificaciones solo se han probado con dobles (jsdom).
- Falta pasar de MSW a la API real (F2-FE-16) cuando `backend-api` aterrice; el guardado de la sesión en `/sync` asume `server_id` en `session_upsert`.
- nginx debe servir `/sw.js` y `/manifest.webmanifest` sin caché larga y `/sw.js` en la raíz (alcance `/`).
- La sesión que caduca a mitad de uso no redirige hasta la siguiente comprobación de `/auth/me`.
- El ruido «ExerciseMedia: no se puede mostrar…» en la salida de tests proviene de un test previo que provoca ese error a propósito.

## Peticiones a otros agentes

- **devops-despliegue**: cabeceras de `sw.js`/`manifest.webmanifest` (arriba); `MEDIA_REQUIRE_AUTH` funciona con el SW porque los medios se piden con `credentials: same-origin`.
- **backend-api**: `POST /sync` debe devolver `server_id` en `session_upsert` aplicados (el resumen lo usa); `POST /sessions/{id}/finish` idempotente con el mismo `finished_at`.
- **qa-tests**: E2E de «cortar la red a mitad de sesión», reanudar tras recarga, login/guarda y arranque offline con SW.

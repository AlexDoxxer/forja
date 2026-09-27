# Handoff · Fase 2 · frontend-ui — integración con la API real (F2-FE-16)

Rama: `f2/frontend-integration` (con `main` fusionado: contrato 1.2.0, motor de nutrición
0.2.0/engine 0.2.0). Sin fusionar a `main`. Modo rápido: solo tests de los ficheros tocados +
lint + tsc; sin Lighthouse.

## Resumen

**El flujo de Gate 2 funciona de extremo a extremo contra la API real** (sin MSW): alta →
onboarding → generar rutina → activar → entrenar una sesión completa (con temporizador de
descanso, cambio de peso/repeticiones por teclado, deshacer) → resumen de sesión → progreso
(mapa de calor, récords). También verificado contra la API real: Biblioteca (mapa muscular,
búsqueda), Detalle de ejercicio (medio con atribución), Editor de rutina, Perfil, Admin
(ajustes globales, usuarios, ingesta) y Nutrición (la pantalla carga; el cálculo de objetivo
falla por un bug del backend, ver más abajo).

Se encontraron y arreglaron **6 bugs de frontend** al integrar con la API real (el contrato
generado por MSW ocultaba varios porque los mocks eran más permisivos que el backend real).
Se documentan **2 bugs de backend** que no se tocan (ADR 0002): uno de `POST
/nutrition/targets/calculate` y uno de comportamiento en `POST /sync` con `set_index`
0-based aceptado en algún punto anterior; el mapeo con el contrato ya era 1-based, lo que se
arregló en el cliente (no es bug de backend, se detalla abajo en «Decisiones»).

## Cómo levantar la pila local

```bash
# 1) Postgres (contenedor efímero; ajusta el puerto si 55432 está ocupado)
docker run -d --name forja-pg -e POSTGRES_USER=forja -e POSTGRES_PASSWORD=forja \
  -e POSTGRES_DB=forja -p 55432:5432 postgres:16-alpine

# 2) Entorno para el backend (sustituye a `.env`; ajusta si usas otro puerto/host)
export DATABASE_URL=postgresql+asyncpg://forja:forja@localhost:55432/forja
export SECRET_KEY=devsecretdevsecretdevsecretdevsecret1234567890
export PUBLIC_BASE_URL=http://localhost:5173
export MEDIA_ROOT=/tmp/forja-media
export MEDIA_REQUIRE_AUTH=false
export REGISTRATION_OPEN=true

# 3) Migraciones + ingesta (si /tmp/forja-media no existe, antes: uv run forja-ingest fetch)
uv sync --project backend
cd backend
uv run alembic upgrade head
uv run forja-ingest load     # 1324 ejercicios, 2648 medios verificados

# 4) API (mismo entorno del paso 2 en esta shell)
uv run uvicorn --factory app.main:create_app --port 8000

# 5) Frontend, en otra shell — proxy /api → :8000, /media servido desde $MEDIA_ROOT
cd frontend
npm ci
MEDIA_ROOT=/tmp/forja-media npx vite --host 127.0.0.1
# abre http://localhost:5173 (habla con la API real por defecto)

# Recorrido automatizado (Playwright) que reproduce el Gate 2 y guarda capturas:
BASE_URL=http://localhost:5173 node frontend/scripts/gate2-live.mjs
```

Para volver a MSW en desarrollo (sin backend): `VITE_USE_MSW=1 npx vite`.

## Ficheros tocados

Todo en `frontend/` salvo este handoff y las capturas.

- **`frontend/vite.config.ts`**: plugin `devMedia` (solo `apply: "serve"`) que sirve
  `$MEDIA_ROOT` bajo `/media` en desarrollo, byte a byte, sin transformar (ADR 0004); el
  proxy de `/api` ahora es configurable con `VITE_API_TARGET` (por defecto `:8000`); se quitó
  el proxy fijo de `/media` (lo sustituye `devMedia`).
- **`frontend/src/main.tsx`**: MSW pasa a ser opt-in con `VITE_USE_MSW=1` (antes se activaba
  siempre que hubiera Service Worker en desarrollo); por defecto la app habla con la API real.
- **`frontend/src/lib/api/client.ts`**: el middleware CSRF ahora pide `GET /auth/csrf` una vez
  antes de la primera escritura si todavía no hay cookie `__Host-forja_csrf` (login y
  registro son la primera escritura de la sesión, así que antes fallaban con
  `403 csrf_failed`; MSW no lo exponía porque los mocks generados aceptan cualquier
  cabecera).
- **`frontend/src/i18n/partA/onboarding.ts`** y
  **`frontend/src/features/onboarding/OnboardingScreen.tsx`**: la fecha de nacimiento pasa a
  ser obligatoria (con su error), como la altura. `onboarding_completed` en el backend exige
  `birth_date + height_cm + parq_completed_at`; antes el wizard dejaba avanzar sin fecha de
  nacimiento y mostraba «Todo listo» aunque el backend seguía marcando el onboarding como
  incompleto (regresión silenciosa: la guarda de `/` habría reenviado a `/onboarding` en la
  siguiente carga).
- **`frontend/src/features/session/playerMachine.ts`**: `toSetCreate` ahora envía
  `set_index: set.setIndex + 1` (el contrato exige `set_index >= 1`; el estado interno del
  reproductor sigue siendo 0-based, solo cambia el mapeo a la operación de sincronización).
  Antes de este cambio, cada serie enviada se rechazaba con `422` para siempre.
- **`frontend/src/features/session/syncQueue.ts`**: cuando un lote entero se rechaza con
  `422` (una sola operación con datos inválidos, p. ej. RIR fuera de rango), la cola ya no
  reintenta el lote para siempre; lo divide y envía cada operación por separado, aislando la
  culpable (se descarta con un aviso visible en «Cambios pendientes de sincronizar», como ya
  hacía un `rejected` normal) y deja seguir al resto. Antes un solo dato inválido bloqueaba
  toda la sincronización de la sesión sin fin visible para la persona.
- **`frontend/src/features/progress/queries.ts`**: `GET /body-metrics` pedía `limit=120`,
  por encima del máximo del contrato (`maximum: 100`); devolvía `422` y la tarjeta de peso de
  Progreso se quedaba en error permanente. Bajado a 100.
- **`frontend/src/features/progress/ProgressScreen.tsx`** y **`progress.module.css`**: el
  mapa de calor de 26 semanas se desplaza automáticamente para mostrar la columna de hoy
  (antes se veía la primera semana, la más antigua, y había que hacer scroll horizontal a
  ciegas para ver la actividad reciente); la tarjeta que lo contiene ya no desborda su
  columna del grid de dos columnas en escritorio (`min-width: 0`).
- **`frontend/scripts/gate2-live.mjs`** (nuevo): recorrido Playwright end-to-end del Gate 2
  contra la API real, usado para las capturas y como regresión manual reproducible. Excluido
  del lint de TypeScript (no forma parte de la app).
- **`frontend/tests/lib/api-client.test.ts`**: test del nuevo comportamiento (pide
  `/auth/csrf` antes de la primera escritura sin cookie).
- **`frontend/tests/features/session/core.test.ts`**: test de que un `422` de una sola
  operación aísla y descarta esa operación sin bloquear el resto de la cola.
- **`frontend/tests/features/onboarding.test.tsx`**: cubre la fecha de nacimiento obligatoria
  y se ajustan los tests existentes para rellenarla.
- **`frontend/eslint.config.js`**: excluye `scripts/gate2-live.mjs` del proyecto de
  TypeScript de ESLint (script suelto, no forma parte del build de la app).
- **`docs/screenshots/*.png`** (19 capturas, nuevas): recorrido completo en móvil (390×844) +
  3 en escritorio (1280×800). Todas las que muestran medios de ejercicio (`06`, `07`, `13`)
  llevan la atribución «© Gym visual» visible sin modificar el fichero original.

## Decisiones

- **MSW opt-in**: se mantiene para tests (Vitest sigue usando `msw/node` vía
  `tests/setup.ts`, sin cambios) y para desarrollo sin backend (`VITE_USE_MSW=1`), pero deja
  de ser el comportamiento por defecto en `npm run dev`, que ahora es la vía principal según
  esta tarea.
- **Servir medios en desarrollo**: en vez de un segundo proxy hacia la API (que no sirve
  ficheros estáticos) o un `serve` aparte, un plugin de Vite (`devMedia`) lee directamente de
  `$MEDIA_ROOT`. Solo se activa con `apply: "serve"` (nunca en build/producción, donde nginx
  sirve `/media` con `auth_request`, ADR 0003/0004). No copia, transforma ni cachea el
  fichero — lo transmite con `createReadStream`, preservando bytes y sin exponer nada fuera
  de `$MEDIA_ROOT` (comprobación de `..` y de prefijo de ruta).
- **`set_index` 1-based**: se mantiene el estado interno del reproductor 0-based (no se toca
  la máquina de estados, ya cubierta por tests) y el ajuste se hace solo en el punto de
  conversión a `SyncOperation`, que es donde vive el contrato.
- **Aislar un `422` de lote en vez de reintentarlo entero**: un lote de hasta 500
  operaciones se envía junto; si el servidor rechaza el lote completo con `422` (una sola
  operación mal formada rompe la validación de todo el `SyncRequest`), reintentar el lote tal
  cual nunca convergería. Se aísla recursivamente (divide y vencerás) hasta encontrar la
  operación culpable, que se marca `rejected` igual que si el servidor la hubiera aceptado
  como tal explícitamente; el resto de operaciones del lote se reenvían normalmente. No hace
  falta lógica de negocio del motor para esto, solo manejo de errores de transporte.
- **Onboarding exige fecha de nacimiento**: el backend (`onboarding_completed`, ver
  `backend/app/services/auth.py`) no la trata como opcional pese a que el campo del formulario
  no tenía validación de obligatoriedad; se alinea el frontend al contrato real de
  «onboarding completo» en vez de pedir al backend que la relaje (fuera de alcance, y tiene
  sentido pedirla: personaliza el algoritmo del generador).

## Cómo verificar

```bash
export PATH=$HOME/.local/bin:$HOME/.local/npm10/node_modules/.bin:$PATH
cd frontend
npm run lint && npm run typecheck && npm test && npm run build
```

Con la pila local levantada (sección anterior):

```bash
BASE_URL=http://localhost:5173 node frontend/scripts/gate2-live.mjs
```

El script termina con código 0 y `[gate2] sin errores HTTP/JS` si no hubo ninguna respuesta
`>= 400` (aparte del `401` esperado de `GET /auth/me` sin sesión) ni ningún error de consola
de página. Guarda 19 capturas en `docs/screenshots/`.

## Métricas

- Lint: 0 avisos (incluye `gen:api`/`gen:mocks` como pretareas; sin diff porque el contrato
  ya estaba regenerado tras el merge de `main`).
- `tsc --noEmit`: 0 errores.
- Vitest: **194 tests verdes** (25 ficheros); 2 tests nuevos (CSRF en frío, aislamiento de un
  `422` de lote), 1 test nuevo y 3 ajustados en onboarding.
- Build de producción: `index-*.js` **148,2 KB gzip** (< 200 KB), `sw.js` 8,75 KB gzip,
  precache 43 entradas.
- Recorrido Gate 2 end to end contra la API real: **OK**, 0 errores HTTP/JS al final de la
  ejecución (tras las correcciones de este handoff).

## Riesgos / pendientes

- **`Rate limiting` / cuenta bloqueada tras muchos registros de prueba**: no se ha topado con
  él durante la verificación (`REGISTRATION_OPEN=true` en local), pero no se ha probado el
  límite de tasa de `/api/v1/auth/` con el proxy de Vite; en producción lo aplica nginx
  (`limit_req`), fuera de esta tarea.
- **Mensaje de error de registro impreciso**: si `POST /auth/register` falla con `403` por
  cualquier motivo (no solo «registro cerrado», también un `csrf_failed` transitorio antes de
  esta corrección), el frontend siempre muestra «El registro está cerrado en este servidor.»
  (`onboarding.account.errorForbidden`, mapeo de `status === 403` en
  `OnboardingScreen.registerAccount`). Con la corrección del CSRF en frío esto ya no debería
  darse en el flujo normal, pero el mensaje sigue siendo engañoso si ocurre por otra causa.
  No se ha tocado por ir más allá del alcance de esta tarea (F2-FE-16 es integración, no una
  revisión de copys de error); lo dejo anotado por si `qa-tests` lo encuentra.
- **`docker compose` no se ha probado** para este flujo (se usó `docker run postgres:16-alpine`
  suelto + `uvicorn` y `vite` directos, más simple para iterar). Los comandos de
  `docs/handoffs/f2-backend-api.md` con `make up`/`docker-compose` no se han re-verificado
  aquí; deberían funcionar igual porque no se ha tocado nada de `backend/` ni `deploy/`.
- **Nutrición**: la pantalla carga y el resto de acciones (ajustes, generar plan) no se
  probaron a fondo porque `POST /nutrition/targets/calculate` (paso previo lógico) falla en
  el backend — ver bugs abajo. Cuando ese bug se arregle, conviene repetir el recorrido de
  Nutrición completo (generar plan semanal, lista de la compra, intercambio de alimentos).
- Este entorno tenía además un `docker-compose` (`forja-deploy-*`) corriendo de forma
  independiente en el host (contenedores `web`/`api`/`db`), no relacionado con esta tarea; no
  se ha tocado.

## Bugs de backend encontrados (no corregidos aquí, ADR 0002)

1. **`POST /nutrition/targets/calculate` devuelve `422` con cuerpo `{}` (el que envía el
   frontend, que es válido: todos los campos del `NutritionTargetOverrides` son opcionales).**
   - Endpoint: `POST /api/v1/nutrition/targets/calculate`
   - Request: `{}` (con sesión válida y CSRF correcto)
   - Response observada:
     ```json
     {
       "type": "/problems/validation-error", "status": 422,
       "errors": [
         {"loc": ["fat", "max_pct_kcal"], "msg": "Extra inputs are not permitted", "type": "extra_forbidden"},
         {"loc": ["tolerances", "fat_over_allowed"], "msg": "...", "type": "extra_forbidden"}
       ]
     }
     ```
   - Esperado: `201`/`200` con un `NutritionTargetRecord` (o el error de validación real si el
     perfil no tiene datos suficientes, pero no `extra_forbidden` sobre campos que el propio
     backend genera internamente).
   - El error ocurre con un cuerpo vacío, así que no es una discrepancia de lo que envía el
     frontend: `backend/app/services/nutrition.py::calculate_target` construye un
     `engine_input` para `forja_nutrition.calculate_target` que ya no coincide con el
     esquema Pydantic del motor tras la subida a nutrition 0.2.0/engine 0.2.0 (`fat.max_pct_kcal`
     y `tolerances.fat_over_allowed` ya no existen o se llaman distinto en la versión nueva).
     Encaja con el aviso del arquitecto de que `f2/backend-align` todavía está alineando
     `Food`/nutrición al contrato 1.2.0; probablemente la misma rama toca este servicio.
   - Bloquea probar el resto de Nutrición desde el frontend (objetivo, plan semanal).

2. **Menor / no bloqueante — confirmar intención**: `PUT /profile` acepta
   `preferences: {}` (objeto vacío) sin error 422 explícito pero el guardado no se aplica tal
   cual — hay que enviar el objeto `preferences` completo (`theme`, `sounds`, `vibration`,
   `default_rest_s`) o falla más adelante con `422` genérico sin señalar qué campo falta. No
   se ha investigado a fondo (se resolvió enviando el objeto completo desde curl); si es
   intencional (reemplazo total, no *merge* parcial) convendría que el `422` señalara el
   campo que falta en vez de un error genérico, para que un cliente que sí manda un
   `preferences` parcial por error lo detecte rápido. Encontrado depurando manualmente con
   `curl`, no a través del frontend (el frontend siempre manda el objeto completo que lee de
   `GET /profile` primero).

## Peticiones a otros agentes

- **backend-api / f2-backend-align**: arreglar `POST /nutrition/targets/calculate` (bug 1
  arriba) — probablemente ya en alcance de esa rama dado el aviso de Food/nutrición 1.2.0.
- **backend-api**: confirmar si `PUT /profile.preferences` debe aceptar un *merge* parcial o
  si el objeto completo es el contrato pretendido (bug 2); si es pretendido, no hace falta
  cambio, pero un mensaje de `422` más preciso ayudaría a otros clientes.
- **qa-tests**: repetir el recorrido de Nutrición (generar plan, lista de la compra,
  intercambio de alimentos) en cuanto el bug 1 esté arreglado; probar el límite de tasa de
  `/auth/` en un entorno con nginx; revisar el mensaje de error de registro cerrado con una
  causa 403 distinta a «registro cerrado» (riesgo apuntado arriba).
- **devops-despliegue**: los comandos de arranque local de este handoff usan `docker run`
  suelto para Postgres y `uvicorn`/`vite` directos, no `docker compose`; si hay un
  `docker-compose.dev.yml` pensado para este flujo, indicarlo en el próximo handoff de
  arquitectura para no duplicar instrucciones.

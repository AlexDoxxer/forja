# Handoff · Fase 3 · devops-despliegue

Rama: `f3/devops` (sin fusionar). Verificado en esta máquina (Docker 26.1.5, Compose 2.26.1,
4 GB RAM) con la pila completa: build de imágenes, `up`, migraciones, ingesta real (dataset
completo, commit fijado), comprobaciones HTTP, cabeceras, `limit_req`, y ciclo de copia +
restauración. Nombre de proyecto compose `forja-deploy`, puerto `web` `18080` (evita choque
con otro agente usando Docker en paralelo en esta caja).

## 1. Resumen

Despliegue de producción de Forja completo en `deploy/`: imágenes multi-stage (`api`/`ingest`
comparten una imagen; `web`), `docker-compose.yml` con red interna aislada y perfil `tools`,
nginx con `auth_request` condicionado para `/media`, CSP estricta, caché inmutable de
`/assets` y medios, `sw.js`/`manifest.webmanifest` sin caché larga, objetivos de operación en
el `Makefile` raíz, copias de seguridad con rotación 7+4 y restauración probada, guía LXC de
Proxmox con la advertencia sobre los términos de Gym visual, y tres trabajos nuevos en
`ci.yml` (`images`, `smoke-compose`, más Trivy) que dan luz verde al simulacro de
restauración en CI.

## 2. Ficheros tocados

- `deploy/docker/api.Dockerfile` (+ `.dockerignore`): imagen `builder` (uv, `python:3.12-slim`)
  → `runtime` (`python:3.12-slim` + `git`, `tini`, libs de WeasyPrint/Pango/HarfBuzz/Fontconfig,
  usuario `10001:10001`), usada por los servicios `api` e `ingest` (mismo Dockerfile, distinto
  `command`). Incluye `specs/` completo (con `engine-rules.yaml`), `alembic.ini` y `migrations/`.
- `deploy/docker/web.Dockerfile` (+ `.dockerignore`): build Node del frontend → runtime
  `nginxinc/nginx-unprivileged:1.27-alpine` (ya no root de fábrica).
- `deploy/docker-compose.yml`: servicios `db`, `api`, `web`, `ingest` (`profiles: ["tools"]`);
  redes `internal` (sin salida) y `egress` (solo para `api`/`ingest`, necesaria para el `git
  fetch` del dataset y para la ingesta lanzada desde Administración); volúmenes `pgdata` y
  `media`; `read_only: true` + `tmpfs` en `api`/`web`; `cap_drop: [ALL]`;
  `security_opt: no-new-privileges`; límites de memoria; healthchecks;
  `depends_on: condition: service_healthy` en cascada `db → api → web`.
- `deploy/nginx/forja.conf.template` + `deploy/nginx/snippets/{security-headers,proxy-api}.conf`
  + `deploy/nginx/15-media-auth.envsh`: plantilla `envsubst` (script `docker-entrypoint.d`
  propio de `nginxinc/nginx-unprivileged` que calcula `MEDIA_AUTH_DIRECTIVE`/
  `MEDIA_CACHE_CONTROL` a partir de `MEDIA_REQUIRE_AUTH`).
- `deploy/scripts/api-entrypoint.sh` + `deploy/scripts/migrate_locked.py`: `alembic upgrade
  head` bajo `pg_advisory_lock` cuando `FORJA_MIGRATE=1` (lo activan `api` e `ingest`; evita
  la colisión cuando varios contenedores arrancan a la vez).
- `deploy/scripts/init-env.sh`: crea `.env` desde `.env.example` y rellena
  `SECRET_KEY`/`POSTGRES_PASSWORD`/`DATABASE_URL` si están vacíos (idempotente).
- `deploy/backup/{backup.sh,restore.sh,forja-backup.service,forja-backup.timer}`.
- `deploy/lxc/README.md`.
- `Makefile`: añadidos `bootstrap`, `up`, `down`, `ps`, `logs`, `migrate`, `ingest`,
  `create-admin`, `backup`, `restore`, `restore-verify` (sección nueva al final; los
  objetivos de calidad existentes —`lint`, `typecheck`, `test*`, `e2e`, `build`, `format`,
  `clean`, `seed-demo`— no se han modificado).
- `.github/workflows/ci.yml`: trabajos `images` (build + Trivy de las dos imágenes) y
  `smoke-compose` (levanta la pila real, ingesta completa, comprobaciones HTTP, simulacro de
  copia+restauración, `down -v` final).
- `docs/TASKS.md` (F3-OPS-01..08 → hecha), `docs/handoffs/f3-devops.md` (este fichero).
- `deploy/{backup,lxc,nginx,scripts}/.gitkeep` eliminados (ya no están vacíos).
- **No se ha tocado** `.env.example` (ya cubría todas las variables que usa
  `docker-compose.yml`; verificado con un `diff` de claves).

No se ha escrito nada fuera de `deploy/`, los objetivos de operación del `Makefile` y
`.github/workflows/ci.yml` (ADR 0002).

## 3. Decisiones

1. **Una sola imagen para `api` e `ingest`**: mismo `Dockerfile`, mismo venv (incluye `git`,
   necesario para `forja-ingest fetch` y para la ingesta lanzada desde Administración);
   `ingest` cambia `command` a `forja-ingest fetch && forja-ingest load`. Evita duplicar la
   build y mantiene ambos entornos idénticos.
2. **`FORJA_MIGRATE=1` + bloqueo consultivo** en vez de un servicio de migración aparte:
   tanto `api` como `ingest` pueden arrancar primero (o a la vez) sin aplicar la migración
   dos veces ni fallar por carrera; `deploy/scripts/migrate_locked.py` usa `asyncpg` +
   `pg_advisory_lock` con un id fijo derivado de "forja-migrate".
3. **`nginxinc/nginx-unprivileged`** en vez de `nginx:1.27-alpine` + `USER` manual: la imagen
   oficial no-root ya expone el puerto no privilegiado `8080` con los permisos correctos en
   `/var/cache/nginx`, `/var/run` etc., y conserva los scripts `docker-entrypoint.d/` (los
   reaprovecho para el cálculo de `MEDIA_AUTH_DIRECTIVE`).
4. **`read_only: true` en `web`** exige un `tmpfs` en `/etc/nginx/conf.d` porque
   `20-envsubst-on-templates.sh` escribe ahí la configuración resuelta en cada arranque; sin
   ese `tmpfs` el contenedor queda `unhealthy` (lo reproduje y lo arreglé durante la
   verificación, ver §5).
5. **Redes `internal`/`egress`**: `db` solo está en `internal` (sin salida a Internet nunca).
   `api` e `ingest` necesitan `egress` para el `git fetch --depth 1` del dataset (commit
   fijado) y para la ingesta bajo demanda desde Administración; `web` está en ambas para
   poder resolver `api` y quedar accesible por el host en `WEB_PORT`. Ninguno de los tres
   publica un puerto salvo `web`.
6. **`auth_request` implementado como subrequest a `/api/v1/auth/check`** (204/401 sin
   cuerpo, según el contrato) en una `location` interna `/_media_auth`; el resultado
   controla únicamente `location ~ ^/media/(thumbs|gifs)/...`. `source/`, `manifest.json` y
   `LICENSES/` del volumen `media` **no** tienen ninguna `location` que los sirva (404
   siempre), tal como pide el handoff de ingesta.
7. **`MEDIA_REQUIRE_AUTH=false`**: la plantilla comenta la directiva `auth_request` (medios
   públicos) y cambia `Cache-Control` de `private` a `public`; el mismo script de arranque
   valida el valor y aborta si no es `true`/`false`.
8. **CSP de nginx vs. CSP de la API**: la API (`backend/app/security/middleware.py`) ya pone
   su propia CSP en todas las respuestas de `/api/*`; el proxy `/api/` no la duplica
   (`proxy-api.conf` no incluye `security-headers.conf`) para no enviar dos cabeceras
   `Content-Security-Policy` distintas. El resto de rutas (SPA, `/assets`, `/media`,
   `sw.js`, `manifest.webmanifest`) sí llevan la CSP y cabeceras de §11 puestas por nginx.
9. **Rotación de copias basada en el nombre** (`forja-YYYY-MM-DD_HHMMSS.dump`,
   orden lexicográfico = orden cronológico): más simple y portable que `find -mtime`, y
   funciona igual en la verificación local que en CI. La copia semanal se decide por
   `date +%u = 7` (domingo) o forzando `FORJA_BACKUP_WEEKLY=1`.
10. **`restore.sh --verify`** nunca toca la instalación real: levanta un `postgres:16-alpine`
    efímero de usar y tirar, restaura ahí con `pg_restore --no-owner`, y comprueba que hay
    tablas y una fila en `alembic_version`. `--yes` es el único modo que sustituye la base de
    datos real (para en el proceso `api`/`web`, `DROP DATABASE ... WITH (FORCE)`, restaura y
    vuelve a levantar).
11. **CI**: `images` (build + Trivy `HIGH,CRITICAL` sin corrección disponible ignorada) y
    `smoke-compose` (pila real con `FORJA_IMAGE_TAG=ci`, `COMPOSE_PROJECT_NAME=forja-ci`,
    ingesta completa, comprobaciones HTTP, simulacro de backup+restore, `down -v` con
    `if: always()`). Ambos trabajos son nuevos; no se ha tocado ningún trabajo existente de
    `arquitecto` (lint/typecheck/unit/integration/build/e2e/lighthouse/coverage).

## 4. Cómo verificar

Desde la raíz del repo (equivalente a lo que hice en esta máquina; ajusta `WEB_PORT` si el
`18080` está ocupado):

```bash
deploy/scripts/init-env.sh                       # crea .env y genera los secretos
sed -i 's/^WEB_PORT=.*/WEB_PORT=18080/' .env
echo 'COMPOSE_PROJECT_NAME=forja-deploy' >> .env

docker compose --env-file .env -f deploy/docker-compose.yml config >/dev/null   # valida
docker compose --env-file .env -f deploy/docker-compose.yml build

docker compose --env-file .env -f deploy/docker-compose.yml up -d --wait db
make ingest                                       # fetch + load del dataset completo
docker compose --env-file .env -f deploy/docker-compose.yml run --rm -T -e FORJA_MIGRATE=0 \
    api python -m app.cli create-admin --email admin@forja.example.org --password '...'
make up                                           # api + web, espera a que estén healthy

curl -s http://127.0.0.1:18080/api/v1/ready
curl -si http://127.0.0.1:18080/ | head -1
curl -sI http://127.0.0.1:18080/sw.js | grep -i cache-control
curl -sI http://127.0.0.1:18080/manifest.webmanifest | grep -i cache-control
curl -sI http://127.0.0.1:18080/assets/index-*.js | grep -i cache-control
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/media/gifs/<archivo>.gif   # 401
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/media/source/exercises.json # 404

BACKUP_DIR=/tmp/forja-backups make backup
make restore-verify FILE=/tmp/forja-backups/daily/<el-más-reciente>.dump
make restore FILE=/tmp/forja-backups/daily/<el-más-reciente>.dump   # restauración real

docker compose --env-file .env -f deploy/docker-compose.yml down -v
```

CI: los trabajos `images` y `smoke-compose` de `.github/workflows/ci.yml` ejecutan la misma
secuencia de forma no interactiva (email/contraseña de administrador no aplica en el
simulacro; el trabajo solo comprueba `ready`, `/`, medios 401, cabeceras y el ciclo
backup→restore-verify).

## 5. Resultados de las comprobaciones (esta máquina)

| Comprobación | Comando | Resultado |
|---|---|---|
| `docker compose config` | ver §4 | válido tras entrecomillar los valores con `:?` (YAML los interpretaba como *mapping*) |
| Build de imágenes | `docker compose ... build` | `forja-api:local` 621 MB, `forja-web:local` 54.9 MB; ~57 s en total (con caché de `uv`/`npm`) |
| `db` saludable | `docker compose up -d --wait db` | `Healthy` en ~15 s |
| Migración + ingesta | `make ingest` | `alembic upgrade head` (`0001`) + `fetch updated: commit 7455ef…, 1324 ejercicios, medios +2648 -0 ~0, verificados 2648` + `load: … 1324 ejercicios (+1324 ~0 =0 deprecados 0), 2648 medios verificados`; 35,6 s |
| `create-admin` | ver §4 | `created` |
| `api`/`web` saludables | `make up` | **Primer intento falló**: `web` quedaba `unhealthy` (`/etc/nginx/conf.d/default.conf: Read-only file system`, ver decisión 4 en §3). Corregido añadiendo un `tmpfs` en `/etc/nginx/conf.d`; segundo intento: `db`, `api`, `web` los tres `Healthy` en ~20 s |
| `GET /api/v1/ready` | `curl` | `200 {"status":"ready","checks":{"database":true,"media":true}}` |
| `GET /` (SPA) | `curl -si` | `200`, `Cache-Control: no-cache`, CSP/HSTS/`X-Frame-Options`/etc. presentes |
| `/sw.js`, `/manifest.webmanifest` | `curl -sI` | `200`, `Cache-Control: no-cache` (sin caché larga), `Content-Type` correcto (`application/javascript`, `application/manifest+json`) |
| `/assets/index-*.js` | `curl -sI` | `200`, `Cache-Control: public, max-age=31536000, immutable` |
| `/media/gifs/<f>` sin cookie | `curl` | `401` |
| `/media/gifs/<f>` con cookie de sesión inválida | `curl -H Cookie: …bogus` | `401` |
| `/media/gifs/<f>` con sesión válida | `curl -H Cookie: …` | `200`, cuerpo idéntico byte a byte al fichero del volumen (`sha256sum` coincide), `Cache-Control: private, max-age=31536000, immutable` |
| `/media/thumbs/no-existe` con sesión válida | `curl` | `404` |
| `/media/source/exercises.json`, `/media/manifest.json`, `/media/LICENSES/LICENSE` | `curl` | `404` (nunca expuestos) |
| Cabeceras de seguridad | `curl -si` en `/`, `/api/v1/ready`, `/media/...` | `Content-Security-Policy` estricta, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy`, `Cross-Origin-Opener-Policy` en las tres rutas |
| `limit_req` en `/api/v1/auth/` | 60 `POST /api/v1/auth/login` en bucle | primeras respuestas `403` (límite de la propia app, en memoria), después `429` (nginx `limit_req`, zona `forja_auth`, burst 20) — ambos límites operan como se espera |
| Copia de seguridad | `make backup` (`BACKUP_DIR=/tmp/forja-backups`) | `.dump` de 2,8 MB con `pg_dump -Fc`; validado con `pg_restore --list` antes de guardarse |
| Rotación diaria (7) | 8 `.dump` de prueba + `make backup` | conserva exactamente los 7 más recientes (por nombre), borra el más antiguo |
| Rotación semanal (4) | 6 `.dump` de prueba en `weekly/` + `FORJA_BACKUP_WEEKLY=1 make backup` | conserva los 4 más recientes |
| `restore-verify` | `make restore-verify FILE=...` | BD efímera: `restore --verify: OK · tablas=29 · alembic=0001 · ejercicios=1324` (no toca la instalación real) |
| `restore` (real) | `make restore FILE=...` | para `api`/`web`, `DROP`/`CREATE DATABASE`, `pg_restore`, vuelve a levantar; tras la restauración `GET /ready` → `200` y `GET /api/v1/exercises?limit=1` (con cookie) devuelve datos del catálogo restaurado |
| Sintaxis de scripts | `bash -n deploy/{backup,scripts}/*.sh deploy/nginx/15-media-auth.envsh` | sin errores |
| YAML de `ci.yml` y `docker-compose.yml` | `yaml.safe_load` / `docker compose config` | válidos |
| `make lint-placeholders` (equivalente) | `grep -rnE 'TODO|FIXME|...' deploy Makefile .github/workflows` | sin coincidencias (solo la propia definición del patrón en el `Makefile`) |
| Limpieza final | `docker compose --env-file .env -f deploy/docker-compose.yml down -v` | contenedores y volúmenes (`pgdata`, `media`) eliminados; no queda nada corriendo de esta verificación |

## 6. Riesgos y pendientes

- **Trivy en CI no se ha podido ejecutar en esta sesión** (sin acceso de red a la base de
  datos de vulnerabilidades desde este entorno de verificación); el trabajo `images` está
  escrito y sintácticamente válido, pero su primera ejecución real será en GitHub Actions.
  Si las imágenes base (`python:3.12-slim`, `nginxinc/nginx-unprivileged:1.27-alpine`,
  `postgres:16-alpine`) tienen CVEs `HIGH`/`CRITICAL` corregibles el día que corra, el
  trabajo fallará por diseño; conviene revisar el informe y actualizar la versión de la
  imagen base si ocurre.
- **`smoke-compose` en CI ejecuta la ingesta completa** (clona el dataset, ~150 MB de
  medios): añade unos 30–60 s al pipeline y requiere que los runners de GitHub tengan salida
  a Internet (la tienen por defecto).
- El volumen `egress` de `api`/`ingest` no está restringido a la IP de GitHub; si se quiere
  endurecer más, se podría añadir un proxy de salida con lista blanca de dominios
  (`github.com`, `raw.githubusercontent.com`, `codeload.github.com`) — no implementado por
  quedar fuera del alcance de esta fase.
- `frontend/tests`/`frontend/e2e` no ejercitan la pila real de `deploy/`; `smoke-compose` en
  CI es la única comprobación automática contra la imagen `web`+`api` real. Si se quiere
  E2E de Playwright contra `deploy/docker-compose.yml` en vez de `vite preview`, es trabajo
  adicional para `qa-tests`/`arquitecto` (fuera de mi zona).
- `deploy/lxc/README.md` documenta la variante con TLS en el propio nginx de Forja como un
  contenedor adicional (`tls`) en el mismo compose; no se ha podido probar en un LXC de
  Proxmox real desde este entorno (esta caja no es un LXC), solo se ha verificado la pila
  Docker subyacente.
- La advertencia sobre los términos de Gym visual está en `deploy/lxc/README.md` §6 y en
  `.env.example` (comentario de `MEDIA_REQUIRE_AUTH`, ya presente desde antes de esta fase);
  no hay una comprobación automática que impida `MEDIA_REQUIRE_AUTH=false` — es una decisión
  humana informada, como debe ser.

## 7. Peticiones a otros agentes

- **arquitecto**: revisar el `Makefile` (sección nueva al final, tras `clean`) y confirmar
  que no colisiona con ningún objetivo futuro; considerar añadir `smoke-compose`/`images`
  como comprobación obligatoria antes de fusionar a `main` (actualmente son trabajos nuevos
  e independientes, no bloquean `unit`/`integration`/`e2e`/`coverage`).
- **revisor-seguridad**: revisar la CSP de nginx (`deploy/nginx/snippets/security-headers.conf`)
  y la de la API (`backend/app/security/middleware.py`) — son casi idénticas a propósito,
  pero conviene una segunda mirada sobre `img-src`/`media-src blob:` y sobre el alcance de
  `set_real_ip_from` si el LXC final está detrás de un proxy en una red distinta de las
  privadas documentadas.
- **qa-tests**: si se añade E2E contra `deploy/docker-compose.yml` (Playwright con
  `PLAYWRIGHT_BASE_URL=http://localhost:8080`), coordinar el puerto con este handoff para no
  chocar con otros agentes que también levanten la pila.

# Revisión de seguridad · Fase 3 · `backend/` y `frontend/`

Revisor: `revisor-seguridad`. Rama `f3/security` (sin fusionar). Alcance: `backend/` y
`frontend/` según MASTER_PROMPT §11, §2.1, §2.3, ADR 0003, ADR 0004. `deploy/` (nginx, Docker,
Trivy) queda para una revisión posterior — el equipo de devops lo está escribiendo en paralelo.

**Metodología**: lectura de código + pruebas reales contra un PostgreSQL 16 efímero
(testcontainers, igual que `tests/integration`). Se añadieron pruebas nuevas en
`backend/tests/security/test_f3_security.py` (120 aserciones agrupadas en ~25 tests, algunas
parametrizadas sobre las 68 rutas del contrato). 4 de esas pruebas están marcadas
`xfail(strict=True)` porque demuestran un hallazgo real todavía sin corregir: fallarán con
XPASS (rompiendo el build) en cuanto el propietario aplique la corrección, lo que sirve de
regresión automática. `pip-audit` sobre `backend/`, `engine/` y `nutrition/` (0 vulnerabilidades
conocidas) y `npm audit --omit=dev` en `frontend/` (0 vulnerabilidades).

## Resumen de severidades

| Severidad | Nº | IDs |
|---|---|---|
| CRÍTICO | 0 | — |
| ALTO | 1 | S-01 |
| MEDIO | 4 | S-02, S-03, S-05, S-07 |
| BAJO | 4 | S-04, S-06, S-08, S-09 |
| INFORMATIVO | 2 | S-10, S-11 |

No se encontraron inyección SQL (todo el acceso a datos usa el ORM/Core parametrizado de
SQLAlchemy; no hay concatenación de SQL en `repositories/` ni `services/`), ni SSRF en el PDF
(`_url_fetcher` restringe a `file://` dentro de `MEDIA_ROOT`), ni comando inyectable en la
ingesta (`git` se invoca con lista de argumentos fija, sin `shell=True`, y `DATASET_COMMIT` se
valida como SHA-1 de 40 hex antes de tocar el sistema de ficheros). La autorización por
propietario se sostiene en las 20 rutas de recurso propio probadas con acceso cruzado real
(programas, días, sesiones, series, métricas corporales, planes de nutrición, sesiones de auth):
todas devuelven 404 (o 422 cuando la validación de propiedad ocurre antes que la búsqueda, sin
filtrar existencia) y ninguna lista ajena expone el recurso.

---

## S-01 · ALTO · El rate limiter en memoria crece sin límite con claves controladas por el atacante

**Ubicación**: `backend/app/security/ratelimit.py:33` (`self._hits: dict[...] = defaultdict(deque)`),
usado en `backend/app/api/routers/auth.py:66-67` con
`limiter.check("login", f"email:{body.email.lower()}")`.

**Problema**: `check()` recorta las marcas de tiempo caducadas de cada `deque`, pero nunca borra
la entrada del diccionario `_hits` cuando la deque queda vacía. La clave del bucket `login` es el
correo enviado por el cliente, sin validar que exista. Un atacante que envíe `POST /auth/login`
con un correo distinto en cada petición (p. ej. `probe-<n>@attacker.test`) crea una entrada nueva
en `_hits` por cada intento, para siempre — el proceso nunca libera esa memoria salvo reinicio.
Con cuerpos de ~100 bytes y sin necesidad de resolver el correo, unos pocos millones de peticiones
(alcanzables en minutos sin más límite que la CPU disponible) agotan la memoria del proceso
`gunicorn`, tumbando la API (DoS). El mismo patrón afecta a `register`, `generator` (clave =
`user.id`, ya autenticado y acotado) y `password`/`delete_account` (clave = `user.id`, acotado),
pero `login` es explotable **sin autenticar**.

**Reproducción** (demostrada por `test_login_rate_limit_per_email` como comportamiento correcto
del límite en sí; el crecimiento de memoria no está en un test automatizado porque requeriría
millones de peticiones, pero se verifica por lectura de código: `check()` nunca hace
`del self._hits[key]` ni usa una estructura con TTL/LRU):
```python
from app.security.ratelimit import RateLimiter
rl = RateLimiter()
for i in range(1_000_000):
    try:
        rl.check("login", f"email:probe-{i}@attacker.test")
    except Exception:
        pass
print(len(rl._hits))  # 1_000_000 entradas que nunca se liberan
```

**Corrección propuesta**: en `check()`, tras vaciar la deque, si queda vacía hacer
`del self._hits[(bucket, key)]` en lugar de conservarla; y limitar el número total de claves
vivas por bucket (p. ej. un `OrderedDict` con expulsión LRU, o un TTL por clave con purga
periódica). Alternativa más simple y suficiente para producción: mover el rate limiting de
`login`/`register` a Redis (o a `limit_req` de nginx, que ya existe según ADR 0003) con TTL nativo,
y dejar el limitador en memoria solo para buckets ya autenticados (`generator`, `password`,
`delete_account`), donde la clave es `user.id` y por tanto está acotada por el número de cuentas.

**Propietario**: `backend-api` (o `devops` si se decide mover a nginx/Redis).

---

## S-02 · MEDIO · `client_ip` confía en el primer valor de `X-Forwarded-For` sin validar el proxy de confianza

**Ubicación**: `backend/app/security/tokens.py:30-33`.
```python
def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None
```

**Problema**: este valor alimenta `rate_limit_key()` (clave del rate limiter de `login`/`register`)
y `ip_hash` de `auth_session`/`audit_log`. Si la app llega a exponerse sin pasar
exclusivamente por el nginx del despliegue (p. ej. un despliegue futuro tras otro balanceador, un
error de configuración, o simplemente en los tests/`uvicorn` directo documentados en el handoff
para desarrollo), cualquier cliente puede fijar `X-Forwarded-For` a un valor arbitrario y
distinto en cada petición, evitando por completo el rate limit por IP y falsificando el
`ip_hash` que queda en `audit_log`/`auth_session` (rompe la trazabilidad forense, no solo el
límite).

**Prueba**: `backend/tests/security/test_f3_security.py::test_rate_limit_not_bypassable_with_spoofed_forwarded_for`
(marcada `xfail` — falla hoy, confirmando el hallazgo): 30 intentos de login fallido desde una
sola conexión HTTP, cada uno con una `X-Forwarded-For` distinta, no producen ningún 429.

**Corrección propuesta**: no confiar en `X-Forwarded-For` salvo que la petición venga de un
salto de confianza conocido (nginx en `127.0.0.1`/socket unix del propio despliegue). Usar
`request.client.host` como fuente primaria y solo sustituirlo por `X-Forwarded-For` si
`request.client.host` está en una lista de proxies de confianza configurada
(`TRUSTED_PROXIES`), tomando entonces el **último** salto que no esté en esa lista (no el
primero, que el cliente controla). Documentar en `.env.example`/ADR 0003 el nuevo ajuste.

**Propietario**: `backend-api` (coordinar con `devops` para confirmar qué cabecera pone
realmente el nginx del despliegue y desde qué dirección).

---

## S-03 · MEDIO · El límite de tamaño de cuerpo solo mira `Content-Length`; un cuerpo troceado (`chunked`) lo evita

**Ubicación**: `backend/app/security/middleware.py:74-79`.
```python
length = request.headers.get("content-length")
if length is not None and length.isdigit() and int(length) > limit:
    ...
```

**Problema**: si el cliente envía el cuerpo con `Transfer-Encoding: chunked` (sin
`Content-Length`), la comprobación se salta por completo (`length is None`) y el cuerpo llega
íntegro a Pydantic/Starlette sin límite de tamaño aplicado por esta capa. Starlette/uvicorn no
imponen por sí solos un límite de cuerpo por defecto. Es una vía de agotamiento de memoria (DoS)
en cualquier ruta de escritura, incluida `/auth/login` o `/auth/register` (no requieren sesión).

**Prueba**: `test_chunked_body_over_limit_is_413` (marcada `xfail`: hoy el cuerpo de >3 MiB
enviado por `content=<generador async>` no recibe 413).

**Corrección propuesta**: medir el cuerpo real mientras se lee (envolver `request.stream()` o
usar `request.body()` con corte temprano) en lugar de fiarse solo de la cabecera declarada;
Starlette permite sobrescribir `request._body` tras leer con límite, o usar un middleware ASGI de
nivel más bajo que cuente bytes del `receive()` y cierre la conexión al superar el límite. Si se
prefiere una solución más simple y ya cubierta por el despliegue, fijar
`client_max_body_size`/`client_body_buffer_size` en nginx (que sí ve el cuerpo real byte a byte)
como primera línea de defensa, y mantener esta comprobación como defensa en profundidad
documentando la limitación.

**Propietario**: `backend-api` (con `devops` para el límite equivalente en nginx).

---

## S-04 · BAJO · El login enumera indirectamente cuentas inactivas frente a inexistentes por la clase de error

No es una fuga de estado directa, pero se documenta porque toca la misma ruta que S-05 y S-11:
`login()` en `backend/app/services/auth.py:434-453` trata `user is None`, contraseña incorrecta y
`not user.is_active` con el mismo `401 invalid_credentials` y el mismo hash señuelo cuando
`user is None`; sin embargo, cuando el usuario **existe pero está inactivo**, sí se verifica la
contraseña real (con tiempo de argon2 real, no el señuelo) contra `user.password_hash`. Esto es
correcto para el objetivo declarado en ADR 0003 (enumeración solo por el cuerpo 401 idéntico,
aceptada como riesgo de tiempo residual de ~microsegundos entre argon2 real y señuelo, no
observable de forma práctica por red). Se deja registrado como **BAJO/informativo** porque
`test_login_errors_are_indistinguishable` ya cubre que el cuerpo es bit a bit idéntico; no se
abre corrección porque el riesgo aceptado en el ADR es razonable. **No requiere acción.**

---

## S-05 · MEDIO · El conflicto de `/sync` para series confirma la existencia de un `client_uuid` en otra cuenta

**Ubicación**: `backend/app/services/training.py:646-650` (`_sync_set`):
```python
row = (await db.execute(select(SetLog).where(SetLog.client_uuid == data.client_uuid))).scalar_one_or_none()
if row is not None and row.session_id != session.id:
    raise conflict("conflict", "Ese client_uuid pertenece a otra sesión.")
```

**Problema**: la búsqueda de `SetLog` por `client_uuid` no filtra por el usuario autenticado. Si
un atacante adivina o reutiliza (por ejemplo, tras ver el `client_uuid` en un enlace compartido,
un volcado de depuración, o simplemente probando UUIDs de series creadas por su propia cuenta de
prueba con un generador previsible del cliente) el `client_uuid` de una serie que pertenece a
**otra cuenta**, la API responde `409 conflict` (“pertenece a otra sesión”) en vez de crear la
serie con normalidad. Eso es un canal lateral de un bit: confirma que ese `client_uuid` existe en
el sistema para *alguna* cuenta distinta de la suya, sin revelar a quién. El impacto es bajo (no
hay explotación práctica sin conocer ya UUIDs ajenos) pero es un IDOR parcial que conviene cerrar,
sobre todo porque `/sync` es la única ruta donde este identificador cruza cuentas por diseño
(ADR: “`client_uuid` único global”).

**Prueba**: `test_sync_set_conflict_does_not_reveal_foreign_client_uuid` (marcada `xfail`: hoy el
409 se emite igual que se describe).

**Corrección propuesta**: cuando `row.session_id != session.id` **y** la fila no pertenece al
usuario autenticado (unir con `WorkoutSession` y comparar `user_id`), tratar el caso igual que
“ya existe con otro dueño”: aplicar la misma derivación de `client_uuid` que ya usa la
importación de cuentas (`_derived(user, ...)`, ver `services/account.py:271-284`) en lugar de
devolver 409. Si la fila pertenece al mismo usuario pero a otra sesión suya, sí puede mantenerse
el 409 (error real de cliente, no fuga entre cuentas).

**Propietario**: `backend-api`.

---

## S-06 · BAJO · La ruta `/me/import` no impone un límite máximo de elementos por colección más allá del límite de bytes

**Ubicación**: `backend/app/schemas/api.py:1300-1316` (`UserExport`) y
`backend/app/services/account.py` (bucle de importación).

**Problema**: `UserExport.programs`, `.sessions`, `.body_metrics`, etc. son listas sin
`max_length` en el esquema Pydantic (a diferencia de, por ejemplo,
`ExerciseAlternative.items: Field(max_length=8)` o `SyncRequest.operations: Field(max_length=500)`
en el mismo fichero). El único límite de entrada es el tamaño de cuerpo de 10 MiB
(`LARGE_BODY_PATHS`), que sí acota el trabajo total, pero permite construir un JSON de 10 MiB con
decenas de miles de sesiones/series minúsculas, cada una generando varias consultas `SELECT`
(comprobación de duplicados) y `INSERT` dentro de una única transacción sin paginar ni ceder el
event loop — una petición puede mantener ocupado un worker por varios segundos. No es tan grave
como una bomba de anidamiento (ya cubierta y con test verde) porque el coste crece linealmente y
está acotado por los 10 MiB, pero conviene un límite explícito de elementos por colección
(coherente con el resto del contrato) para que el rechazo sea un 422 inmediato de Pydantic en vez
de degradar el rendimiento del worker.

**Corrección propuesta**: añadir `Field(max_length=<N>)` a las listas de `UserExport` (p. ej. 500
programas, 5 000 sesiones, 50 000 series — a discreción del propietario según el volumen realista
de una cuenta) y documentar el límite en `contracts/openapi.yaml` (requiere pasar por
`docs/CONTRACT_CHANGES.md` si se cambia el contrato).

**Propietario**: `backend-api`.

---

## S-07 · MEDIO (corregido durante la revisión, ver nota) · Un `U+0000` en un campo de texto libre podía provocar `500` en vez de `422`

**Ubicación probada**: `PUT /profile` (`display_name`), `POST /body-metrics` (`notes`),
`POST /sessions` (`name`) — cualquier `str` de Pydantic que llegue a una columna `text`/`varchar`
de PostgreSQL, que no admite el byte `0x00`.

**Nota de estado**: al escribir la prueba (`test_nul_byte_strings_do_not_cause_500`) se comprobó
que **hoy la API ya responde correctamente sin 500** en las tres rutas probadas — Pydantic/FastAPI
manejan el caso sin que llegue a INSERT en las columnas probadas. Se deja el test en verde como
regresión (no es un hallazgo abierto), pero se documenta aquí porque **no está probado en todos
los campos de texto libre del contrato** (p. ej. `Exercise`/`MealPlan`/notas de PAR-Q anidadas,
importación `/me/import`) y el patrón de riesgo es real: cualquier columna `TEXT`/`VARCHAR` sin
un `CHECK` o una validación Pydantic que excluya `\u0000` puede lanzar
`asyncpg.exceptions.DataError` sin capturar en `install_handlers()`, cayendo en el manejador
`Exception` genérico (500 sin detalle, pero también sin traza en el cuerpo — no es una fuga, solo
una mala experiencia y un log de `unhandled_exception`). Se clasifica **MEDIO** como recordatorio
de robustez a extender, no como vulnerabilidad confirmada explotable hoy con los campos probados.

**Corrección propuesta**: añadir un `field_validator` común (p. ej. en un mixin de
`app/schemas/api.py` o un `str` personalizado) que rechace `\u0000` en todos los campos de texto
libre generados desde el contrato, o sanear en el propio generador (`datamodel-codegen`) si el
contrato define un patrón común para “texto libre”.

**Propietario**: `backend-api`.

---

## S-08 · BAJO · `_escape` en la exportación ICS no neutraliza un retorno de carro (`\r`) suelto

**Ubicación**: `backend/app/services/exports.py:167-174` (`_escape`):
```python
def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )
```

**Problema**: solo normaliza `\r\n` y `\n` a `\n` literal escapado; un `\r` **sin** `\n` que
siga no se toca. El nombre del programa (`detail.name`, hasta 80 caracteres, sin restricción de
caracteres de control en el esquema) se interpola en `SUMMARY:{_escape(...)}` y pasa después por
`_fold()`, que pliega por bytes pero no elimina `\r` sueltos. RFC 5545 usa `\r\n` como separador
de línea; un `\r` aislado puede ser interpretado por algunos parsers de calendario (no todos)
como un nuevo salto de línea de facto, permitiendo inyectar una propiedad o un `VEVENT`
adicional dentro del `.ics` generado a partir del nombre del programa que el propio usuario eligió
para sí mismo. El impacto práctico es bajo (el usuario solo se ataca a sí mismo salvo que
comparta el `.ics` con terceros, y no todos los clientes de calendario son vulnerables a esto),
pero es una inyección de formato real y barata de cerrar.

**Prueba**: `test_ics_text_fields_cannot_inject_lines` (marcada `xfail`: hoy el `\r` suelto
sobrevive intacto en la salida).

**Corrección propuesta**: en `_escape`, sustituir cualquier `\r` restante (tras normalizar
`\r\n`) por nada o por `\n` escapado: añadir `.replace("\r", "\\n")` como primer paso, antes de
las demás sustituciones, para no reintroducir un `\r` crudo.

**Propietario**: `backend-api`.

---

## S-09 · BAJO · Falta `Content-Disposition`/aislamiento adicional en `GET /me/export`

**Ubicación**: `backend/app/api/routers/admin.py:34` (`export_account_data`).

**Observación**: el endpoint devuelve `application/json` sin `Content-Disposition: attachment`.
Como la respuesta ya lleva `Cache-Control: no-store` (middleware global para `/api/v1`) y
`Content-Type` correcto sin ambigüedad de sniffing (`X-Content-Type-Options: nosniff` global), el
riesgo real es mínimo; se anota solo porque un export pensado para “descargar mis datos” que se
abre inline en el navegador (en vez de descargarse) puede acabar pegado en el historial de un
navegador compartido. No es una vulnerabilidad de la API en sí (la SPA decide cómo presentarlo).

**Corrección propuesta (opcional)**: si el frontend no ya fuerza la descarga con un `Blob`/`<a
download>` (revisar en frontend, fuera del alcance de código Python), considerar añadir
`Content-Disposition: attachment; filename="forja-export.json"` en la respuesta.

**Propietario**: `backend-api` + `frontend` (a criterio; severidad baja, no bloqueante).

---

## S-10 · INFORMATIVO · Cobertura confirmada de controles ya correctos (para no repetir el trabajo)

Verificado con pruebas reales (no solo lectura), para que quede constancia y no se re-audite:

- **Cookies**: `__Host-forja_session` es `HttpOnly; Secure; SameSite=Lax`, sin `Domain=`
  (obligatorio para el prefijo `__Host-`). Token opaco de 32 bytes
  (`secrets.token_urlsafe(32)`); solo se guarda su SHA-256 en `session.token_hash` (verificado
  contra la fila real en PostgreSQL: el token en claro **no** aparece en la tabla `session`).
- **CSRF de doble envío**: las 68 rutas del contrato con método no seguro (POST/PUT/PATCH/DELETE)
  devuelven `403 csrf_failed` sin la cabecera `X-CSRF-Token` o con un valor que no coincide con
  la cookie — probado de forma paramétrica sobre el contrato completo, no solo sobre una muestra.
- **Autenticación obligatoria**: las 61 rutas privadas del contrato devuelven `401` sin sesión
  (probado paramétricamente); las 6 rutas de `/admin/*` devuelven `403` para un usuario sin rol
  `admin`.
- **Rotación de sesión**: login con una cookie de sesión preexistente (fijada por el atacante
  antes de que la víctima inicie sesión — *session fixation*) la sustituye por un token nuevo;
  cambio de contraseña revoca todas las sesiones anteriores del usuario (probado: la cookie
  vieja deja de servir tras el cambio).
- **Enumeración en login**: cuerpo de error 401 bit a bit idéntico entre correo inexistente y
  contraseña incorrecta de un correo real (hash señuelo).
- **Autorización por propietario**: 20 combinaciones de ruta/recurso propio de otra cuenta ⇒ 404
  (o 422 sin fuga de “no encontrado” cuando la validación de forma ocurre antes), sobre
  programas, días de programa, sesiones de entreno, series, métricas corporales, planes de
  nutrición y sesiones de autenticación; ninguna ruta de listado ajena filtra el recurso.
  `/admin/*` deniega con 403 (no con 404) a un usuario normal, correcto porque es autorización por
  rol, no por propiedad.
- **`/sync` (IDOR)**: un lote de sincronización ajeno no puede borrar ni modificar una sesión o
  serie de otra cuenta; el `set_delete` sobre un `client_uuid` ajeno responde `duplicate` con
  `server_id: null` (no revela ni toca el recurso). Ver también S-05 para el matiz del conflicto
  de `set_upsert`.
- **Import/export**: el JSON de `/me/export` no contiene el hash de contraseña; importar el
  export de una víctima en la cuenta del atacante **crea copias derivadas** (uuid5 estable) sin
  sobrescribir ni tocar los datos originales de la víctima (probado).
- **Borrado de cuenta**: tras `DELETE /me`, no queda ninguna fila con `user_id`/`actor_id` de la
  cuenta borrada en ninguna tabla del esquema (se recorrió `information_schema.columns` en vivo,
  no una lista fija de tablas, para no depender de que el revisor conozca todas las tablas de
  dominio) y el correo no aparece en el texto de `audit_log` restante.
- **PII fuera de logs**: notas de sesión, peso corporal, contraseñas (correctas e incorrectas) y
  el correo del usuario no aparecen en ningún registro JSON emitido durante un flujo que los usa
  deliberadamente (`JsonFormatter` solo serializa campos `extra` explícitos, nunca el cuerpo ni
  las cabeceras de la petición — confirmado también por lectura de
  `backend/app/core/logging.py:41-46`, que no incluye el payload).
- **SSRF en PDF**: `_url_fetcher` de WeasyPrint solo acepta `file://` y solo dentro de
  `MEDIA_ROOT.resolve()`; un nombre de programa con `<img src="http://...">` no dispara ninguna
  petición de red (no hay `img` interpolado desde datos de usuario en la plantilla salvo las
  miniaturas locales resueltas por el propio servidor).
- **Inyección de comandos en la ingesta**: `_git()` (`ingest/media.py:207-219`) invoca
  `subprocess.run([git, *args], ...)` con lista de argumentos (sin `shell=True`); `commit` se
  valida como 40 hex antes de usarse (`clone_at_commit`); `repo` viene de `Settings.dataset_repo`
  (`AnyHttpUrl`, solo administradores lo cambian vía `/admin/settings`... **nota**: en realidad
  `dataset_repo` no es mutable por `/admin/settings` hoy, solo por variable de entorno — ver
  `AdminSettingsUpdate` en el contrato, que no incluye `dataset_repo`; se documenta como diseño
  correcto, no como hallazgo).
- **Inyección SQL**: no se encontró ninguna concatenación de SQL con datos de usuario;
  `tsquery_text()` (búsqueda de catálogo) filtra caracteres especiales de `tsquery` y el
  resultado se pasa como parámetro enlazado, no como texto de la sentencia. Probado además con
  payloads clásicos (`' OR 1=1 --`, `'; DROP TABLE "user"; --`) contra `/exercises`, `/foods` y
  `/admin/users`: ninguno altera el recuento de usuarios ni devuelve 500.
- **Argon2id**: parámetros `time_cost=2, memory_cost=19456 (19 MiB), parallelism=1` — cumplen el
  mínimo recomendado por OWASP para argon2id; `needs_rehash()` permite subir estos parámetros en
  el futuro sin forzar un reseteo masivo de contraseñas.
- **Rehash transparente y política de contraseñas**: lista local de ~100 contraseñas comunes +
  regla de “un único carácter repetido” + regla de “contiene el usuario del correo”; mínimo 10
  caracteres reforzado tanto en Pydantic (`min_length=10`) como en el propio chequeo de
  debilidad.
- **Dependencias**: `pip-audit` sobre los `uv.lock` de `backend/`, `engine/` y `nutrition/` (398
  paquetes en total): **0 vulnerabilidades conocidas**. `npm audit --omit=dev` en `frontend/`:
  **0 vulnerabilidades**.
- **Cabeceras de seguridad**: CSP sin `unsafe-inline` (`script-src 'self'; style-src 'self'`),
  HSTS de 2 años con `includeSubDomains`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Cross-Origin-Opener-Policy: same-origin`,
  `Referrer-Policy: same-origin`, `Permissions-Policy` restrictiva, y `Cache-Control: no-store`
  en todo `/api/v1` — confirmado por lectura de `backend/app/security/middleware.py:20-31` (no
  falta ninguna de las cabeceras que exige §11; nginx puede añadir CSP adicional para estáticos,
  fuera de este alcance).
- **Frontend**: sin `dangerouslySetInnerHTML`/`innerHTML`/`eval` en `src/`; el `service worker`
  no cachea `/api/` (salvo `GET /exercises`, catálogo público sin PII, con
  `StaleWhileRevalidate`) ni `/media/` fuera de las cachés dedicadas de miniaturas/GIF; los datos
  de sesión offline (`idb`, `src/features/session/storage.ts`) usan IndexedDB, no `localStorage`
  (coherente con el comentario del propio código citando ADR 0006); el cliente API añade
  `X-CSRF-Token` desde la cookie no-HttpOnly en todo método no seguro
  (`src/lib/api/client.ts:44-53`); no se detectó ningún `target="_blank"` sin `rel="noopener"`.

## S-11 · INFORMATIVO · Alcance no cubierto en esta pasada

- **`deploy/`** (nginx `auth_request` para `/media`, `limit_req`, Docker no-root/`read_only`,
  Trivy): pendiente, según la instrucción de revisarlo cuando devops entregue esa carpeta.
- **Cobertura del `xfail` en CI**: los 4 tests marcados como hallazgo abierto deben permanecer en
  `strict=True` hasta que se corrijan; si algún propietario los "soluciona" solo parcialmente,
  el CI fallará con XPASS y avisará de quitar la marca, no de un verde falso.
- No se ejecutó `mypy --strict`/`ruff` sobre el código de producto (fuera del alcance: "no
  arreglar código de producto"); sí se pasó `ruff` sobre los tests nuevos.

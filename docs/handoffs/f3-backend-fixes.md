# Handoff · Fase 3 · backend-api — correcciones de seguridad y bug de nutrición

Rama: `f3/backend-fixes` (sin fusionar). Alcance: solo `backend/`, según ADR 0002. Aplica los
hallazgos S-01 a S-09 de `docs/reviews/f3-security.md` (propietario `backend-api`) y el bug de
`POST /nutrition/targets/calculate` documentado en `docs/handoffs/f2-frontend-integration.md`.

## Resumen

De los 9 hallazgos asignados, **8 quedan corregidos y verificados con test**; **S-07 no requería
corrección** (la propia revisión lo deja documentado como robustez a extender, no como
vulnerabilidad confirmada, y ya estaba en verde). El bug de nutrición del frontend **ya estaba
corregido en el código actual** (por `f2/backend-align` + nutrition 0.2.1, mergeados en `main`
antes que la rama de integración de frontend) — se añadió una regresión explícita que reproduce
literalmente el reporte (`POST` con cuerpo `{}`) para que no vuelva a pasar inadvertido.

| ID | Severidad | Estado | Evidencia |
|---|---|---|---|
| Bug nutrición | — | **Ya corregido** (upstream); regresión añadida | `test_target_plan_swap_and_shopping_list` ahora incluye `POST .../calculate` con `json={}` → 200 |
| S-01 | ALTO | **Corregido** | `RateLimiter` con expulsión LRU acotada por bucket; sin test `xfail` (la propia revisión indica que no es probable con un test automatizado); verificado manualmente (ver «Cómo verificar») |
| S-02 | MEDIO | **Corregido** | `test_rate_limit_not_bypassable_with_spoofed_forwarded_for` — `xfail` retirado, ahora pasa en verde |
| S-03 | MEDIO | **Corregido** | `test_chunked_body_over_limit_is_413` — `xfail` retirado, ahora pasa en verde |
| S-04 | BAJO | Sin acción (por diseño, ver ADR 0003) | Ya estaba así en la revisión; no tocado |
| S-05 | MEDIO | **Corregido** | `test_sync_set_conflict_does_not_reveal_foreign_client_uuid` — `xfail` retirado, ahora pasa en verde |
| S-06 | BAJO | **Corregido** | Nueva aserción en `test_export_import_roundtrip_is_idempotent` (`import_too_large` con 422) |
| S-07 | MEDIO | Sin acción (ya en verde, ver revisión) | `test_nul_byte_strings_do_not_cause_500` seguía pasando; no se tocó código de producto |
| S-08 | BAJO | **Corregido** | `test_ics_text_fields_cannot_inject_lines` — `xfail` retirado, ahora pasa en verde |
| S-09 | BAJO | **Corregido** | Nueva aserción en `test_export_import_roundtrip_is_idempotent` (`Content-Disposition`) |

## Ficheros tocados

Todos dentro de `backend/`:

- **`backend/app/services/nutrition.py`**: sin cambios (ya generaba el `engine_input` correcto;
  ver «Decisiones»). Se añadió cobertura en
  `backend/tests/integration/test_nutrition_account_admin.py`.
- **`backend/app/security/ratelimit.py`** (S-01): `RateLimiter._hits` pasa de
  `defaultdict(deque)` sin límite a `dict[str, dict[str, deque]]` (por bucket, luego por clave)
  con expulsión LRU acotada a `max_keys_per_bucket` (10 000 por defecto) y borrado de claves sin
  marcas de tiempo vigentes.
- **`backend/app/security/tokens.py`** (S-02): `client_ip()` acepta `trusted_proxy_count`; con 0
  (por defecto) ignora `X-Forwarded-For` por completo y usa `request.client.host`; con N ≥ 1 toma
  el salto correspondiente contando desde la derecha.
- **`backend/app/core/config.py`** (S-02): nuevo ajuste `trusted_proxy_count` (env
  `TRUSTED_PROXY_COUNT`, 0-10, por defecto 0).
- **`backend/app/api/deps.py`**, **`backend/app/services/auth.py`** (S-02): los tres puntos que
  llamaban a `client_ip(request)` ahora pasan `settings.trusted_proxy_count`.
- **`backend/app/security/middleware.py`** (S-03): `BodyLimitAndCsrfMiddleware` deja de ser
  `BaseHTTPMiddleware` y pasa a ser un middleware ASGI puro que envuelve `receive` (cuenta bytes
  reales de cada `http.request`, no solo `Content-Length`) y `send` (si se supera el límite,
  sustituye lo que el downstream intente responder por un único 413, sin duplicar mensajes ASGI).
- **`backend/app/core/ids.py`** (S-05): nueva función pública `derived_uuid()` (antes vivía como
  `_derived()`/`IMPORT_NAMESPACE` privados en `services/account.py`); ambos servicios que
  necesitan derivar un id estable para un `client_uuid` ajeno la importan desde aquí (evita
  duplicar la lógica y el import circular `account.py` ↔ `training.py`).
- **`backend/app/services/account.py`** (S-05, S-06): `_derived()` pasa a ser un envoltorio de
  `derived_uuid()`; nuevas `IMPORT_MAX_ITEMS` y `_check_import_size()` llamada al inicio de
  `import_account()`.
- **`backend/app/services/training.py`** (S-05): `_sync_set()` distingue "pertenece a otra
  sesión mía" (409 real) de "pertenece a otra cuenta" (deriva un `client_uuid` propio con
  `derived_uuid()` y continúa como si no existiera fila, igual que la importación de cuentas).
- **`backend/app/services/exports.py`** (S-08): `_escape()` normaliza `\r\n` y luego cualquier
  `\r` suelto a `\n` **antes** de escapar los saltos de línea a `\n` literal.
- **`backend/app/api/routers/admin.py`** (S-09): `GET /me/export` añade
  `Content-Disposition: attachment; filename="forja-export.json"`.
- **`backend/tests/security/test_f3_security.py`**: se retira `@KNOWN_ISSUE` (`xfail(strict=True)`)
  de los 4 tests que demostraban S-02, S-03, S-05 y S-08 (ahora pasan en verde como regresión); se
  actualizan sus docstrings a "(corregido)". Ningún test se ha borrado ni debilitado.
- **`backend/tests/integration/test_nutrition_account_admin.py`**: regresión del bug de nutrición
  (`POST .../calculate` con `json={}` explícito) y dos aserciones nuevas en
  `test_export_import_roundtrip_is_idempotent` para S-06 y S-09.

**No se ha tocado** `contracts/openapi.yaml`, `.env.example` (fuera de mi zona por ADR 0002; ver
«Peticiones a otros agentes»), ni ningún fichero de `engine/`, `nutrition/`, `frontend/`,
`deploy/`.

## Decisiones

1. **Bug de nutrición ya corregido en `main`**: reproduje el escenario exacto del reporte
   (`POST /nutrition/targets/calculate` con cuerpo `{}` literal, no una petición sin cuerpo) contra
   un PostgreSQL efímero y devuelve `200` con un `NutritionTarget` completo. `nutrition/`
   (0.2.1) y `backend/app/services/nutrition.py::build_input` ya construyen un `NutritionInput`
   que coincide exactamente con `forja_nutrition.models.NutritionInput` (sin `fat`/`tolerances`
   anidados: esos campos viven en `NutritionTables`, las tablas internas del motor, no en la
   entrada). El commit `f4e38a6 feat(backend): align API with contract 1.2.0` (rama
   `f2/backend-align`, mergeada en `main` **antes** que `f2/frontend-integration`) ya lo resolvió;
   el handoff de frontend describe un estado anterior al merge. Añadí la regresión de todos modos
   porque no existía una prueba que mandara literalmente `{}` (la prueba previa mandaba la
   petición sin cuerpo en absoluto, un caso distinto aunque el resultado sea el mismo hoy).
2. **S-01 sin `xfail` dedicado**: la propia revisión ya señala que demostrarlo con un test
   automatizado exigiría millones de peticiones reales; no he añadido uno (ralentizaría la suite
   sin necesidad). Verifiqué la corrección con un script ad-hoc (50 000 claves distintas quedan
   acotadas a `max_keys_per_bucket`; una misma clave repetida no acumula deques vacíos) — ver
   «Cómo verificar». Elegí expulsión LRU en memoria (sin Redis) por bucket, tal como pedía la
   tarea; los nombres de bucket (`login`, `register`, …) son fijos y no los controla el atacante,
   solo la clave dentro de cada bucket.
3. **S-02, `TRUSTED_PROXY_COUNT` en vez de un allowlist de IPs**: opté por un contador de saltos
   de confianza (más simple de configurar y suficiente para un único nginx delante de la app,
   que es el despliegue de ADR 0003) en vez de una lista de IPs de proxy. Por defecto (`0`) no se
   lee `X-Forwarded-For` en absoluto. **Pendiente**: el ajuste vive en `Settings`
   (`backend/app/core/config.py`), pero `.env.example` (raíz del repo) es zona de
   `devops-despliegue` según ADR 0002, así que no lo he tocado — ver «Peticiones a otros
   agentes». Esto hace que `backend/tests/unit/test_env_example.py::test_env_example_matches_settings`
   falle hasta que se añada la línea `TRUSTED_PROXY_COUNT=0` allí; es la única prueba roja en toda
   la suite (`666 passed, 1 failed` en `uv run pytest tests -m "not slow"`) y es exactamente la
   dependencia cruzada que predijo la revisión ("documentar en `.env.example`/ADR 0003").
4. **S-03, middleware ASGI puro en vez de `BaseHTTPMiddleware`**: la primera versión (envolver
   solo `receive` y dejar que la excepción se propagase hasta el `exception_handler` ya
   registrado) parecía la más simple, pero **FastAPI captura *cualquier* excepción durante el
   parseo del cuerpo** (`request_body_to_args`) y la convierte en `HTTPException(400)` sin mirar
   el tipo — así que un `ProblemError(413)` lanzado desde dentro de `receive()` acababa en `400`,
   no en `413` (lo detecté con el propio test `test_chunked_body_over_limit_is_413`, que primero
   falló con `400 == 413`). La solución robusta es envolver también `send`: cuando se supera el
   límite, `receive()` devuelve un `http.disconnect` limpio (en vez de lanzar) y `send()` sustituye
   **lo que sea** que el downstream intente responder (400, 500, lo que sea) por nuestro único
   413, descartando cualquier mensaje ASGI adicional. Esto es más robusto que depender de qué
   excepción concreta dispare FastAPI internamente.
5. **S-05, mismo espacio de nombres UUID que la importación de cuentas**: moví
   `IMPORT_NAMESPACE`/`_derived()` de `services/account.py` a una función pública
   `derived_uuid()` en `core/ids.py` (import circular: `account.py` ya importa `training.py`,
   así que `training.py` no puede importar `account.py`). El resultado es el mismo UUID v5
   estable que ya usaba la importación, solo que ahora reutilizable desde `/sync`.
6. **S-06, límite en la capa de servicio, no en el esquema Pydantic**: `UserExport` (en
   `app/schemas/api.py`) es un fichero **generado** por `datamodel-codegen` desde
   `contracts/openapi.yaml`; añadirle `Field(max_length=…)` directamente habría hecho que el
   OpenAPI que exporta FastAPI divergiera del contrato aprobado (rompiendo
   `tests/contract/test_api_matches_contract.py`) y habría exigido pasar por
   `docs/CONTRACT_CHANGES.md` (arquitecto), que la propia revisión ya anticipaba como necesario
   "si se cambia el contrato". En vez de eso, añadí `_check_import_size()` en
   `services/account.py`: un 422 explícito (`import_too_large`) antes de tocar la base de datos,
   sin cambiar el contrato ni el esquema. Verificado que `tests/contract` sigue en verde
   (455 passed).
7. **S-09, cabecera puesta en el router, no en el esquema**: `Content-Disposition` se añade con
   `response.headers[...]` en el propio `export_account_data()`; no forma parte del
   `response_model` ni del OpenAPI exportado por FastAPI (una cabecera puesta así en tiempo de
   ejecución no aparece en el spec salvo que se declare explícitamente en `responses=`), así que
   tampoco afecta al contrato — confirmado con `tests/contract` en verde.
8. **S-07 y S-04, sin cambios**: ambos quedan exactamente como los dejó la revisión (S-04 es un
   riesgo aceptado en ADR 0003 sin corrección abierta; S-07 ya pasaba en verde en los tres campos
   probados y no había vulnerabilidad confirmada, solo una recomendación de robustez a futuro que
   tocaría muchos esquemas generados — lo dejo anotado para una tarea propia si se decide
   abordarlo, en vez de mezclarlo aquí).

## Cómo verificar

```bash
cd backend
uv sync --locked

# FAST MODE pedido por la tarea
uv run pytest tests/security tests/integration/test_nutrition_account_admin.py -m "not slow" --no-cov -q
# Esperado: 134 passed (0 xfail — los 4 KNOWN_ISSUE de S-02/S-03/S-05/S-08 se retiraron y ahora
# son tests normales en verde).

uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy --strict app        # Success: no issues found in 54 source files

# Suite completa (informativo, no es el modo rápido pedido):
uv run pytest tests -m "not slow" --no-cov -q
# 666 passed, 1 failed: tests/unit/test_env_example.py::test_env_example_matches_settings
# (esperado hasta que devops-despliegue añada TRUSTED_PROXY_COUNT a .env.example; ver Decisión 3
# y «Peticiones a otros agentes»). No es una regresión de este trabajo, es la dependencia cruzada
# documentada por la propia revisión de seguridad.

# Contrato (confirma que los cambios de S-06/S-09 no divergen de contracts/openapi.yaml):
uv run pytest tests/contract --no-cov -q   # 455 passed
```

Reproducción puntual de cada hallazgo corregido:

```bash
uv run pytest tests/security -k test_rate_limit_not_bypassable_with_spoofed_forwarded_for -q   # S-02
uv run pytest tests/security -k test_chunked_body_over_limit_is_413 -q                          # S-03
uv run pytest tests/security -k test_sync_set_conflict_does_not_reveal_foreign_client_uuid -q   # S-05
uv run pytest tests/security -k test_ics_text_fields_cannot_inject_lines -q                      # S-08
uv run pytest tests/integration/test_nutrition_account_admin.py -k test_target_plan_swap -q      # bug nutrición
uv run pytest tests/integration/test_nutrition_account_admin.py -k test_export_import_roundtrip -q  # S-06 + S-09
```

S-01 no tiene un test automatizado dedicado (ver Decisión 2); para verificarlo manualmente:

```python
from app.security.ratelimit import RateLimiter
rl = RateLimiter(max_keys_per_bucket=1000)
for i in range(50_000):
    try:
        rl.check("login", f"email:probe-{i}@attacker.test")
    except Exception:
        pass
assert len(rl._hits["login"]) <= 1000   # antes: 50 000 entradas que nunca se liberaban
```

## Métricas

- `tests/security`: **134 passed**, 0 xfail, 0 errores (antes: 130 passed + 4 xfail).
- `tests/integration/test_nutrition_account_admin.py`: **12 passed** (2 aserciones nuevas: bug de
  nutrición y S-06/S-09; antes 10 tests, mismas 10 funciones, 2 con más cobertura).
- `tests/contract`: **455 passed** (sin cambios; confirma que ningún fix divergió del contrato).
- Suite completa `tests -m "not slow"`: **666 passed, 1 failed** (la dependencia cruzada de
  `.env.example` descrita en la Decisión 3; 0 regresiones en el resto).
- `ruff check`/`ruff format --check` sobre `app` y `tests`: limpio.
- `mypy --strict app`: **0 errores** (54 ficheros). `mypy --strict` sobre `tests` tiene **1 error
  preexistente, no introducido por este trabajo**, en
  `tests/security/test_f3_security.py:412` (`test_nul_byte_strings_do_not_cause_500`, un `dict`
  con anotación `dict[str, Any]` que mypy infiere como `object` en una rama) — no toqué esa
  función; queda anotado por si se quiere limpiar en una pasada de tipos aparte.
- Ficheros de producto tocados: 11. Ficheros de test tocados: 2 (ninguno nuevo).

## Riesgos/pendientes

- **`TRUSTED_PROXY_COUNT` no está en `.env.example`** (zona de `devops-despliegue`, ADR 0002):
  hasta que se añada, `test_env_example_matches_settings` queda en rojo (ver Decisión 3). El
  comportamiento en producción es seguro mientras tanto (por defecto `0` = no confiar en
  `X-Forwarded-For`), pero si el despliegue real necesita `TRUSTED_PROXY_COUNT=1` para que el
  rate limit y el `ip_hash` de auditoría vean la IP real de los usuarios detrás del nginx del
  propio despliegue, alguien tiene que fijarlo explícitamente (por defecto, sin ese ajuste, todas
  las peticiones que pasen por ese nginx compartirían la misma IP aparente —la del propio
  nginx—, lo que agruparía el rate limit de todos los usuarios entre sí; ver Petición a devops).
- **S-07 y S-04 quedan sin tocar** intencionadamente (ver Decisión 8); si se decide cerrarlos de
  verdad (un `field_validator` común contra `\u0000` en todos los esquemas de texto libre) es
  trabajo aparte, no incluido aquí para no mezclar alcance.
- El bug de nutrición del frontend ya estaba resuelto por otra rama antes de que llegara esta
  tarea; no hay riesgo residual ahí, solo lo dejo explícito para que el orquestador no lo
  reabra pensando que sigue pendiente.

## Peticiones a otros agentes

- **`devops-despliegue`**: añadir `TRUSTED_PROXY_COUNT=0` a `.env.example` (con un comentario
  explicando que solo debe subirse a `1` si hay exactamente un proxy de confianza —el nginx del
  propio despliegue— inmediatamente delante de la app, y confirmando qué cabecera pone realmente
  ese nginx, tal como pedía S-02 en `docs/reviews/f3-security.md`). Sin este cambio,
  `backend/tests/unit/test_env_example.py` seguirá en rojo.
- **`arquitecto`**: informativo, no se pide nada — S-06 y S-09 se resolvieron sin tocar
  `contracts/openapi.yaml` (ver Decisiones 6 y 7), así que no hay ninguna entrada pendiente en
  `docs/CONTRACT_CHANGES.md` por este trabajo.
- **`qa-tests`**: si se añade un job de suite completa (`tests` sin filtrar por directorio) en
  CI, tendrá un rojo esperado en `test_env_example_matches_settings` hasta que devops complete la
  petición anterior; no es una regresión de esta rama.
- **Orquestador**: no fusionar `f3/backend-fixes` hasta que `devops-despliegue` añada la variable
  de entorno (o decidir fusionar ya y aceptar el rojo puntual en `tests/unit`, ya que no forma
  parte del "modo rápido" pedido para esta tarea ni de `make test`/CI si ese target no incluye
  `tests/unit` — a confirmar con `arquitecto`, propietario de los objetivos de calidad del
  `Makefile`).

# Handoff · Fase 3 · revisor-seguridad

Rama: `f3/security` (sin fusionar). Alcance revisado: `backend/`, `frontend/`. `deploy/` queda
pendiente para otra pasada (lo está escribiendo devops en paralelo).

## Resumen

Auditoría de seguridad y privacidad de §11 sobre autenticación, sesiones, CSRF, autorización por
propietario, entrada/validación, importación JSON, borrado de cuenta, PII en logs, SQLi, SSRF/RCE
en la ingesta e IDOR en `/sync`, más `pip-audit`/`npm audit`. Se ejecutó todo contra un PostgreSQL
16 real (testcontainers, igual que `tests/integration`), no solo por lectura de código.

**0 críticos, 1 alto, 4 medios, 4 bajos, 2 informativos.** Detalle completo con evidencia
`file:line`, exploit/prueba y corrección exacta en `docs/reviews/f3-security.md`. No se encontró
inyección SQL, SSRF en el PDF ni inyección de comandos en la ingesta del dataset — los tres
controles clave de §11/§2.1 sobre esas superficies están correctamente implementados. La
autorización por propietario se sostiene en las 20 combinaciones de recurso/ruta probadas con
acceso cruzado real.

- **S-01 ALTO** — El rate limiter en memoria (`security/ratelimit.py`) nunca libera las
  entradas de su diccionario interno; la clave del bucket `login` es el correo enviado por el
  cliente (sin autenticar), así que un atacante puede agotar memoria del proceso enviando
  millones de intentos de login con correos distintos. → propietario `backend-api`.
- **S-02 MEDIO** — `client_ip()` confía en el primer valor de `X-Forwarded-For` sin validar
  que venga de un proxy de confianza; permite falsificar la clave del rate limit y el `ip_hash`
  de auditoría. → `backend-api` (coordinar con `devops`).
- **S-03 MEDIO** — El límite de cuerpo de la app solo mira `Content-Length`; un cuerpo
  `Transfer-Encoding: chunked` lo evita. → `backend-api` (+ límite equivalente en nginx,
  `devops`).
- **S-05 MEDIO** — El conflicto `409` de `/sync` al reutilizar un `client_uuid` de serie ajeno
  confirma su existencia en otra cuenta (canal lateral de un bit). → `backend-api`.
- **S-07 MEDIO** — Ningún campo de texto libre probado produce hoy un 500 por `\u0000`, pero no
  hay una regla Pydantic común que lo prevenga en el resto del contrato; se deja como robustez
  a extender, no como vulnerabilidad confirmada. → `backend-api`.
- **S-04, S-06, S-08, S-09 BAJO**: enumeración de cuentas inactivas (riesgo aceptado en ADR
  0003, sin acción), falta de `max_length` explícito en las listas de `/me/import`, un `\r`
  suelto no neutralizado en la exportación ICS, y falta de `Content-Disposition` en
  `/me/export`. → `backend-api` (y `frontend` para S-09, opcional).
- **S-10/S-11 INFORMATIVO**: inventario de controles ya verificados correctos (para no
  reauditarlos) y alcance pendiente (`deploy/`).

## Ficheros tocados

Solo se han creado pruebas y documentación, ningún fichero de producto:

- `backend/tests/security/__init__.py` (nuevo)
- `backend/tests/security/conftest.py` (nuevo — reexporta fixtures de
  `tests/integration/conftest.py`, mismo PostgreSQL efímero)
- `backend/tests/security/test_f3_security.py` (nuevo — ~25 tests, 120 aserciones tras
  parametrizar sobre las 68 rutas del contrato; 4 marcados `xfail(strict=True)` como hallazgo
  abierto)
- `docs/reviews/f3-security.md` (nuevo)
- `docs/handoffs/f3-security.md` (este fichero)

No se ha tocado nada en `backend/app/**`, `frontend/src/**`, `contracts/**` ni `deploy/**`.

## Decisiones

1. Las pruebas nuevas viven en `backend/tests/security/` (paquete propio, no dentro de
   `tests/integration/`) para que el propietario pueda ejecutarlas de forma aislada
   (`pytest tests/security`) o incluirlas en `make test` sin más cambios, ya que reutilizan las
   fixtures de integración vía import directo (mismo contrato `pytest.mark.integration`,
   requiere Docker).
2. Los tests que demuestran un hallazgo real y no un simple gap de cobertura se marcan
   `@pytest.mark.xfail(strict=True, reason=...)` en vez de `skip` o de dejarlos en rojo: así
   quedan verdes en el resumen de la suite pero **fallan el build en XPASS** si alguien los
   "arregla" sin que el propietario haya aplicado la corrección real — evita que una corrección
   parcial pase inadvertida y sirve de regresión automática una vez corregido (momento en el que
   hay que quitar la marca).
3. La prueba de autenticación/CSRF paramétrica lee `contracts/openapi.yaml` directamente (no una
   lista mantenida a mano) para cubrir las 68 rutas reales del contrato sin quedar desactualizada
   si se añaden rutas nuevas en fases futuras.
4. Se evitó cualquier prueba que dependa de tiempos de red para medir el retraso constante de
   argon2 vs. hash señuelo (ruido de CI); en su lugar se comprueba que el **cuerpo de la
   respuesta** es bit a bit idéntico entre correo inexistente y contraseña incorrecta, que es la
   garantía que ADR 0003 promete explícitamente.
5. No se modificó ni se propuso modificar código de producto (fuera de mandato): todo hallazgo
   incluye la corrección exacta para que el agente propietario la aplique.

## Cómo verificar

```bash
cd backend
uv sync --locked
uv run pytest tests/security --no-cov -q        # requiere Docker (testcontainers-postgres)
# Esperado: ~120 passed, 4 xfailed (S-02, S-03, S-05, S-08 — hallazgos abiertos)

# Auditoría de dependencias (0 vulnerabilidades en las tres bases de código Python)
uv export --frozen --no-emit-project --no-hashes -q -o /tmp/req-backend.txt
uv run --with pip-audit pip-audit -r /tmp/req-backend.txt --no-deps --disable-pip
cd ../engine  && uv export --frozen --no-emit-project --no-hashes -q -o /tmp/req-engine.txt \
  && (cd ../backend && uv run --with pip-audit pip-audit -r /tmp/req-engine.txt --no-deps --disable-pip)
cd ../nutrition && uv export --frozen --no-emit-project --no-hashes -q -o /tmp/req-nutrition.txt \
  && (cd ../backend && uv run --with pip-audit pip-audit -r /tmp/req-nutrition.txt --no-deps --disable-pip)

cd ../frontend
npm audit --omit=dev                            # 0 vulnerabilidades
```

Para reproducir un hallazgo concreto, ejecutar solo su test:
`uv run pytest tests/security -k test_rate_limit_not_bypassable_with_spoofed_forwarded_for -q`
(pasará como `xfail`; tras la corrección de S-02 debe quitarse la marca y volverá a `passed`).

## Métricas

- Tests nuevos: 1 fichero, ~25 funciones de test → **120 casos** ejecutados (tras parametrizar
  sobre las rutas del contrato) + **4 xfail** (hallazgos abiertos), 0 errores de colección.
- Tiempo de ejecución de la suite nueva: ~19 s (PostgreSQL efímero incluido).
- No se ha medido cobertura de línea/rama porque el mandato es auditar, no ampliar cobertura de
  producto; `ruff check`/`ruff format` pasan limpios sobre `backend/tests/security/`.
- Dependencias auditadas: 398 paquetes Python (`backend` + `engine` + `nutrition`, unión de
  `uv.lock`) y el árbol de producción de `frontend` (`npm audit --omit=dev`) → **0
  vulnerabilidades conocidas** en ambos.

## Riesgos/pendientes

- **S-01 (ALTO)** es explotable hoy sin autenticación y debería priorizarse antes de exponer el
  entorno de producción a Internet, aunque el despliegue detrás de nginx con `limit_req` (§12)
  mitiga parcialmente si esa capa está bien configurada — pendiente de confirmar en la revisión
  de `deploy/`.
- `deploy/` (nginx `auth_request`, `limit_req`, Docker no-root/`read_only`, Trivy) **no** se ha
  revisado en esta pasada; pido explícitamente al orquestador una segunda tanda de este mismo
  agente cuando devops entregue esa carpeta (ver Peticiones).
- Los 4 tests `xfail(strict=True)` deben mantenerse así hasta que el propietario corrija cada
  hallazgo; si CI los ve pasar sin que el hallazgo se haya cerrado explícitamente, es una señal
  de que algo cambió el comportamiento por accidente y merece revisión, no solo quitar la marca.
- No he corregido ningún fichero de producto (fuera de mandato); S-01 a S-09 quedan asignados a
  sus propietarios con la corrección exacta redactada en `docs/reviews/f3-security.md`.

## Peticiones a otros agentes

- **`backend-api`**: aplicar S-01 (ALTO, prioridad), S-02, S-03, S-05, S-06, S-07, S-08 y,
  opcionalmente, S-09. Cada uno incluye la corrección exacta y el fichero/línea. Al corregir un
  hallazgo con un test `xfail` asociado, quitar la marca `@KNOWN_ISSUE`/`xfail` de
  `backend/tests/security/test_f3_security.py` (no borrar el test: debe quedar en verde como
  regresión).
- **`devops`**: al escribir `deploy/`, tener en cuenta S-02 (qué cabecera de IP real pone nginx y
  desde qué dirección llega a la app) y S-03 (fijar `client_max_body_size` como defensa
  complementaria al límite de la app). Pido al orquestador programar una segunda revisión de
  seguridad centrada en `deploy/` cuando esa carpeta esté lista.
- **`frontend`**: revisar si `GET /me/export` ya se descarga como fichero (Blob/`<a download>`)
  en la UI; si se abre inline, considerar S-09 (baja prioridad).
- **Orquestador**: no fusionar `f3/security` — solo contiene tests y documentación nuevos, sin
  tocar código de producto; puede fusionarse en cualquier momento sin riesgo de romper nada, o
  esperar a que los propietarios corrijan primero. Recomiendo fusionar pronto para que los tests
  actúen de barrera de regresión desde ya, con los 4 `xfail` visibles en el resumen de CI como
  recordatorio de deuda pendiente.

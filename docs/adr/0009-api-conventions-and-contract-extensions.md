# ADR 0009 · Convenciones de API y ampliaciones del contrato de §9

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
§9 fija los endpoints y las convenciones básicas (JSON `snake_case`, RFC 9457, cursor,
`ETag`, `Idempotency-Key`). Al escribir `contracts/openapi.yaml` aparecen huecos que otras
secciones exigen pero §9 no enumera, y detalles que deben quedar decididos antes de que el
frontend genere cliente y mocks.

## Decisión
**Convenciones** (recogidas en `info.description` del contrato y verificadas por
`backend/tests/contract/test_openapi_contract.py`):
- Errores `application/problem+json` con extensiones `code` (estable), `request_id`,
  `errors[]` (validación), `violations[]` (motor) y `block` (nutrición). `type` es una URI
  relativa `/problems/<código>`. Excepciones deliberadas: `GET /auth/check` (401 sin cuerpo
  para nginx) y `GET /ready` (503 con el detalle de comprobaciones).
- Paginación por cursor opaco (`cursor`, `limit` 1–100, defecto 20) con sobre
  `{items, next_cursor}`. Colecciones acotadas por naturaleza (sesiones activas,
  alternativas) devuelven `{items}` sin cursor.
- `ETag` débil + `If-None-Match` ⇒ 304 en `GET /exercises`, `/exercises/{id}`,
  `/exercises/{id}/alternatives` y `/catalog/facets`, con `Cache-Control: private, no-cache`
  porque la representación incluye favoritos del usuario.
- `Idempotency-Key` obligatorio en `POST /sessions` y `POST /sessions/{id}/sets` (24 h);
  clave reutilizada con otro cuerpo ⇒ 422 `idempotency_key_reused`; concurrente ⇒ 409.
- Recursos ajenos ⇒ 404 (nunca 403). Rol insuficiente ⇒ 403 `admin_required`.
- Seguridad declarada por operación: cookie `sessionCookie` y, en métodos no seguros,
  `csrfToken`. `register` y `login` exigen solo CSRF.
- Índices desde 0; `set_index` desde 1; unidades métricas; semillas ≤ 2^53−1.
- Parámetros de filtro multivalor con `style: form, explode: true`.

**Ampliaciones aprobadas** sobre la tabla de §9 (todas justificadas por otras secciones):

| Endpoint | Motivo |
|---|---|
| `GET /auth/csrf` | Obtener la cookie CSRF antes de login/registro (§11, ADR 0003). |
| `GET /auth/sessions`, `DELETE /auth/sessions/{auth_session_id}` | «Sesiones activas» y revocación desde ajustes (§10.2.10, §11). |
| `GET /about` | Créditos con licencia MIT, aviso de Gym visual y SHA del dataset (§2.1, §10.2.10). |
| `POST /generator/preview/regenerate-day`, `POST /generator/preview/swap` | El wizard regenera un día y cambia ejercicios **antes** de guardar (§10.2.3); sin estado en servidor, el plan viaja en el cuerpo. |
| `GET /nutrition/plans` | Localizar el plan vigente y el historial de planes (§10.2.9). |

**Interpretaciones de §9**: `DELETE /body-metrics` se concreta como
`DELETE /body-metrics/{metric_id}`; `POST /body-metrics` es un *upsert* por fecha (200 si
sustituye, 201 si crea); `GET /sessions/next` devuelve siempre 200 con
`status ∈ {scheduled, rest_day, no_active_program, program_completed}`.

## Alternativas
- **Paginación por offset**: más simple, pero inestable con inserciones concurrentes y más
  lenta en listas largas.
- **Guardar borradores de plan en servidor** para regenerar/cambiar en el wizard: añade
  estado, limpieza y otra tabla; el plan cabe holgadamente en el cuerpo (decenas de KB).
- **Errores ad hoc `{detail}` de FastAPI**: incumplen §9.

## Consecuencias
- El frontend genera cliente y mocks MSW directamente de `contracts/openapi.yaml`, cuyos
  ejemplos validan contra sus esquemas (test de contrato).
- `backend-api` debe producir exactamente este esquema (test de contrato en CI).
- Nuevos endpoints o campos pasan por `docs/CONTRACT_CHANGES.md`.

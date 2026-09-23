# ADR 0003 · Autenticación por sesión con cookie y CSRF de doble envío

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
La SPA y la API comparten origen detrás de nginx (§4.3). nginx necesita validar el acceso a
`/media` con `auth_request` (§2.1) sin lógica propia. §11 exige cookie `__Host-`, token opaco
hasheado, expiración deslizante, revocación y CSRF de doble envío.

## Decisión
- **Sesión opaca en servidor**: token aleatorio de 32 bytes (`secrets.token_urlsafe(32)`), se
  guarda solo su SHA-256 en `session.token_hash`. Cookie
  `__Host-forja_session=<token>; Path=/; Secure; HttpOnly; SameSite=Lax`, `Max-Age` de
  `SESSION_TTL_DAYS` (30) renovado de forma deslizante (como mucho una escritura de
  `last_seen_at`/`expires_at` por minuto y sesión).
- **Rotación**: nuevo token en login y en cambio de contraseña; el cambio de contraseña y la
  desactivación de un usuario revocan el resto de sesiones.
- **CSRF de doble envío**: cookie `__Host-forja_csrf` (no HttpOnly, 32 bytes aleatorios) +
  cabecera `X-CSRF-Token` idéntica en todo POST/PUT/PATCH/DELETE, comparadas en tiempo
  constante. Se emite en `GET /auth/csrf` (necesario antes de login/registro, que también
  exigen CSRF para evitar *login CSRF*) y se rota al iniciar sesión.
- **`GET /auth/check`**: responde 204/401 sin cuerpo, solo lectura de BD por índice único
  (`token_hash`), sin renovar la sesión; lo usa `auth_request` de nginx para `/media`.
- **Contraseñas**: argon2id (`argon2-cffi`, parámetros OWASP: m=19 MiB, t=2, p=1 como mínimo),
  mínimo 10 caracteres y lista local de contraseñas comunes; rehash transparente si cambian
  los parámetros.
- **Registro**: `REGISTRATION_OPEN=false` por defecto; `make bootstrap` crea el admin por CLI.
  Si el registro está abierto y no hay usuarios, el primero es `admin`. El admin puede abrir o
  cerrar el registro en `app_setting` (prevalece sobre el entorno).
- **Enumeración**: el login responde siempre `401 invalid_credentials` con tiempo constante
  (verificación argon2 contra un hash señuelo si el email no existe). El registro abierto
  revela si un email existe (`409 email_taken`); se acepta porque el registro está cerrado por
  defecto y limitado por tasa.
- **Rate limiting**: en la app (login, registro, cambio de contraseña, borrado de cuenta,
  generador) y `limit_req` en nginx para `/api/v1/auth/`.

## Alternativas
- **JWT en `Authorization`**: sin estado, pero no revocable sin lista negra, expone el token a
  JS (XSS) y `auth_request` para medios sería más complejo.
- **JWT en cookie**: revocación igualmente difícil y tamaño de cookie mayor.
- **`SameSite=Strict` sin token CSRF**: rompe enlaces entrantes a la app instalada y no cubre
  navegadores antiguos; §11 exige doble envío.

## Consecuencias
- Cada petición autenticada hace una consulta por índice a `session` (coste despreciable).
- El frontend lee `__Host-forja_csrf` y la añade a toda escritura (middleware de
  `openapi-fetch`); los mocks MSW deben aceptar la cabecera.
- `Secure` exige HTTPS; en desarrollo se usa `http://localhost`, que los navegadores tratan
  como contexto seguro.

# ADR 0006 · Estrategia offline y sincronización

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
El reproductor de sesión debe funcionar sin conexión, sobrevivir a recargas y cierres, y
sincronizar al volver la red (§10.2.5, §10.3), sin duplicar series ni perder correcciones.

## Decisión
- **Fuente de verdad local durante la sesión**: el estado del reproductor (máquina de estados)
  y la cola de escrituras se guardan en IndexedDB (`idb`), nunca en `localStorage`.
- **Identidad en el cliente**: cada sesión y serie lleva `client_uuid` (UUID v7 generado en el
  cliente). En servidor son únicos (`workout_session (user_id, client_uuid)`,
  `set_log (client_uuid)`), lo que hace las escrituras idempotentes.
- **Online**: `POST /sessions` y `POST /sessions/{id}/sets` con `Idempotency-Key =
  client_uuid`; reintentos seguros (misma respuesta con `Idempotent-Replayed: true`).
- **Offline**: las operaciones se encolan (`session_upsert`, `set_upsert`, `set_delete`) con
  `updated_at` del cliente y se envían en lotes de hasta 500 a `POST /sync` con reintento
  exponencial (1 s, 2 s, 4 s… máx. 5 min, con *jitter*) al detectar conectividad
  (`online` + sondeo de `/api/v1/health`) y mediante Background Sync donde exista.
- **Resolución**: por operación y en orden; «última escritura gana» comparando `updated_at`
  del cliente con `client_updated_at` del servidor. Resultado por operación: `applied`,
  `duplicate` (ya aplicada), `superseded` (el servidor tiene algo más nuevo: el cliente
  descarta su versión y recarga) o `rejected` (con `problem`, p. ej. ejercicio inexistente; el
  cliente lo muestra y lo retira de la cola). Un fallo no aborta el lote.
- **Borrados**: tombstones (`set_log.deleted_at`) para que un `set_upsert` tardío no resucite
  una serie borrada después.
- **Lecturas offline**: el service worker (Workbox) precachea el shell, usa
  stale-while-revalidate para `/api/v1/exercises*`, cache-first para miniaturas (límite 1.400)
  y GIFs (límite configurable, 300 MB) y el botón «Descargar biblioteca» precachea los medios
  del programa activo. Las respuestas de `/api/v1` con datos personales distintos del
  catálogo no se cachean en el SW; el cliente conserva el programa activo en IndexedDB.
- Los récords personales se recalculan en el servidor al aplicar la sincronización.

## Alternativas
- **CRDT / sincronización por registros de cambios**: robusto para edición concurrente
  multi-dispositivo, pero desproporcionado para un registro de series de un solo usuario.
- **Background Sync como único mecanismo**: no disponible en Safari/WebKit (objetivo E2E).

## Consecuencias
- El backend implementa `/sync` y la tabla `idempotency_key`; el frontend implementa la cola,
  el reintento y la reconciliación; QA prueba «cortar la red a mitad de sesión».
- Las marcas de tiempo del cliente pueden estar desfasadas: `SyncResponse.server_time`
  permite al cliente estimar el desfase y corregir `updated_at` en envíos posteriores.

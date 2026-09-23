# ADR 0004 · Medios fuera del repositorio y licencia de Gym visual

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
Los datos del dataset son MIT, pero los medios (`images/*.jpg`, `videos/*.gif`) son © Gym
visual, redistribuidos con permiso a 180×180 y **no** cubiertos por MIT (§2.1). Clonar el
repo de Forja no puede conceder licencia sobre ellos.

## Decisión
- Los medios **no se versionan** en el repo de Forja (`.gitignore` excluye `media/`). Se
  obtienen en el despliegue con `forja-ingest fetch` desde
  `DATASET_REPO@DATASET_COMMIT` (`7455efae41b330c265e7cd4b78dfa848e7ce5ebd`), en clon
  superficial del commit exacto.
- Se copian **byte a byte** a `$MEDIA_ROOT/thumbs/` y `$MEDIA_ROOT/gifs/`; se genera
  `manifest.json` con SHA-256, bytes y dimensiones (Pillow en solo lectura) y se verifica
  180×180. Prohibido reescalar, recodificar, recortar, convertir o marcar.
- Se sirven por nginx desde un volumen de solo lectura con
  `Cache-Control: public, max-age=31536000, immutable` (los nombres incluyen `media_id`) y,
  con `MEDIA_REQUIRE_AUTH=true` (defecto), tras `auth_request /api/v1/auth/check`.
- La API expone siempre `media.attribution = {text: "© Gym visual", url: "https://gymvisual.com/"}`
  junto a las URLs, y el frontend tiene un **único** componente `ExerciseMedia` que muestra la
  atribución debajo del medio (regla ESLint que prohíbe `<img>` de medios fuera de él y test
  que falla si falta la atribución). El PDF incluye la atribución en cada página.
- `LICENSE` y `NOTICE.md` del dataset se copian a `$MEDIA_ROOT/LICENSES/` y se muestran en
  «Créditos» junto con el SHA del commit ingerido (`GET /about`).
- La documentación de despliegue advierte de revisar los términos de Gym visual antes de
  exponer la app públicamente.

## Alternativas
- **Versionar los medios** (Git LFS): contradice §2.1 y redistribuiría medios sin licencia.
- **Hotlinking a GitHub**: dependencia externa en ejecución, rompe la CSP `img-src 'self'`,
  el uso offline y la privacidad.
- **Convertir a WebP/MP4** para ahorrar ancho de banda: prohibido por la licencia.

## Consecuencias
- El despliegue necesita red la primera vez (o una copia local del dataset en el commit fijado).
- La ingesta es idempotente y verificable por checksums; los medios no requieren copia de
  seguridad (se regeneran).
- Los tests de licencia (componente, E2E de QA y PDF) son obligatorios en CI.

# Auditoría de Definition of Done — MASTER_PROMPT §15

Fecha: 2026-09-28. Auditor: agente `f4/dod-audit` (tarea F4-QA-01 de `docs/TASKS.md`).
Alcance: los 8 puntos de §15 sobre el estado real de `main` (`70a056d`, 212 commits), cruzados
con `docs/handoffs/*.md`, `docs/reviews/*.md`, `docs/TASKS.md`, la rama sin fusionar `f4/docs`
y el historial de ejecuciones de CI en GitHub Actions (`gh run list`). No se han re-ejecutado
suites completas; solo comandos puntuales (`openapi-spec-validator`, `grep`, `gh run view`,
lectura de código y specs).

**Resumen**: de 8 puntos, **2 hechos**, **1 hecho pero con matices que registrar**, **5
abiertos**. El hallazgo más importante es que **la CI de GitHub Actions nunca ha estado en
verde en `main`**: las 27 ejecuciones más recientes (`gh run list --branch main`) son todas
`failure` o `cancelled`, incluida la del commit actual `70a056d` (falla en `typecheck` e
`images`/Trivy).

---

## 1. `make bootstrap && make up` en LXC limpio con 1.324 ejercicios y medios verificados por checksum

**Estado: ABIERTO (parcial).**

- La ingesta y verificación por checksum SHA-256 están hechas y probadas repetidamente:
  `docs/handoffs/f1-ingesta-datos.md` (2.648/2.648 medios verificados, `manifest.json` con
  SHA-256), reconfirmado en `docs/handoffs/f3-devops.md` §5 (`make ingest` sobre Docker Compose
  real: "fetch updated: commit 7455ef…, 1324 ejercicios, medios +2648 -0 ~0, verificados 2648").
- **Lo que falta**: el propio handoff de devops lo deja explícito en "Riesgos y pendientes":
  *"`deploy/lxc/README.md` (...) no se ha podido probar en un LXC de Proxmox real desde este
  entorno (esta caja no es un LXC), solo se ha verificado la pila Docker subyacente."*
  `make bootstrap && make up` se ha ejecutado y verificado en Docker plano, **no en un LXC de
  Proxmox limpio** como exige literalmente el punto de §15.
- Evidencia: `docs/handoffs/f3-devops.md` §5 (tabla de comprobaciones) y §6 (riesgo explícito).

## 2. Atribución de Gym visual visible; medios servidos sin modificar y solo a usuarios autenticados por defecto; Créditos con licencias y SHA

**Estado: HECHO.**

- Atribución obligatoria en el componente único de medios, con lanzamiento de excepción si
  falta: `docs/handoffs/f1-frontend-ui.md` (`ExerciseMedia`, "si el medio no trae la atribución
  exacta, **lanza** en vez de omitirla").
- Servido byte a byte y solo autenticado por defecto, verificado con `curl` real:
  `docs/handoffs/f3-devops.md` §5 — `/media/gifs/<f>` sin cookie → `401`; con sesión válida →
  `200` con `sha256sum` idéntico al fichero de origen; `/media/source/...`, `manifest.json`,
  `LICENSES/` → `404` siempre.
- PDF exportado también lleva atribución en cada página (`docs/handoffs/f2-backend-api.md`,
  "atribución de Gym visual en el pie de **cada** página"; confirmado en
  `docs/TASKS.md` F2-BE-10).
- Créditos con MIT + aviso de medios + SHA del commit ingerido: `docs/handoffs/f1-frontend-ui.md`
  (`ProfileRoute`/`/about`) y `docs/handoffs/f2-frontend-b.md` ("Créditos y licencias (MIT, Gym
  visual, SHA)").
- E2E de licencia en el DOM: `docs/TASKS.md` F3-QA-04 "hecha" ("Falla si falta en cualquier
  pantalla").

## 3. Generador válido para las 1.890 combinaciones de §7.8 y los 12 snapshots aprobados por el experto

**Estado: HECHO, con una matiz de proceso a registrar.**

- Las 1.890 combinaciones pasan de forma reproducible: `docs/handoffs/f1-motor-rutinas.md`
  ("1.890 combinaciones, 0 errores"), repetido en cada handoff posterior del motor
  (`f1b-fix-motor-rutinas.md`, `f1b-close-b5.md`: "Suite completa: 2135 passed, cobertura 100 %").
- Revisión de dominio: `docs/reviews/f1b-experto-entrenamiento.md` encontró 8 BLOQUEANTES;
  `docs/reviews/f1b-reverify.md` confirma 7/8 cerrados con **B5 aún abierto** ("Puerta 1 FAIL").
  El cierre de B5 (ids `2400`/`0720` a `fixture_gated`) está aplicado en
  `docs/handoffs/f1b-close-b5.md` y **verificado en el árbol actual**
  (`specs/engine-rules.yaml` contiene ambos ids; `ENGINE_VERSION = 0.2.1`).
- **Matiz**: no existe en `docs/reviews/` un informe de re-verificación del experto **posterior**
  al cierre de B5 (solo hay `f1b-experto-entrenamiento.md` y `f1b-reverify.md`, este último ya
  con B5 todavía abierto). El cierre de B5 lo certifica el propio equipo de `motor-rutinas` con
  sus tests, no una re-revisión de dominio firmada. Los 12 snapshots están regenerados y en
  verde por tests propios, pero la "aprobación del experto" formal sobre el estado final
  (post-B5) no está documentada como tal.
- Comando usado para confirmar el fix en el árbol: `grep -n "0720\|fixture_gated"
  specs/engine-rules.yaml` → `ids: ["2400", "0720"]`.

## 4. Flujo E2E completo en móvil y escritorio, incluido offline en el reproductor

**Estado: ABIERTO (parcial).**

- Escritorio (Chromium): completo y en verde. `docs/handoffs/f3-qa-tests.md`: "17 pasadas, 1
  fallo real, 1 omitida" — onboarding → generar → activar → entrenar → progreso, offline
  ("Offline indicator" ✅), exportar y dieta.
- **Móvil (WebKit) NO pasa para ningún flujo autenticado**: el propio handoff lo documenta como
  bloqueo reproducible, no como fallo de producto: *"Todo flujo que registra o inicia sesión
  falla en `webkit-mobile` sobre `http://localhost`, siempre"* porque WebKit no guarda la
  cookie `Secure` sin HTTPS real en local. Solo pasan las pantallas sin sesión (Biblioteca, PWA,
  atribución de medios).
- `docs/TASKS.md` marca **F3-QA-01 "hecha"** con criterio literal *"Chromium escritorio + WebKit
  iPhone verdes"* — esto es **inconsistente** con la evidencia del propio handoff de qa-tests,
  que dice explícitamente que WebKit no se puede probar en local y pide decidir la estrategia de
  HTTPS local antes de "exigir WebKit en la Puerta 3". No hay documentado un
  `docker compose` con TLS real donde se haya vuelto a correr Playwright contra WebKit para
  cerrar ese pendiente.
- Sesión offline del reproductor sí está cubierta (IndexedDB, cola de sync, Background Sync):
  `docs/handoffs/f2-frontend-b.md` y confirmado en `f3-qa-tests.md` ("Offline indicator" ✅).

## 5. Dieta desactivable, con suelos de seguridad probados

**Estado: HECHO.**

- Suelos de seguridad probados exhaustivamente: `docs/handoffs/f1-motor-nutricion.md` §Métricas
  ("Bloqueos §8.5 probados: menor de 18, embarazo, lactancia, IMC < 18,5 + `lose`, suelo de
  kcal"), reforzado tras revisión de dominio en `docs/handoffs/f1b-fix-motor-nutricion.md` (barrido
  de 288 perfiles / 2.016 días: 0 alérgenos, 0 días > 35 % grasa, techo de proteína en obesidad).
- Activación en onboarding: `docs/handoffs/f2-frontend-a.md` ("4 pasos + PAR-Q + «activar
  dieta»").
- **Desactivación posterior**: `docs/handoffs/f3-qa-tests.md` señaló como hallazgo abierto que
  "no hay interruptor en Perfil para `diet_enabled` tras el onboarding". Esto se corrigió en el
  commit `9107579` ("Fix 4 frontend gaps: ... diet toggle"), ya en `main`: verificado en el árbol
  actual — `frontend/src/features/profile/ProfileScreen.tsx:105` tiene el checkbox
  `diet_enabled`. Backend ya soportaba `403 diet_disabled`/`422 nutrition_blocked`
  (`docs/TASKS.md` F2-BE-14).

## 6. Umbrales de cobertura, lint, tipos, a11y, Lighthouse y seguridad en verde en CI

**Estado: ABIERTO — el más crítico de los 8 puntos.**

Cada umbral individual está documentado en verde **en ejecuciones locales/por rama** (backend
96,9–100 %, motores 100 %/100 %, frontend 93–95 % líneas, 0 violaciones a11y serias salvo A11Y-1
ya corregido, Lighthouse ≥0,9 en las 3 categorías según `lighthouserc.json` y
`f3-qa-tests.md`, seguridad 0 altos/críticos tras `f3-backend-fixes.md`). **Pero la comprobación
que pide literalmente este punto — verde *en CI* — no se cumple**:

```
$ gh run list --branch main --limit 30 --json databaseId,conclusion,displayTitle,createdAt
```
Las 27 ejecuciones más recientes en `main` son `failure` (17) o `cancelled` (10). **Ninguna
ejecución de CI en `main` ha terminado en éxito** en todo el historial consultado. La más
reciente, sobre el commit actual `70a056d` (`gh run view 36364769858`):

- Job `lint`: ✓ verde.
- Job `images`: ✗ — Trivy falla en la imagen `web` por CVEs `HIGH/CRITICAL` corregibles en
  `openssl`, `libxml2`, `musl`, `nghttp2-libs`, `zlib` de la base `nginx-unprivileged:1.27-alpine`
  (paquetes desactualizados en la imagen base, no en el código de Forja).
- Job `typecheck`: ✗ — `tsc --strict` falla en `frontend/scripts/gate2-live.mjs`
  (`Object literal may only specify known properties, and 'baseURL' does not exist in type...`,
  un script de Playwright fuera de la app que quedó con un error de tipos de una versión de
  Playwright distinta a la de `devDependencies`).
- Jobs `unit`, `integration`, `build`, `e2e`, `lighthouse`, `coverage`, `smoke-compose`: no
  llegaron a ejecutarse (dependían de `typecheck`).

Esto significa que, aunque cada pieza individual se ha verificado en verde por separado en su
rama de origen, **la puerta de CI unificada que exige §15 nunca se ha cerrado en verde sobre el
estado combinado de `main`**. Es la brecha más seria de esta auditoría porque toca directamente
la redacción literal del punto.

## 7. Sin `TODO`/placeholders (grep en CI), sin secretos en el repo

**Estado: HECHO.**

- `grep -rnE '\bTODO\b|\bFIXME\b' --include="*.py" --include="*.ts" --include="*.tsx" backend
  engine nutrition frontend/src` → 0 resultados.
- Los únicos `# type: ignore` presentes están justificados inline por comentario (regla de §2.2
  "sin `# type: ignore` sin justificación"), p. ej. `backend/app/services/auth.py:57-59`
  (`# validado por CHECK en BD`), `backend/app/services/exports.py:100,142`
  (`# weasyprint sin tipos`).
- `make lint-placeholders` existe como objetivo dedicado (`Makefile`) y se reporta en verde en
  todos los handoffs que lo ejecutan (arquitecto, ingesta, devops).
- Sin `.env` versionado (`git ls-files | grep '^\.env$'` → vacío); no se encontraron secretos
  literales fuera de fixtures/ejemplos con el grep de `SECRET_KEY=`/`password=`.
- **Nota de alcance**: `docs/TASKS.md` marca **F3-QA-05 "pendiente"**: *"Ampliar la comprobación
  de marcadores prohibidos a tests y documentación de usuario si procede"*. El `grep` actual de
  `lint-placeholders` no cubre explícitamente `docs/` ni `frontend/e2e`/`tests/`; no se ha
  encontrado ningún TODO real en esas rutas al inspeccionarlas, pero la ampliación formal del
  target sigue sin hacer.

## 8. Documentación: README.md, docs/USER_GUIDE.md (ES), deploy/lxc/README.md, ADRs, CHANGELOG.md

**Estado: ABIERTO (parcial) — resuelto por este mismo trabajo en cuanto a README.**

- `deploy/lxc/README.md`: existe y está completo (`docs/handoffs/f3-devops.md`).
- ADRs: 12 ADRs (`0001`–`0012`) + `docs/adr/README.md`, cubren todas las decisiones citadas en
  los handoffs (verificado con `ls docs/adr/`).
- `docs/USER_GUIDE.md` y `CHANGELOG.md`: **escritos pero no fusionados a `main`**. Viven en la
  rama local `f4/docs` (commits `3b1a987`, `20a11cf`, `ccc1bc8`), confirmados con
  `git diff --stat main f4/docs` (`CHANGELOG.md` +242 líneas, `docs/USER_GUIDE.md` +378
  líneas), pero **no existen en `main`** (`ls docs/USER_GUIDE.md` y `ls CHANGELOG.md` fallan
  sobre el árbol de trabajo actual). `docs/TASKS.md` lo confirma: **F4-ORQ-01 "pendiente"**.
- `README.md`: era el provisional del arquitecto ("Estado: Fase 0 (fundaciones) completada
  (...) este README se completa en la Fase 4"). **Sustituido en esta misma auditoría** (ver
  commit de esta rama) por una versión final que enlaza a `docs/USER_GUIDE.md`,
  `deploy/lxc/README.md` y `CHANGELOG.md`, e incluye el aviso de licencia de medios de §2.1.
  Como `docs/USER_GUIDE.md`/`CHANGELOG.md` siguen sin fusionar a `main`, los enlaces del nuevo
  README apuntarán a rutas válidas solo una vez que `f4/docs` (o su contenido) se fusione;
  hasta entonces son enlaces rotos en `main`. **Pendiente del orquestador**: fusionar `f4/docs`
  (o repetir su contenido) antes o junto con este trabajo.
- `docs/TASKS.md` **F4-ORQ-02 "pendiente"**: README definitivo + tag `v1.0.0`. Esta auditoría
  resuelve la parte de README (sujeta a la fusión de `f4/docs` de arriba); el tag `v1.0.0`
  **no se crea aquí** por instrucción explícita de la tarea ("no tagees").

---

## Resumen ejecutivo

| # | Punto de §15 | Estado |
|---|---|---|
| 1 | `make bootstrap && make up` en LXC limpio + checksums | **Abierto** (probado en Docker, no en LXC real) |
| 2 | Atribución Gym visual + medios autenticados + Créditos | **Hecho** |
| 3 | Generador 1.890 combinaciones + 12 snapshots aprobados | **Hecho** (matiz: sin re-firma formal del experto tras el último fix de B5) |
| 4 | E2E móvil + escritorio + offline | **Abierto** (WebKit móvil autenticado no pasa en ningún entorno probado) |
| 5 | Dieta desactivable + suelos probados | **Hecho** |
| 6 | Umbrales verdes **en CI** | **Abierto** (ninguna ejecución de CI en `main` ha sido exitosa; el commit actual falla en `images`/Trivy y en `typecheck`) |
| 7 | Sin TODO/placeholders, sin secretos | **Hecho** (con alcance de `lint-placeholders` aún sin ampliar a docs/tests, F3-QA-05) |
| 8 | README, USER_GUIDE, deploy/lxc/README, ADRs, CHANGELOG | **Abierto** (USER_GUIDE y CHANGELOG solo en `f4/docs`, sin fusionar; README resuelto en esta rama) |

**Puntos abiertos: 4 de 8 (1, 4, 6, 8)** — más un matiz de proceso en el punto 3 y un cabo suelto
de alcance en el punto 7. El bloqueador más importante para poder etiquetar `v1.0.0` es el punto
6 (CI roja en `main`); el más rápido de cerrar es el punto 8 (fusionar `f4/docs`).

## Tareas nuevas recomendadas (para `docs/TASKS.md`, fuera del alcance de esta auditoría)

- **F4-QA-02**: arreglar `frontend/scripts/gate2-live.mjs` (error de tipos `baseURL`) o excluirlo
  correctamente de `tsc --strict` en CI; investigar por qué el `exclude` de
  `frontend/eslint.config.js` (mencionado en `docs/handoffs/f2-frontend-integration.md`) no
  cubre también el paso de `typecheck` del CI.
- **F4-OPS-01**: actualizar la imagen base `nginxinc/nginx-unprivileged` (o congelar una versión
  reciente) para resolver los CVEs `HIGH/CRITICAL` de Trivy en el job `images`.
- **F4-QA-03**: decidir y ejecutar la estrategia de HTTPS local (o contra `deploy/docker-compose.yml`
  con TLS) para poder correr de verdad el proyecto `webkit-mobile` de Playwright en flujos
  autenticados, y corregir la etiqueta "hecha" de F3-QA-01 en `docs/TASKS.md` si no se logra
  antes de la Puerta 3.
- **F4-ORQ-03**: fusionar `f4/docs` (`CHANGELOG.md`, `docs/USER_GUIDE.md`) a `main`.
- **F4-EXP-01**: pedir a `experto-entrenamiento` una re-verificación breve y firmada de los 12
  snapshots tras el cierre de B5 (`f1b/close-b5`, `ENGINE_VERSION 0.2.1`), ya que la única
  re-revisión de dominio documentada (`docs/reviews/f1b-reverify.md`) es anterior a ese fix.
- **F3-QA-05** (ya existente, sigue pendiente): ampliar `make lint-placeholders` a `docs/` y
  `frontend/e2e`/`tests/`.

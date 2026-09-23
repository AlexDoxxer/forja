# ADR 0010 · CI en GitHub Actions y puertas de calidad

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
§13 define la cadena de CI (lint → tipos → unit → integración → build → E2E → Lighthouse →
cobertura) y §2.2 umbrales distintos para líneas y ramas. coverage.py solo admite un umbral
combinado. §4.2 permite GitHub Actions o Gitea (por ADR).

## Decisión
- **GitHub Actions** en `.github/workflows/ci.yml` (la sintaxis es compatible con Gitea
  Actions si el propietario migra; en ese caso se copia a `.gitea/workflows/`).
- Trabajos encadenados con `needs`: `lint` → `typecheck` → `unit` → `integration` → `build`
  → `e2e` → `lighthouse` → `coverage`. Todos ejecutan comprobaciones reales desde la Fase 0:
  - `lint`: ruff (check + format) por paquete, ESLint, validación de `contracts/openapi.yaml`
    y búsqueda de marcadores prohibidos (`TODO`, `FIXME`, `XXX`, `NotImplementedError`,
    `lorem ipsum`) en código de producción.
  - `typecheck`: mypy `--strict` por paquete y `tsc` estricto.
  - `unit`: motores (con umbral), backend sin Docker (unit + contrato) y Vitest (umbral 85 %).
  - `integration`: suite completa del backend con testcontainers (Docker del runner) y
    umbral de cobertura del backend.
  - `build`: wheels de los tres paquetes y bundle de producción del frontend. `devops-despliegue`
    añade la construcción de imágenes Docker y Trivy en Fase 3.
  - `e2e`: Playwright (Chromium escritorio + WebKit móvil) contra `vite preview`; en Fase 3
    `qa-tests` lo apunta a `docker compose` con `E2E_BASE_URL`.
  - `lighthouse`: Lighthouse CI (`frontend/lighthouserc.json`) con Rendimiento,
    Accesibilidad y Buenas prácticas ≥ 0,9.
  - `coverage`: publica el resumen de cobertura de todos los paquetes en el *job summary*.
- **Umbrales exactos** con `scripts/coverage_gate.py` sobre `coverage.json`: motores 100 %
  líneas y ≥ 95 % ramas; backend ≥ 90 % líneas y ≥ 90 % ramas. Además, `fail_under`
  combinado en cada `pyproject.toml` y `thresholds` de Vitest (85 % en las cuatro métricas).
- **Categoría PWA de Lighthouse**: desde Lighthouse 12 ya no existe. El criterio «PWA ≥ 90» de
  §10.5 se sustituye por comprobaciones equivalentes que `qa-tests` añade en Fase 3
  (manifest válido con iconos *maskable*, service worker que controla la página, arranque
  offline) en Playwright.
- Locales: `make lint typecheck test` reproduce `lint`, `typecheck`, `unit` e `integration`;
  `make e2e` reproduce `e2e`.

## Alternativas
- **Un solo trabajo secuencial**: más simple, pero sin paralelismo futuro ni informes por fase.
- **Umbral combinado únicamente**: no garantiza «100 % líneas y ≥ 95 % ramas» de §2.2.

## Consecuencias
- La CI tarda más que un único trabajo (instalaciones repetidas), mitigado con cachés de uv y
  npm.
- `devops-despliegue` y `qa-tests` amplían la CI sin reestructurarla (ADR 0002).

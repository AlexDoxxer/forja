# Progreso de Forja

## Fase 0 · Fundaciones — completada (2026-09-23)
- **Hecho**: monorepo §4.2 (backend, engine, nutrition con uv/ruff/mypy --strict/pytest;
  frontend Vite + TS estricto + ESLint + Vitest + Playwright), `contracts/openapi.yaml`
  (OpenAPI 3.1, 59 rutas, 71 operaciones), `contracts/domain.md`, ADR 0001–0010,
  `docs/TASKS.md`, CI en `.github/workflows/ci.yml`.
- **Métricas**: `make lint typecheck test` en verde (verificado por el orquestador);
  cobertura 100 % en todos los paquetes del esqueleto; `openapi-spec-validator` OK.
- **Decisiones**: el orquestador aprueba las 7 rutas añadidas en ADR 0009 y la lectura
  `DELETE /body-metrics/{metric_id}`; se acepta ADR 0010 (la categoría PWA de Lighthouse ya
  no existe; se sustituye por comprobaciones de manifest/SW/offline en Playwright).
  Contratos congelados con el tag `contracts-v1`.
- **Riesgos abiertos**: CI aún no ejecutado en GitHub; npm 9 del sistema falla en
  `npm install` (usar npm ≥ 10, ADR 0008).

## Fase 1 y 1b · Núcleo y revisión de dominio — completadas (2026-09-26)
- **Hecho**: ingesta (1.324 ejercicios, 2.648 medios verificados, nombres ES 100 %), motor de
  rutinas 0.2.1, motor de nutrición 0.2.1, shell de frontend.
- **Puerta 1**: revisión del experto con 8 bloqueantes; todos cerrados. B5 (`0720`, `0970`,
  `2400` fuera de presets sin equipamiento) verificado por el orquestador: ninguno aparece en
  los goldens 01, 06, 07 y 08. Barrido de nutrición de 288 perfiles: 0 días > 35 % grasa,
  0 violaciones de alérgenos, `tolerance_not_met` 4,2 %.
- **Decisiones**: CC-0001 a CC-0004 aprobados (contrato 1.2.0); ADR 0011 (`specs/nutrition.yaml`
  fuente única) y ADR 0012 (`loadable_in_main: +10`).
- **Riesgos abiertos** (cambios, no bloqueantes): déficits de volumen semanal avisados en 10 de
  12 snapshots; sésamo, mostaza y apio sin valor de alérgeno (no se seleccionan solos);
  propuesta pendiente `pullup_bar`/`bench` en `EquipmentCode`; prioridad de hueco limitada a 3.

## Fase 2 · Integración — en curso
- Backend (59 rutas, contrato 1.2.0), frontend A y B fusionados; integración con API real y
  Puerta 2 en `f2/frontend-integration`.

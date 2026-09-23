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

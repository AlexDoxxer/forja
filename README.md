# Forja

Aplicación web de entrenamiento **autoalojada** (PWA) para uso personal o familiar: biblioteca
de 1.324 ejercicios con GIF e instrucciones en 10 idiomas, generador determinista de rutinas
según objetivo, días, sexo, nivel y equipamiento, reproductor de sesión que funciona sin
conexión, seguimiento del progreso y un módulo opcional de dieta.

> **Estado**: Fase 0 (fundaciones) completada: monorepo, contratos, ADRs y CI. La aplicación
> se construye por fases según `ORCHESTRATION.md`; este README se completa en la Fase 4.

## Documentación

| Documento | Contenido |
|---|---|
| [`MASTER_PROMPT.md`](MASTER_PROMPT.md) | Especificación completa (fuente de verdad) |
| [`ORCHESTRATION.md`](ORCHESTRATION.md) | Fases, puertas y protocolo entre agentes |
| [`CLAUDE.md`](CLAUDE.md) | Reglas del proyecto para agentes |
| [`contracts/openapi.yaml`](contracts/openapi.yaml) | Contrato de la API (OpenAPI 3.1) |
| [`contracts/domain.md`](contracts/domain.md) | Modelo de dominio, enumeraciones y DTOs de los motores |
| [`docs/adr/`](docs/adr/README.md) | Decisiones de arquitectura |
| [`docs/TASKS.md`](docs/TASKS.md) | Tablero de tareas por fase y agente |
| [`docs/CONTRACT_CHANGES.md`](docs/CONTRACT_CHANGES.md) | Propuestas y resoluciones de cambios de contrato |
| [`docs/dataset-analysis.md`](docs/dataset-analysis.md) | Análisis del dataset de origen |

## Estructura

```
contracts/   Contrato OpenAPI y modelo de dominio
specs/       Tablas YAML del motor (splits, volumen, prescripción, nutrición…)
backend/     API FastAPI (app/), migraciones Alembic y pipeline de ingesta (ingest/)
engine/      forja_engine: motor de rutinas puro y determinista
nutrition/   forja_nutrition: motor de nutrición puro y determinista
frontend/    PWA React + TypeScript + Vite (tests en tests/, E2E en e2e/)
deploy/      Docker Compose, nginx, Proxmox LXC, copias de seguridad
docs/        ADRs, tablero, handoffs y análisis
scripts/     Utilidades de calidad del monorepo
```

## Desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/) (instala Python 3.12), Node 20.19+ con npm 10+ y
Docker (tests de integración con testcontainers).

```bash
make install      # dependencias exactas (uv.lock y package-lock.json)
make lint         # ruff, ESLint, validación del contrato OpenAPI y marcadores prohibidos
make typecheck    # mypy --strict y tsc estricto
make test         # tests con umbrales de cobertura (motores 100 %/95 %, backend 90 %, frontend 85 %)
make e2e          # Playwright (requiere `npx playwright install` en frontend/)
make help         # todos los objetivos
```

Configuración exclusivamente por variables de entorno: copia `.env.example` a `.env`. Los
objetivos de despliegue (`make bootstrap`, `make up`, `make ingest`, copias de seguridad) y la
guía para Proxmox LXC llegan en la Fase 3 (`deploy/`).

## Licencias y medios

- Los **datos** del dataset [`hasaneyldrm/exercises-dataset`](https://github.com/hasaneyldrm/exercises-dataset)
  (nombres, músculos, equipamiento, instrucciones y traducciones) son **MIT**.
- Los **medios** (GIF y miniaturas) son **© Gym visual — https://gymvisual.com/**, se
  redistribuyen con permiso a 180×180 y **no** están cubiertos por MIT. No se versionan en
  este repositorio: se descargan en el despliegue desde un commit fijado, se sirven sin
  modificar, solo a usuarios autenticados por defecto, y siempre con la atribución visible.
  Clonar este repositorio no concede ninguna licencia sobre ellos. Antes de exponer Forja
  públicamente, revisa los [términos de Gym visual](https://gymvisual.com/content/3-terms-and-conditions-of-use).

## Aviso sanitario

Forja no sustituye el consejo de profesionales sanitarios, de entrenamiento ni de nutrición.

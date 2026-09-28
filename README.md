# Forja

Aplicación web de entrenamiento **autoalojada** (PWA): biblioteca de 1.324 ejercicios con GIF e
instrucciones en 10 idiomas, generador determinista de rutinas según objetivo, días, sexo, nivel
y equipamiento, reproductor de sesión que funciona sin conexión, seguimiento del progreso y un
módulo opcional de dieta.

## Empezar

- **¿Vas a usar Forja?** Lee la [guía de usuario](docs/USER_GUIDE.md): qué hace la app, cómo
  generar y entrenar tu primera rutina, la dieta opcional y el módulo de progreso.
- **¿Vas a desplegarla en tu propio servidor?** Sigue la [guía de despliegue en Proxmox
  LXC](deploy/lxc/README.md) (Docker Compose + nginx, backups y actualización).
- **¿Quieres ver qué ha cambiado en cada versión?** Consulta el [`CHANGELOG.md`](CHANGELOG.md).

## Documentación técnica

| Documento | Contenido |
|---|---|
| [`MASTER_PROMPT.md`](MASTER_PROMPT.md) | Especificación completa (fuente de verdad) |
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Guía de usuario en español |
| [`deploy/lxc/README.md`](deploy/lxc/README.md) | Despliegue en Proxmox LXC |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de versiones |
| [`contracts/openapi.yaml`](contracts/openapi.yaml) | Contrato de la API (OpenAPI 3.1) |
| [`contracts/domain.md`](contracts/domain.md) | Modelo de dominio, enumeraciones y DTOs de los motores |
| [`docs/adr/`](docs/adr/README.md) | Decisiones de arquitectura |
| [`docs/DOD_REPORT.md`](docs/DOD_REPORT.md) | Auditoría de Definition of Done (§15) |

## Estructura del repositorio

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

Configuración exclusivamente por variables de entorno: copia `.env.example` a `.env`.

## Despliegue

```bash
deploy/scripts/init-env.sh   # crea .env con secretos generados
make bootstrap                # construye imágenes y prepara la base de datos
make up                       # levanta la pila (db, api, web)
make ingest                   # descarga y carga el catálogo de ejercicios
```

Detalle completo (Proxmox LXC, TLS, copias de seguridad y restauración, variables de entorno)
en [`deploy/lxc/README.md`](deploy/lxc/README.md).

## Licencias y medios

- Los **datos** del dataset [`hasaneyldrm/exercises-dataset`](https://github.com/hasaneyldrm/exercises-dataset)
  (nombres, músculos, equipamiento, instrucciones y traducciones) son **MIT**.
- Los **medios** (imágenes y vídeos) son **© Gym visual — https://gymvisual.com/**, usados con
  permiso escrito del titular. **No** están cubiertos por la licencia MIT del dataset. Se
  redistribuyen únicamente a **180×180 px**, sin reescalar, recodificar, recortar, convertir de
  formato ni marcar de agua; se sirven **byte a byte tal cual**. Toda vista que muestre un medio
  incluye la atribución **«© Gym visual — https://gymvisual.com/»** de forma visible. Los medios
  **no se versionan** en este repositorio: se obtienen en el despliegue desde el repositorio de
  origen en un commit fijado y se verifican por checksum. Clonar este repositorio **no concede
  ninguna licencia** sobre los medios: la aplicación está pensada para **uso privado
  autoalojado**, y por defecto los medios solo se sirven a usuarios autenticados. Si vas a exponer
  tu instancia de Forja públicamente, revisa antes los
  [términos y condiciones de Gym visual](https://gymvisual.com/content/3-terms-and-conditions-of-use)
  y obtén tu propia licencia.

## Aviso sanitario

Forja no sustituye el consejo de profesionales sanitarios, de entrenamiento ni de nutrición.

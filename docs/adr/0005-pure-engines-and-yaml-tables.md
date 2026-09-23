# ADR 0005 · Motores puros y tablas YAML versionadas

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
§7 y §8 exigen motores deterministas (misma entrada + semilla + tablas ⇒ misma salida byte a
byte), 100 % de cobertura de líneas y constantes revisables por un experto sin tocar código.

## Decisión
- `forja_engine` y `forja_nutrition` son **paquetes Python independientes** (`engine/`,
  `nutrition/`) sin E/S: ni BD, ni red, ni reloj (`datetime.now`), ni variables de entorno, ni
  `random` global. La aleatoriedad usa `random.Random(seed_derivado)` sembrado por
  (seed, semana, día, slot); la nutrición solo lee `data/foods.json` empaquetado.
- Todas las constantes viven en `specs/*.yaml`, versionadas (`version:` en cada fichero). Se
  cargan y validan con Pydantic al importar/cargar (fallo rápido ante YAML inválido o
  referencias rotas). `tables_hash` = SHA-256 del JSON canónico de las tablas cargadas.
- Los DTOs son Pydantic `frozen=True, extra="forbid"` y su forma JSON coincide con
  `contracts/openapi.yaml` (`contracts/domain.md` §5–§6).
- Cada programa persiste `generator_input`, `generator_version` (`ENGINE_VERSION`),
  `tables_hash` y `seed`, de modo que se puede reproducir o auditar.
- Los motores **no** dependen del backend; el backend depende de ellos como dependencias de
  ruta editables (`[tool.uv.sources]`). Cada motor tiene su propio entorno virtual, de modo que
  importar por error una dependencia no declarada (SQLAlchemy, FastAPI) falla en sus tests.
- Cualquier cambio que altere la salida para una entrada y semilla dadas incrementa la
  versión semver del motor y regenera los snapshots golden con revisión del experto.

## Alternativas
- **Constantes en código**: más sencillo de tipar, pero el experto no puede revisarlas ni
  proponer diffs sin programar.
- **Tablas en BD**: editables en caliente, pero rompen el determinismo reproducible y
  complican los tests puros.
- **Un único paquete con API y motores**: menos ficheros `pyproject.toml`, pero sin garantía
  estructural de pureza.

## Consecuencias
- Los motores se prueban con fixtures congeladas en milisegundos (1.890 combinaciones).
- La imagen del backend debe incluir `specs/` (lo resuelve `devops-despliegue`).
- Las tablas YAML son parte del contrato funcional; su cambio pasa por revisión del experto.

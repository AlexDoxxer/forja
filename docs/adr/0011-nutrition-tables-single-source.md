# ADR 0011 · `specs/nutrition.yaml` es la fuente de las tablas de nutrición

- **Estado**: Aceptado · **Fecha**: 2026-09-26 · **Autor**: arquitecto

## Contexto
`specs/nutrition.yaml` (revisado por el experto) y `nutrition/forja_nutrition/data/nutrition.yaml`
(empaquetado, sin depender del repo en tiempo de ejecución; ADR 0005) deben ser idénticos y hoy
nada lo comprueba.

## Decisión
- La **fuente** es `specs/nutrition.yaml`; la copia empaquetada es derivada y no se edita a mano.
- Un test de contrato (`backend/tests/contract/test_nutrition_tables_sync.py`) falla si difieren byte a byte.
- Se descarta generar la copia en el build: añade un paso y oculta la divergencia en lugar de detectarla.

## Consecuencias
Cambiar las tablas exige copiar el fichero (`cp specs/nutrition.yaml nutrition/forja_nutrition/data/`).

# Forja — reglas del proyecto

App web autoalojada de entrenamiento basada en `hasaneyldrm/exercises-dataset`.
**Fuente de verdad: `MASTER_PROMPT.md`.** Coordinación: `ORCHESTRATION.md`.

## Siempre
- Lee `MASTER_PROMPT.md` y las secciones de tu rol antes de actuar; consulta `specs/` y
  `contracts/` en lugar de inventar valores.
- Código de producción: sin TODO, sin placeholders, sin datos simulados en rutas reales.
- UI y documentación de usuario en español; código, rutas, tablas y commits en inglés.
- Ejecuta lint, tipos y tests de tu zona antes de terminar; respeta los umbrales de cobertura.
- Escribe tu handoff en `docs/handoffs/` y actualiza `docs/TASKS.md`.

## Nunca
- Modificar, reescalar o recodificar los medios de Gym visual, ni mostrarlos sin la
  atribución «© Gym visual — https://gymvisual.com/».
- Versionar los medios en este repo (se obtienen en el despliegue por commit fijado).
- Cambiar un contrato de `contracts/` sin aprobación (usa `docs/CONTRACT_CHANGES.md`).
- Escribir fuera de tu directorio asignado (ADR 0002).
- Usar el sexo del usuario para excluir ejercicios o limitar cargas.

## Comandos
`make lint` · `make typecheck` · `make test` · `make up` · `make ingest`

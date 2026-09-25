# Cambios de contrato

Registro de propuestas de cambio sobre `contracts/openapi.yaml`, `contracts/domain.md` y la
forma de los DTOs compartidos (MASTER_PROMPT §0, ADR 0002). **Ningún agente cambia un
contrato en silencio.**

## Procedimiento

1. El agente que necesita el cambio añade una entrada al final de «Registro» con estado
   `propuesto`, usando la plantilla. No modifica `contracts/` en su rama.
2. El arquitecto la resuelve (`aprobado` o `rechazado`, con motivo) en el siguiente ciclo de
   orquestación. Si la aprueba:
   - actualiza en un mismo commit `contracts/openapi.yaml`, `contracts/domain.md` y
     `backend/tests/contract/test_openapi_contract.py`;
   - incrementa `info.version` (menor si es compatible: campo opcional nuevo, endpoint nuevo,
     valor de enumeración nuevo en una salida; mayor si rompe clientes existentes, con ADR);
   - anota la versión resultante en la entrada y avisa a los agentes afectados en su handoff.
3. El orquestador etiqueta cada versión congelada (`contracts-v1`, `contracts-v1.1`, …).

## Plantilla

```markdown
### CC-NNNN · <título corto>
- **Estado**: propuesto | aprobado | rechazado
- **Propone**: <agente> · **Fecha**: AAAA-MM-DD
- **Afecta a**: <esquemas/endpoints/secciones de domain.md>
- **Motivo**: <necesidad real, con referencia a MASTER_PROMPT/ADR>
- **Cambio propuesto**: <diff o descripción exacta>
- **Compatibilidad**: compatible | incompatible (por qué)
- **Resolución**: <arquitecto: decisión, motivo, versión resultante, agentes avisados>
```

## Registro

### CC-0000 · Versión inicial del contrato
- **Estado**: aprobado
- **Propone**: arquitecto · **Fecha**: 2026-09-23
- **Afecta a**: `contracts/openapi.yaml` y `contracts/domain.md` completos
- **Motivo**: Fase 0 (ORCHESTRATION.md §3). Cubre todos los endpoints de §9 más las
  ampliaciones justificadas en ADR 0009 (`/auth/csrf`, `/auth/sessions`,
  `/auth/sessions/{auth_session_id}`, `/about`, `/generator/preview/regenerate-day`,
  `/generator/preview/swap`, `GET /nutrition/plans`).
- **Cambio propuesto**: creación.
- **Compatibilidad**: no aplica (primera versión).
- **Resolución**: aprobado como **1.0.0**; pendiente de congelar con el tag `contracts-v1`
  por el orquestador (tarea F0-ORQ-01).

### CC-0001 · Orden estable de `exercise_secondary_muscle`
- **Estado**: propuesto
- **Propone**: ingesta-datos · **Fecha**: 2026-09-24
- **Afecta a**: `contracts/domain.md` §4.1 (`exercise_secondary_muscle`)
- **Motivo**: `ExerciseCard.secondary_muscles` exige «sin duplicados, orden estable»
  (§5.1), pero la tabla solo tiene PK(`exercise_id`, `muscle_code`) y no conserva el orden
  del dataset. Sin él, el catálogo reconstruido desde la BD (caché de `backend-api`) no sería
  idéntico al exportado por `forja-ingest export-cards` y los planes podrían variar.
- **Cambio propuesto**: añadir `position smallint not null` (0…n-1, orden del dataset tras
  normalizar y deduplicar) a `exercise_secondary_muscle`. Ya implementado en
  `backend/app/models/catalog.py` y en `forja-ingest load`.
- **Compatibilidad**: compatible (columna nueva en una tabla que solo escribe la ingesta; no
  cambia la API).
- **Resolución**: _pendiente del arquitecto_.

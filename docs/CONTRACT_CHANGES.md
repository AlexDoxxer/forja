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
- **Estado**: aprobado
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
- **Resolución**: Aprobado; columna `position` añadida a `domain.md` §4.1. Versión resultante **1.1.0**, 2026-09-26 (arquitecto). Avisados: ingesta-datos/backend-api (CC-0001), motor-nutricion (CC-0002), motor-rutinas (CC-0003) en `docs/handoffs/f2-arquitecto.md`.

### CC-0002 · Alérgeno `peanuts` en `Allergen`
- **Estado**: aprobado
- **Propone**: motor-nutricion · **Fecha**: 2026-09-25
- **Afecta a**: enumeración `Allergen` (`contracts/domain.md` §3, `contracts/openapi.yaml`), `NutritionInput.allergens`, `Food.allergens`.
- **Motivo**: MASTER_PROMPT §8.1 lista «frutos secos» como alérgeno, pero el cacahuete es una
  legumbre, no un fruto seco de árbol, y es uno de los alérgenos más frecuentes. Con el
  contrato actual el motor no puede etiquetar `cacahuete` ni `mantequilla_cacahuete` como
  alérgenos y solo se pueden evitar con `excluded_food_ids`.
- **Cambio propuesto**: añadir el valor `peanuts` a `Allergen` (7 → 8 valores) y etiquetarlo
  en `cacahuete` y `mantequilla_cacahuete` de `foods.json`. Interfaz de usuario: «cacahuete».
- **Compatibilidad**: compatible (valor de enumeración nuevo en entrada y salida; los clientes
  existentes no lo envían). Requiere versión menor.
- **Resolución**: Aprobado; `peanuts` añadido a `Allergen` en `domain.md` y `openapi.yaml`. Versión resultante **1.1.0**, 2026-09-26 (arquitecto). Avisados: ingesta-datos/backend-api (CC-0001), motor-nutricion (CC-0002), motor-rutinas (CC-0003) en `docs/handoffs/f2-arquitecto.md`.

### CC-0003 · Códigos de aviso específicos para ejercicios excluidos, evitados o inexistentes
- **Estado**: aprobado
- **Propone**: motor-rutinas · **Fecha**: 2026-09-25
- **Afecta a**: `PlanWarningCode` (`contracts/openapi.yaml`, `contracts/domain.md` §3 y §5.3)
- **Motivo**: `validate_plan` debe detectar ejercicios excluidos, con músculo objetivo o
  patrón evitado e ids que ya no existen en el catálogo (domain.md §5.3), pero la
  enumeración no tiene códigos para ellos. Mientras tanto el motor usa, con `message_es`
  preciso, `avoided_muscle_substituted` (excluido/evitado) y `deprecated_exercise` (id
  inexistente), lo que obliga al frontend a distinguir por texto.
- **Cambio propuesto**: añadir a `PlanWarningCode` los valores `excluded_exercise`,
  `avoided_exercise` y `unknown_exercise`. Al aprobarse, el motor los emitirá en
  `forja_engine/ops.py::_exercise_violations` (cambio de una línea por caso).
- **Compatibilidad**: compatible (valores nuevos en una enumeración de salida ⇒ versión menor).
- **Resolución**: Aprobado; tres códigos añadidos a `PlanWarningCode` en `domain.md` y `openapi.yaml`. Versión resultante **1.1.0**, 2026-09-26 (arquitecto). Avisados: ingesta-datos/backend-api (CC-0001), motor-nutricion (CC-0002), motor-rutinas (CC-0003) en `docs/handoffs/f2-arquitecto.md`.

### CC-0004 · Semántica de `tolerance_not_met` y campos de realismo en `Food`
- **Estado**: aprobado (2026-09-26, orquestador; aplicado en contrato 1.2.0)
- **Propone**: motor-nutricion · **Fecha**: 2026-09-26
- **Afecta a**: `contracts/domain.md` §6.2 (`MealPlan`, `Food`) y `contracts/openapi.yaml` (`Food`).
- **Motivo**: revisión F1b (Riesgo 5, B7, decisión 5). Con la regla actual («kcal ±5 % y macros ±10 %
  o aviso») el aviso salía en 286 de 288 planes y dejó de informar. No se sube la tolerancia.
- **Cambio propuesto**:
  1. `MealPlan`: `tolerance_not_met` se emite solo si algún día se sale de kcal ±5 %, de proteína
     ±10 % o supera el techo de grasa del 35 % de las kcal del día (salvo que el propio objetivo de
     grasa ya lo supere por el suelo de seguridad). La desviación de grasa y carbohidratos deja de
     generar aviso; `MacroDeviation` sigue informándola.
  2. `Food` (`foods.json`): campos nuevos `max_portion_g: number > 0`, `meal_slots: MealSlot[]`
     (vacío = no se selecciona automáticamente) y `weekly_max: integer | null`.
- **Compatibilidad**: compatible (campos de salida opcionales nuevos; el aviso se emite con menos
  frecuencia). Requiere versión menor.
- **Resolución**: aprobado y aplicado por arquitecto (2026-09-26): `domain.md` §6.2/§8, `openapi.yaml` `Food`, contrato 1.2.0.

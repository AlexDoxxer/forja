# ADR 0012 · Puntuación `loadable_in_main` en la selección de slots principales

- **Estado**: Aceptado · **Fecha**: 2026-09-26 · **Autor**: motor-rutinas (aprobado por experto-entrenamiento, informe F1b, Riesgo 4)

## Contexto
MASTER_PROMPT §7.2 paso 5 no incluye ninguna bonificación por tipo de material. Sin ella, un slot
principal de gimnasio podía resolverse con flexión de rodillas o con banda, algo indefendible. El
motor añadió `scoring.loadable_in_main: +10` para preferir material que admite carga progresiva.
El experto la aprobó como extensión de §7.2, con condiciones, y exigió documentarla.

## Decisión
- Se acepta `scoring.loadable_in_main: +10` para candidatos de slots `main` cuyo `equipment_code`
  está en `loadable_equipment` **del nivel** del usuario (`engine-rules.yaml`):
  - `beginner`: `dumbbell, machine, smith, sled, cable, kettlebell` (sin barra libre: técnica y
    seguridad; máquina y goblet enseñan el patrón).
  - `intermediate` y `advanced`: los anteriores más `barbell, ez_bar, trap_bar, weighted`.
- No se aplica con objetivo `endurance` (los circuitos con peso corporal son válidos). Con banda o
  peso corporal como único material disponible no hay competencia, así que el efecto es nulo.
- Complemento (C5): `scoring.barbell_in_strength_main: +10` para `barbell`/`trap_bar` en slots
  `main` con objetivo `strength` e intermedio/avanzado (`strength_main_preferred_equipment`).
- Revalidación: el síntoma que la motivó era en parte consecuencia del filtro de grupo por
  `target_muscle` (B1). Tras corregir B1 (grupo de entrenamiento por patrón en compuestos) se
  regeneraron los snapshots y los slots principales de gimnasio siguen resolviéndose con barra,
  máquina o mancuernas sin depender de esta puntuación como parche.

## Consecuencias
- Los valores viven en `specs/engine-rules.yaml` y entran en `tables_hash`.
- Cambiar la lista por nivel o los pesos exige revisión del experto y subir `ENGINE_VERSION`.

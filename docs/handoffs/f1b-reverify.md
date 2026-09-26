# Handoff · F1b-REVERIFY · experto-entrenamiento

Rama `f1b/reverify` (sin fusionar). Solo documentación: `docs/reviews/f1b-reverify.md` y este handoff.

## Resultado

Puerta 1 **FAIL**: 7 de 8 BLOQUEANTES cerrados; B5 abierto por una fuga.

| Abierto | Propietario | Corrección exacta |
|---|---|---|
| B5: `0720` (side-to-side chin) sale como tirón vertical principal en 06 y 08 (`bodyweight`) | motor-rutinas | `specs/engine-rules.yaml`: `fixture_gated.ids: ["2400", "0720"]` (+ `"side-to-side chin"` en `name_en_any`), test de catálogo para bodyweight/home_bands y regenerar goldens 06 y 08. |

## Decisiones sobre las notas

- (a) general_fitness / principiante y énfasis: CAMBIO. Propuesta en el informe (limitar el bloque de
  énfasis de brazos a hipertrofia/toning y no principiantes; `rationale_es` para principiantes).
- (b) sésamo/mostaza/apio: sin CC en v1. motor-nutricion pone `meal_slots: []` a `sesamo` y `apio`
  (aparecían en el 13 % de los días); frontend-ui añade la nota de alérgenos no filtrables; arquitecto
  abre un CC aditivo para v1.1.

## Evidencia

Goldens auditados por script (dificultad, ids vetados, gated, series, ondulación), barrido propio de
384 planes y el de 288 del autor (0 alérgenos, 0 sobre `max_portion_g`, tolerance_not_met 1,8-4,5 %).
Hallazgo nuevo (CAMBIO): grasa > 35 % en IMC ≥ 32 por el suelo de 0,8 g/kg de peso total.
No se ejecutaron las suites completas (modo rápido).

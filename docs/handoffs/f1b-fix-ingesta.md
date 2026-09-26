# Handoff · Fase 1b · fix-ingesta (ingesta-datos)

Rama `f1b/fix-ingesta` (sin fusionar). Origen: `docs/reviews/f1b-experto-entrenamiento.md`
(§3 C1/C10/C11, §5.2, §5.3, §6.3, §7 criterio 3).

## Resumen

Aplicados todos los hallazgos asignados a ingesta-datos, salvo las ediciones de CC (fuera de mi
zona de escritura, ver pendientes). Catálogo: 136 staples (antes 144), 1.324 ejercicios, 0 `other`
sin justificar. `docs/enrichment-report.md` y `specs/overrides/names_es.json` regenerados.

| Hallazgo | Estado | Detalle |
|---|---|---|
| B3 staples/overrides | Hecho | `0471` y `3302`: `is_staple: false`, `role: accessory`; `0471` `load_type: bodyweight`. Fuera del staple de `vertical_push`. Los ejercicios de dificultad 3 quedan marcados con `difficulty: 3` (`0471`, `3302`, `0251`, `0677`, `1367`, `0670`, `3193`, `0496`, `1759`, dominadas y fondos estrictos) para que el motor los filtre; la lista `skill_gated` vive en `engine-rules.yaml` (motor). |
| B5 `equipment_code` | Hecho | `ExerciseOverride.equipment_code` admitido en `by_id`; se aplica en `normalize_record` (el grupo se deriva de `equipment-normalization.yaml`). `2400` → `cable` / grupo `gym`. Es el único etiquetado de equipamiento que lista el experto. |
| B5 CC `pullup_bar`/`bench` | No hecho | Requiere editar `docs/CONTRACT_CHANGES.md` (fuera de mi zona, ADR 0002). Lo abre arquitecto (ver peticiones). |
| C1 staples | Hecho | Fuera: `0046`, `1759`, `0044`, `0489`, `0488`, `0251`, `0553`, `0471`, `3302`, `3193`, `0496`, `1160` (burpee). Dentro: `3292`, `0696`, `1766`, `3239`. `0044` a `role: accessory`. |
| Celdas exentas | Hecho | `vertical_push x bodyweight` (0 staples) y `hinge x bodyweight` (solo `3292`), en `STAPLE_CELL_EXEMPTIONS` (`domain.py`), con motivo en el informe; test actualizado. La tarea citaba solo la primera; la segunda es necesaria porque C1 retira `0489`/`0488` y el experto la exime (§5.2). |
| C10 enriquecimiento | Hecho | `0555` `knee_extension`; `0352`, `1625`, `0812`-`0815` `mechanic: compound`; `0677`, `1367`, `0670` d3; `0858` cardio/`cardio`/`time`; `0471` bodyweight. Nueva sección `difficulty_rules` (dominadas, chin-ups y fondos con peso corporal a d3, sin `assisted/band/negative/kneeling/inverted/bench/on floor/between benches/bench leg`, más `machine` y `floor` por falsos positivos). Ajustes propios: `0815` d2 (en suelo), `0688` y `3012` d2 (activación escapular). |
| C11 nombres | Hecho | Los 15 CAMBIO aplicados y los 16 APROBADOS registrados en `docs/names-es-review.md`; más `1288`, `1305`, `0043`+`1461`+`1462`, `3562` y `0628`. |
| S2 (parte staples) | Hecho | `1160` burpee ya no es staple de `cardio`. Las opciones de finisher las decide el motor. |

## Ficheros tocados

- `backend/ingest/{specs,normalize,enrich,report,domain}.py` y tests
  (`test_enrich.py`, `test_catalog_report.py`, `test_names_alternatives.py`, `test_load.py`).
- `specs/overrides/{enrichment-overrides,staples,names_es,names-es-exceptions}.yaml|json`
  (overrides v3, staples v3).
- `docs/enrichment-report.md` (regenerado), `docs/names-es-review.md`, este handoff.

## Decisiones (y ADRs)

- Sin ADR nuevo. `difficulty_rules` es una sección nueva de `enrichment-overrides.yaml`
  (`specs/enrichment-rules.yaml` no se toca, es del motor).
- Las dominadas estrictas `0652`, `1326`, `1429` siguen como staples de `vertical_pull x
  bodyweight` (el diff §6.3 no las retira y la celda necesita 2), ahora con d3: el tope de
  dificultad del motor las excluye para principiante/intermedio.
- `1305` no usa el nombre propuesto por el experto porque duplicaba `1302`; el `3562` lleva una
  excepción de glosario (`glute bridge`) por ser un hip thrust.
- `0057` («extensión de codos») no se unifica a «extensión de tríceps» porque colisionaría con `0061`.

## Cómo verificar (comandos exactos)

```bash
cd backend
uv run pytest ingest/tests -q --no-cov -k "not load"   # 121 passed (modo rápido, sin slow ni BD)
uv run ruff check ingest && uv run mypy ingest
```

## Métricas

Staples 136 (`squat` 10, `hinge` 9, `vertical_push` 6, `knee_flexion` 4...). Matriz: todas las celdas
con >= 2 salvo las 2 exentas. Pull-ups/dips estrictos con peso corporal: unos 30 ejercicios a d3.
Tests `load` (Postgres/Docker) y `slow` no ejecutados (modo rápido); sus cadenas de nombre se
actualizaron.

## Riesgos/pendientes

- El fixture del motor (`export-cards`) debe regenerarse: cambian `is_staple`, `difficulty`,
  `role`, `movement_pattern` (`0555`, `0858`), `equipment_code` (`2400`) y `name_es`.
- Ids que el experto pide excluir de auto-selección (`0100`, `0543`): es `skill_gated`/lista del
  motor, no dato de ingesta.
- Marca `low_quality_ids` (criterio 3 de §7) no implementada: no existe en el esquema de
  `ExerciseCard`; requiere decisión de contrato.

## Peticiones a otros agentes

- **arquitecto**: abrir CC v1.1 (`pullup_bar` y `bench` en `EquipmentCode`, preset «peso corporal
  con barra»); B5 punto 5.
- **motor-rutinas**: regenerar el fixture de cartas; usar `difficulty` 3 y el `skill_gated` propio
  para pino (`0471`, `3302`), pistol (`1759`), etc.; `fixture_gated` puede apoyarse en
  `equipment_code` corregido de `2400`.

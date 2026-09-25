# Snapshots golden del motor de rutinas

Doce perfiles representativos (MASTER_PROMPT §7.8) para la revisión del experto
(tarea F1b-EXP-05). Cada perfil tiene dos ficheros:

- `<perfil>.json`: el `ProgramPlan` completo (todas las semanas), comparado byte a byte por
  `tests/test_golden.py`.
- `<perfil>.md`: versión legible de la semana 1 (tabla por día), la progresión del
  mesociclo, el volumen semanal frente al objetivo, los avisos y `rationale_es`.

Todos usan la semilla `20260923` y el catálogo `tests/fixtures/catalog.json` exportado con
`forja-ingest export-cards` (dataset @ `7455efae`). Los nombres de ejercicio son los
`name_es` de la ingesta seguidos del id del dataset.

| # | Perfil | Qué cubre |
|---|---|---|
| 01 | Principiante, mujer, casa con mancuernas, hipertrofia, 3 días × 45 min | Cuerpo completo A/B/C, énfasis tren inferior (preselección por sexo), series al mínimo y RIR +1 |
| 02 | Intermedio, hombre, gimnasio, hipertrofia, 4 días × 60 min | Torso/pierna ×2, superseries de antagonistas por tiempo, +1 serie por semana |
| 03 | Avanzado, hombre, gimnasio, hipertrofia, 6 días × 75 min | Empuje/tirón/pierna ×2, variedad entre días repetidos (−30 por ejercicio ya usado) |
| 04 | Intermedia, mujer, gimnasio, fuerza, 4 días × 60 min | Día «Glúteo e isquios», ondulación pesado/medio, descansos de accesorio −15 % |
| 05 | Avanzado, sin sexo, gimnasio, fuerza, 3 días × 90 min, 6 semanas | Empuje/tirón/pierna, semanas de intensificación (RIR ≤ 1), descarga final |
| 06 | Principiante, peso corporal, pérdida de grasa, 3 días × 30 min | Presupuesto muy justo: finisher y accesorios recortados, relajación por equipamiento |
| 07 | Intermedia, mujer, casa con bandas, tonificación, 4 días × 45 min | Superseries por densidad (`prefer_supersets`), finisher de cardio |
| 08 | Intermedio, hombre, peso corporal, resistencia, 3 días × 40 min | Circuitos con rondas, descansos cortos entre estaciones |
| 09 | Principiante, hombre, gimnasio, forma general, 2 días × 60 min | Cuerpo completo A/B, progresión lineal sin series extra |
| 10 | Avanzada, mujer, gimnasio, hipertrofia, 5 días × 60 min | Empuje/tirón/pierna + torso/pierna con día de glúteo, +1 serie de accesorio por semana |
| 11 | Intermedio, gimnasio, forma general, 7 días × 45 min | Día obligatorio de recuperación activa (cardio suave + movilidad) y avisos de frecuencia |
| 12 | Intermedio, hombre, mancuernas + polea + máquinas, hipertrofia, 5 días × 60 min | Limitaciones (evita bisagra y zona lumbar ⇒ sustitución por patrón afín), énfasis brazos |

Regenerar tras un cambio intencionado de salida (subiendo `ENGINE_VERSION`):

```bash
cd engine && FORJA_UPDATE_GOLDEN=1 uv run --locked pytest tests/test_golden.py --no-cov
```

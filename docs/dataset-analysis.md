# Análisis del dataset de origen

> Generado inspeccionando `hasaneyldrm/exercises-dataset` @ `7455efae41b330c265e7cd4b78dfa848e7ce5ebd`
> (commit del 2026-07-16). Los tests de ingesta DEBEN verificar estas cifras; si el commit
> cambia, se regenera este documento.

## Resumen

- Registros: **1324** · ids `0001`…; ficheros de medios: 1.324 JPG (`images/`, 12 MB) y
  1.324 GIF (`videos/`, 126 MB), todos 180×180 (GIF de ~12 fotogramas). Ninguno falta.
- Nombre del fichero de medio: `<id>-<media_id>.<ext>`.
- Idiomas de instrucciones: en, es, it, tr, ru, zh, hi, pl, ko, fr (todos los registros).
- Pasos por ejercicio (es): {4: 82, 5: 503, 6: 426, 7: 221, 8: 72, 9: 15, 10: 2, 11: 3}.
- `category` y `body_part` son idénticos en todos los registros.
- Licencias: datos MIT; medios © Gym visual con condiciones propias (ver MASTER_PROMPT §2.1).

## Peculiaridades a tratar en la ingesta

- **Nombres solo en inglés**, con erratas (p. ej. `revers`, `sitted`, `side bent`).
- **33 ejercicios con sufijo `(male)`/`(female)`**: `arms apart circular toe touch (male)`, `arms overhead full sit-up (male)`, `astride jumps (male)`, `barbell glute bridge two legs on bench (male)`, `barbell sitted alternate leg raise (female)`, `basic toe touch (male)`, `bent knee lying twist (male)`, `cable kneeling rear delt row (with rope) (male)`, `chest tap push-up (male)`, `dumbbell reverse grip row (female)`, `dynamic chest stretch (male)`, `forward lunge (male)`, `glute bridge two legs on bench (male)`, `half knee bends (male)`, `half sit-up (male)`, `hands clasped circular toe touch (male)`, `hands reversed clasped circular toe touch (male)`, `jack jump (male)`, `kneeling plank tap shoulder (male)`, `kneeling push-up (male)`, `modified hindu push-up (male)`, `prisoner half sit-up (male)`, `resistance band hip thrusts on knees (female)`, `scissor jumps (male)`, `seated calf stretch (male)`, `semi squat jump (male)`, `side lying hip adduction (male)`, `side-to-side toe touch (male)`, `star jump (male)`, `swimmer kicks v. 2 (male)`, `twisted leg raise (female)`, `two toe touch (male)`, `weighted cossack squats (male)`.
- **40 variantes `v. N`**: `band two legs calf raise - (band under both legs) v. 2`, `barbell rear lunge v. 2`, `barbell revers wrist curl v. 2`, `barbell side bent v. 2`, `barbell side split squat v. 2`, `barbell split squat v. 2`, `barbell upright row v. 2`, `barbell upright row v. 3`, `barbell wrist curl v. 2`, `cable lying triceps extension v. 2`, `cable pushdown (straight arm) v. 2`, `dumbbell arnold press v. 2`, `dumbbell cross body hammer curl v. 2`, `dumbbell cuban press v. 2`, `dumbbell decline shrug v. 2`, `dumbbell front raise v. 2`, `dumbbell hammer curl v. 2`, `dumbbell incline curl v. 2`, `dumbbell lying one arm press v. 2`, `dumbbell one arm shoulder press v. 2`, `dumbbell seated lateral raise v. 2`, `dumbbell standing inner biceps curl v. 2`, `inchworm v. 2`, `inverted row v. 2`, `jump squat v. 2`, `lever gripless shrug v. 2`, `lever hip extension v. 2`, `lever incline chest press v. 2`, `lever preacher curl v. 2`, `lever seated crunch v. 2`, `lever shoulder press v. 2`, `lever shoulder press v. 3`, `oblique crunch v. 2`, `push-up (wall) v. 2`, `quick feet v. 2`, `side bridge v. 2`, `sit-up v. 2`, `stationary bike run v. 3`, `swimmer kicks v. 2 (male)`, `weighted russian twist v. 2`.
- **Variantes de cámara**: `barbell full squat (back pov)`, `barbell full squat (side pov)`,
  `dumbbell upright row (back pov)`, `sled 45в° leg press (back pov)`, `sled 45° leg press (side pov)`.
- **Mojibake** `в°` (debería ser `°`) en ids 0738, 0739, 0740, 1464.
- **Nombres duplicados con distinto id**: `barbell seated calf raise`, `ez barbell spider curl`, `lever chest press`, `push-up (on stability ball)`, `self assisted inverse leg curl`, `smith reverse calf raises`.
- 57 nombres contienen `stretch` (→ rol movilidad/vuelta a la calma); 29 de `body_part = cardio`.
- Vocabulario muscular inconsistente entre `target`, `muscle_group` y `secondary_muscles`
  (ver tablas; la normalización está en `specs/muscle-normalization.yaml`).
- Recuento de palabras clave en nombres (orientativo para reglas de patrón): squat 80,
  deadlift 19, lunge 21, press 164, row 105, pull-up 19, chin-up 8, pulldown 27, curl 185,
  extension 72, raise 117, fly 39, push-up 39, dip 30, crunch 36, plank 9, bridge 12,
  thrust 3, shrug 12, kickback 11, calf 52, twist 36, sit-up 16, leg raise 18, jump 17.

### body_part / category

| Valor | Nº |
|---|---|
| `upper arms` | 292 |
| `upper legs` | 227 |
| `back` | 203 |
| `waist` | 169 |
| `chest` | 163 |
| `shoulders` | 143 |
| `lower legs` | 59 |
| `lower arms` | 37 |
| `cardio` | 29 |
| `neck` | 2 |

### equipment

| Valor | Nº |
|---|---|
| `body weight` | 325 |
| `dumbbell` | 294 |
| `cable` | 157 |
| `barbell` | 154 |
| `leverage machine` | 81 |
| `band` | 54 |
| `smith machine` | 48 |
| `kettlebell` | 41 |
| `weighted` | 36 |
| `stability ball` | 28 |
| `ez barbell` | 23 |
| `assisted` | 15 |
| `sled machine` | 15 |
| `medicine ball` | 13 |
| `rope` | 10 |
| `roller` | 8 |
| `resistance band` | 7 |
| `bosu ball` | 3 |
| `olympic barbell` | 2 |
| `wheel roller` | 2 |
| `upper body ergometer` | 1 |
| `skierg machine` | 1 |
| `hammer` | 1 |
| `stationary bike` | 1 |
| `tire` | 1 |
| `trap bar` | 1 |
| `elliptical machine` | 1 |
| `stepmill machine` | 1 |

### target

| Valor | Nº |
|---|---|
| `abs` | 169 |
| `pectorals` | 158 |
| `biceps` | 151 |
| `glutes` | 144 |
| `delts` | 143 |
| `triceps` | 141 |
| `upper back` | 88 |
| `lats` | 81 |
| `calves` | 59 |
| `quads` | 44 |
| `forearms` | 37 |
| `cardiovascular system` | 29 |
| `hamstrings` | 28 |
| `spine` | 19 |
| `traps` | 15 |
| `adductors` | 6 |
| `serratus anterior` | 5 |
| `abductors` | 5 |
| `levator scapulae` | 2 |

### muscle_group

| Valor | Nº |
|---|---|
| `shoulders` | 191 |
| `forearms` | 165 |
| `biceps` | 164 |
| `triceps` | 161 |
| `hamstrings` | 127 |
| `quadriceps` | 110 |
| `glutes` | 71 |
| `obliques` | 67 |
| `hip flexors` | 66 |
| `chest` | 53 |
| `trapezius` | 36 |
| `traps` | 32 |
| `deltoids` | 24 |
| `calves` | 11 |
| `ankles` | 11 |
| `core` | 7 |
| `lower back` | 6 |
| `rotator cuff` | 4 |
| `soleus` | 4 |
| `rhomboids` | 2 |
| `wrist flexors` | 2 |
| `latissimus dorsi` | 2 |
| `abdominals` | 2 |
| `ankle stabilizers` | 1 |
| `upper back` | 1 |
| `wrist extensors` | 1 |
| `lats` | 1 |
| `wrists` | 1 |
| `hands` | 1 |

### secondary_muscles (apariciones)

| Valor | Nº |
|---|---|
| `shoulders` | 400 |
| `hamstrings` | 289 |
| `forearms` | 277 |
| `triceps` | 268 |
| `biceps` | 194 |
| `quadriceps` | 161 |
| `calves` | 147 |
| `glutes` | 136 |
| `core` | 94 |
| `chest` | 91 |
| `hip flexors` | 77 |
| `obliques` | 72 |
| `lower back` | 71 |
| `rhomboids` | 54 |
| `trapezius` | 47 |
| `upper back` | 37 |
| `traps` | 33 |
| `deltoids` | 28 |
| `rear deltoids` | 20 |
| `brachialis` | 14 |
| `back` | 11 |
| `ankles` | 11 |
| `feet` | 8 |
| `rotator cuff` | 6 |
| `latissimus dorsi` | 5 |
| `ankle stabilizers` | 4 |
| `soleus` | 4 |
| `wrists` | 3 |
| `upper chest` | 3 |
| `wrist flexors` | 2 |
| `wrist extensors` | 2 |
| `abdominals` | 2 |
| `sternocleidomastoid` | 2 |
| `hands` | 2 |
| `groin` | 1 |
| `grip muscles` | 1 |
| `lower abs` | 1 |
| `lats` | 1 |
| `inner thighs` | 1 |
| `shins` | 1 |

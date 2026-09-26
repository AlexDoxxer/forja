# Informe de enriquecimiento del catálogo

> Generado por `forja-ingest report` (no editar a mano). Dataset `hasaneyldrm/exercises-dataset` @ `7455efae41b330c265e7cd4b78dfa848e7ce5ebd`; reglas `specs/enrichment-rules.yaml` v1, overrides v3, staples v3.

## Resumen

- Ejercicios: **1324**.
- Patrón `other`: **8**, todos justificados (8 excepciones explícitas).
- Staples: **136** (rol `main`: 68).
- Reglas prioritarias en overrides: 28; overrides por id: 57.
- Nombres en español: 1324/1324 (100 %).
- Ejercicios con demostrador (`demo_sex`): 34.

## Matriz de staples (patrón principal x grupo de equipamiento)

Requisito: al menos 2 staples en cada celda con candidatos, salvo las exentas.

| Patrón | gym | home_basic | bodyweight |
|---|---|---|---|
| `squat` | ✅ 4/42 (0042, 0043, 0739, 0770) | ✅ 4/10 (0413, 0534, 1004, 1760) | ✅ 2/6 (3119, 3533) |
| `lunge` | ✅ 3/12 (0054, 0078, 0114) | ✅ 4/11 (0336, 0381, 0410, 0431) | ✅ 3/6 (1460, 2368, 3470) |
| `hinge` | ✅ 4/24 (0032, 0085, 0117, 0811) | ✅ 4/27 (0549, 0991, 1459, 1757) | ⚠️ exenta 1/4 (3292) |
| `horizontal_push` | ✅ 5/40 (0025, 0047, 0577, 0748, 2144) | ✅ 3/32 (0289, 0314, 1254) | ✅ 3/35 (0493, 0662, 3211) |
| `vertical_push` | ✅ 3/22 (0091, 0587, 0774) | ✅ 3/33 (0405, 0426, 0997) | ⚠️ exenta 0/2 (—) |
| `horizontal_pull` | ✅ 4/49 (0027, 0180, 0861, 3017) | ✅ 3/14 (0292, 0293, 3144) | ✅ 3/18 (0499, 2300, 3168) |
| `vertical_pull` | ✅ 3/41 (0017, 0198, 2330) | ✅ 3/6 (0970, 0974, 1013) | ✅ 3/24 (0652, 1326, 1429) |

Celdas exentas del mínimo (revisión de dominio F1b):

- `vertical_push` x `bodyweight`: solo existen ejercicios gimnásticos (pino y flexión en pino, dificultad 3); el motor cae por afinidad a horizontal_push.
- `hinge` x `bodyweight`: la única bisagra genuina sin material es 3292 (elevator); la bisagra sin material se cubre por afinidad con glute_isolation.

## Distribución por patrón y grupo de equipamiento

| Patrón | Total | gym | home_basic | bodyweight | cardio_machine | other | Staples |
|---|---|---|---|---|---|---|---|
| `squat` | 58 | 42 | 10 | 6 | 0 | 0 | 10 |
| `lunge` | 29 | 12 | 11 | 6 | 0 | 0 | 10 |
| `hinge` | 56 | 24 | 27 | 4 | 0 | 1 | 9 |
| `horizontal_push` | 107 | 40 | 32 | 35 | 0 | 0 | 11 |
| `vertical_push` | 57 | 22 | 33 | 2 | 0 | 0 | 6 |
| `horizontal_pull` | 81 | 49 | 14 | 18 | 0 | 0 | 10 |
| `vertical_pull` | 71 | 41 | 6 | 24 | 0 | 0 | 9 |
| `elbow_flexion` | 146 | 59 | 85 | 2 | 0 | 0 | 6 |
| `elbow_extension` | 133 | 62 | 49 | 22 | 0 | 0 | 7 |
| `shoulder_raise` | 52 | 20 | 32 | 0 | 0 | 0 | 3 |
| `chest_fly` | 42 | 19 | 22 | 1 | 0 | 0 | 3 |
| `rear_delt` | 32 | 14 | 18 | 0 | 0 | 0 | 4 |
| `knee_extension` | 5 | 2 | 1 | 2 | 0 | 0 | 3 |
| `knee_flexion` | 16 | 7 | 2 | 7 | 0 | 0 | 4 |
| `hip_abduction` | 6 | 1 | 1 | 4 | 0 | 0 | 3 |
| `hip_adduction` | 4 | 2 | 0 | 2 | 0 | 0 | 2 |
| `glute_isolation` | 19 | 5 | 4 | 10 | 0 | 0 | 5 |
| `calf` | 48 | 29 | 13 | 6 | 0 | 0 | 7 |
| `core_flexion` | 85 | 24 | 12 | 49 | 0 | 0 | 4 |
| `core_anti_extension` | 25 | 4 | 4 | 17 | 0 | 0 | 4 |
| `core_rotation` | 34 | 15 | 9 | 9 | 0 | 1 | 3 |
| `core_lateral` | 24 | 5 | 8 | 11 | 0 | 0 | 3 |
| `shrug` | 14 | 7 | 6 | 1 | 0 | 0 | 3 |
| `forearm` | 34 | 16 | 17 | 1 | 0 | 0 | 0 |
| `carry` | 2 | 0 | 2 | 0 | 0 | 0 | 2 |
| `plyometric` | 20 | 3 | 10 | 7 | 0 | 0 | 0 |
| `cardio` | 35 | 5 | 1 | 24 | 5 | 0 | 5 |
| `mobility` | 81 | 15 | 13 | 53 | 0 | 0 | 0 |
| `other` | 8 | 2 | 5 | 1 | 0 | 0 | 0 |

## Otras distribuciones

### Rol

| Valor | Nº | % |
|---|---|---|
| `accessory` | 965 | 72.9 % |
| `core` | 165 | 12.5 % |
| `main` | 68 | 5.1 % |
| `mobility` | 64 | 4.8 % |
| `cardio` | 31 | 2.3 % |
| `warmup` | 31 | 2.3 % |

### Mecánica

| Valor | Nº | % |
|---|---|---|
| `isolation` | 863 | 65.2 % |
| `compound` | 461 | 34.8 % |

### Dificultad

| Valor | Nº | % |
|---|---|---|
| `2` | 829 | 62.6 % |
| `1` | 403 | 30.4 % |
| `3` | 92 | 6.9 % |

### Lateralidad

| Valor | Nº | % |
|---|---|---|
| `bilateral` | 1100 | 83.1 % |
| `unilateral` | 224 | 16.9 % |

### Tipo de carga

| Valor | Nº | % |
|---|---|---|
| `external` | 940 | 71.0 % |
| `bodyweight` | 223 | 16.8 % |
| `time` | 139 | 10.5 % |
| `assisted` | 22 | 1.7 % |

### Tipo de variante

| Valor | Nº | % |
|---|---|---|
| `base` | 1238 | 93.5 % |
| `version` | 40 | 3.0 % |
| `demonstrator` | 33 | 2.5 % |
| `duplicate` | 8 | 0.6 % |
| `camera_angle` | 5 | 0.4 % |

### Origen de la decisión de patrón

| Valor | Nº | % |
|---|---|---|
| `rule` | 693 | 52.3 % |
| `override_rule` | 595 | 44.9 % |
| `override` | 36 | 2.7 % |

## Excepciones `other` justificadas

| Id | Nombre | Motivo |
|---|---|---|
| `0020` | balance board | Tabla de equilibrio: trabajo propioceptivo sin patrón de fuerza; se usa como calentamiento. |
| `0216` | cable seated shoulder internal rotation | Rotación interna de hombro (manguito rotador): prehabilitación, sin patrón de §6.3. |
| `0235` | cable standing shoulder external rotation | Rotación externa de hombro (manguito rotador): prehabilitación, sin patrón de §6.3. |
| `0551` | kettlebell turkish get up (squat style) | Levantamiento turco: movimiento global en varias fases (suelo-de pie) sin patrón único. |
| `0863` | dumbbell lying external shoulder rotation | Rotación externa de hombro tumbado (manguito rotador): prehabilitación. |
| `0864` | dumbbell upright shoulder external rotation | Rotación externa de hombro de pie (manguito rotador): prehabilitación. |
| `0984` | band lying hip internal rotation | Rotación interna de cadera con banda: prehabilitación de rotadores de cadera. |
| `0996` | band seated hip internal rotation | Rotación interna de cadera sentado con banda: prehabilitación de rotadores de cadera. |

## Staples por patrón

| Patrón | Nº | Ejercicios |
|---|---|---|
| `squat` | 10 | 0043 sentadilla trasera con barra; 0042 sentadilla frontal con barra; 0770 sentadilla en multipower; 0739 prensa de piernas a 45°; 0413 sentadilla con mancuernas; 0534 sentadilla goblet con kettlebell; 1760 sentadilla goblet con mancuerna; 1004 sentadilla con banda elástica; 3533 sentadilla con peso corporal (cuádriceps); 3119 sentadilla con peso corporal hasta paralelo (potty squat) |
| `lunge` | 10 | 0054 zancada con barra; 0078 zancada atrás con barra; 0114 subida al banco con barra; 0336 zancada con mancuernas; 0381 zancada atrás con mancuernas; 0410 sentadilla búlgara con mancuernas; 0431 subida al banco con mancuernas; 1460 zancada caminando; 2368 sentadilla dividida; 3470 zancada adelante |
| `hinge` | 9 | 0032 peso muerto con barra; 0085 peso muerto rumano con barra; 0117 peso muerto sumo con barra; 0811 peso muerto con barra hexagonal; 0549 swing con kettlebell; 0991 pull through con banda elástica; 1459 peso muerto rumano con mancuernas; 1757 peso muerto a una pierna con mancuernas; 3292 bisagra de cadera con peso corporal (elevator) |
| `horizontal_push` | 11 | 0025 press de banca con barra; 0047 press de banca inclinado con barra; 0577 press de pecho en máquina; 2144 press de pecho sentado en polea; 0748 press de banca en multipower; 0289 press de banca con mancuernas; 0314 press de banca inclinado con mancuernas; 1254 press de banca con banda elástica; 0493 flexión inclinada; 0662 flexión; 3211 flexión de rodillas |
| `vertical_push` | 6 | 0091 press por encima de la cabeza sentado con barra; 0587 press militar en máquina; 0774 press militar de pie en multipower; 0405 press de hombro sentado con mancuernas; 0426 press por encima de la cabeza de pie con mancuernas; 0997 press de hombro con banda elástica |
| `horizontal_pull` | 10 | 0027 remo inclinado con barra; 0180 remo sentado bajo en polea; 0861 remo sentado en polea; 3017 remo Pendlay con barra; 0293 remo inclinado con mancuernas; 0292 remo inclinado con mancuerna a una mano; 3144 remo sentado con espalda recta con banda de resistencia; 0499 remo invertido; 3168 remo en sentadilla con peso corporal; 2300 remo invertido con rodillas flexionadas |
| `vertical_pull` | 9 | 0017 dominada asistida; 2330 jalón al pecho en polea con recorrido completo; 0198 jalón en polea; 0970 dominada asistida con banda elástica; 0974 jalón con banda elástica y agarre cerrado; 1013 jalón con banda elástica y agarre supino; 0652 dominada; 1326 dominada supina; 1429 dominada con agarre ancho |
| `glute_isolation` | 5 | 1409 puente de glúteo con barra; 3562 hip thrust con barra (espalda apoyada en banco); 2286 extensión de cadera en máquina; 3236 hip thrust de rodillas con banda de resistencia; 3013 puente de glúteo bajo en el suelo |
| `chest_fly` | 3 | 0308 aperturas con mancuernas; 0227 aperturas de pie en polea; 0596 aperturas sentado en máquina |
| `shoulder_raise` | 3 | 0334 elevación lateral con mancuernas; 0178 elevación lateral en polea; 0584 elevación lateral en máquina |
| `rear_delt` | 4 | 0383 pájaros con mancuernas; 0993 pájaros con banda elástica; 0203 remo para deltoides posterior en polea con cuerda; 0602 pájaros sentado en máquina |
| `elbow_flexion` | 6 | 0294 curl de bíceps con mancuernas; 0031 curl con barra; 0447 curl con barra Z; 0313 curl martillo con mancuernas; 0165 curl martillo en polea con cuerda; 0968 curl de bíceps alterno con banda elástica |
| `elbow_extension` | 7 | 0201 extensión de tríceps en polea; 0200 extensión de tríceps en polea con cuerda; 0060 press francés tumbado con barra (extensión de tríceps); 0194 extensión de tríceps por encima de la cabeza en polea con cuerda; 0814 fondos de tríceps; 0283 flexión diamante; 0430 extensión de tríceps de pie con mancuerna |
| `knee_extension` | 3 | 0585 extensión de cuádriceps en máquina; 3007 extensión de cuádriceps con banda de resistencia; 1489 sentadilla sissy |
| `knee_flexion` | 4 | 0586 curl femoral tumbado en máquina; 0599 curl femoral sentado en máquina; 0696 curl femoral inverso asistido por uno mismo en el suelo; 1766 curl femoral inverso asistido por uno mismo |
| `hip_abduction` | 3 | 0597 abducción de cadera sentado en máquina; 3006 abducción de cadera sentado con banda de resistencia; 0710 abducción de cadera tumbado de lado |
| `hip_adduction` | 2 | 0598 aducción de cadera sentado en máquina; 3667 aducción de cadera tumbado de lado |
| `calf` | 7 | 1372 elevación de talones de pie con barra (apoyo en suelo); 1373 elevación de talones de pie con peso corporal; 0417 elevación de talones de pie con mancuernas; 0605 elevación de talones de pie en máquina; 0088 elevación de talones sentado con barra; 0409 elevación de talones a una pierna con mancuerna; 0999 elevación de talones a una pierna con banda elástica |
| `shrug` | 3 | 0406 encogimiento de hombros con mancuernas; 0095 encogimiento de hombros con barra; 1018 encogimiento de hombros con banda elástica |
| `core_anti_extension` | 4 | 0276 dead bug (bicho muerto); 2135 plancha frontal lastrada; 0857 rueda abdominal; 3239 plancha de rodillas con toque de hombro |
| `core_flexion` | 4 | 0472 elevación de piernas colgado; 0872 crunch inverso; 0274 crunch en el suelo; 0175 crunch de rodillas en polea |
| `core_rotation` | 3 | 0687 giro ruso; 0846 giro ruso lastrado; 0230 elevación diagonal de pie en polea |
| `core_lateral` | 3 | 0979 press Pallof horizontal con banda elástica; 3544 plancha lateral inclinada con peso corporal; 0407 flexión lateral de tronco con mancuerna |
| `carry` | 2 | 2133 paseo del granjero; 3548 paseo con mancuerna por encima de la cabeza a una mano |
| `cardio` | 5 | 2612 salto a la comba; 2138 bicicleta estática a ritmo de carrera; 2141 elíptica a ritmo de caminata; 3666 caminata en cinta inclinada; 0685 carrera |

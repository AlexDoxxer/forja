# Nombres en español: casos dudosos para revisión

> Propietario: `ingesta-datos`. Revisor: `experto-entrenamiento` (tarea F1b-EXP-03).
> Fuente: `specs/overrides/names_es.json` (1.324 ids, 100 % de cobertura). Los 1.284 nombres
> ingleses distintos se tradujeron en 13 lotes de ≤ 100 aplicando `specs/glossary-es.yaml`;
> tras cada lote se ejecutó la comprobación de glosario (`ingest.names.validate_names`), que hoy
> da 0 incidencias. Las excepciones justificadas al glosario y el único duplicado intencionado
> están en `specs/overrides/names-es-exceptions.yaml`.

## Criterios aplicados

- Minúscula inicial (el frontend capitaliza); nombres propios con mayúscula (`press Arnold`,
  `curl Zottman`, `remo Pendlay`, `sentadilla Zercher`, `press Svend`, `press Scott`).
- Orden «movimiento + implemento + variante» (`curl de bíceps alterno con mancuernas`).
- Los sufijos `(male)`, `(female)`, `v. N`, `(back pov)`/`(side pov)` no se traducen: todas las
  variantes de un grupo comparten nombre y la UI muestra `variant_label_es`.
- `lever` y `leverage machine` ⇒ «en máquina»; `sled` ⇒ «prensa»; `smith` ⇒ «multipower»;
  `exercise ball`/`stability ball` ⇒ «fitball»; `band` ⇒ «banda elástica»;
  `resistance band` ⇒ «banda de resistencia».
- «Single leg split squat» ⇒ «sentadilla búlgara» (pie trasero elevado, según glosario);
  «split squat» ⇒ «sentadilla dividida».
- «Reverse fly» ⇒ «pájaros»; «rear fly» ⇒ «aperturas posteriores».

## Casos dudosos

| Id | Nombre inglés | Propuesta | Duda |
|---|---|---|---|
| 0003 | air bike | crunch bicicleta | En el dataset es un crunch bicicleta (abdominales), no la bicicleta de aire. |
| 0100 | barbell skier | esquiador con barra | Nombre poco habitual; ¿«tirón de esquiador con barra»? |
| 0138 | bottoms-up | elevación de cadera invertida (bottoms-up) | Término sin equivalente asentado. |
| 0137 | body-up | body-up (extensión de codos desde plancha) | Se conserva el anglicismo con explicación. |
| 0172 | cable incline pushdown | extensión de hombros en polea en banco inclinado | El objetivo es el dorsal; no es un «pushdown» de tríceps. |
| 0260 | cocoons | crunch capullo (cocoons) | Nombre poco conocido. |
| 0276 | dead bug | bicho muerto (dead bug) | ¿Mantener solo «dead bug»? |
| 0316 | dumbbell incline breeding | press inclinado con mancuernas y codos a 90° (breeding) | «Breeding» parece una errata del dataset; las instrucciones describen un press. |
| 0543 | kettlebell pirate supper legs | piernas de pirata con kettlebell | Nombre original confuso. |
| 0555 | kick out sit | patada sentado para isquiotibiales | Traducción descriptiva. |
| 0609 | london bridge | puente de Londres con cuerda | Nombre propio de un ejercicio con cuerda (remo). |
| 0641 | otis up | abdominal Otis con disco | — |
| 0777 | spell caster | lanzador de hechizos con mancuernas (spell caster) | ¿Mantener el anglicismo? |
| 0844 | weighted round arm | círculos de brazos inclinado lastrados | Las instrucciones describen elevaciones inclinado (clasificado como `rear_delt`). |
| 0858 | wind sprints | sprints de piernas tumbado | Es un ejercicio abdominal tumbado. |
| 1352 | lower back curl | extensión lumbar boca abajo | No es un curl de brazos (excepción de glosario). |
| 1355 | one arm against wall | estiramiento de dorsal a una mano contra la pared | Traducción descriptiva. |
| 1362 | sphinx | postura de la esfinge | Postura de yoga. |
| 1417 | exercise ball one legged diagonal kick hamstring curl | curl femoral con patada diagonal a una pierna sobre fitball | Nombre largo. |
| 1604 | world greatest stretch | el mejor estiramiento del mundo | ¿Mantener «world's greatest stretch»? |
| 2203 | roller seated shoulder flexor depresor retractor | movilidad de hombro sentado con rodillo (flexores, depresores y retractores) | Nombre técnico. |
| 2271 | left hook. boxing | gancho de izquierda (boxeo) | Clasificado como cardio. |
| 3119 | potty squat | sentadilla profunda en cuclillas | — |
| 3234 | hyght dumbbell fly | aperturas altas con mancuernas (hyght) | «Hyght» no es una palabra inglesa; las instrucciones describen aperturas planas. |
| 3292 | elevator | ascensor (bisagra de cadera con peso corporal) | Nombre original poco descriptivo. |
| 3304 | skin the cat | despellejar al gato (skin the cat) | Elemento gimnástico conocido por su nombre inglés. |
| 3533 | quads | sentadilla con peso corporal (cuádriceps) | El nombre original es solo el músculo. |
| 3665 | power point plank | plancha power point | — |
| 3669 | standing archer | arquero de pie (rotación de tronco) | Movilidad dinámica, no la dominada/flexión arquero. |
| 0653 / 1307 | push-up (bosu ball) / push up on bosu ball | flexión sobre bosu | Mismo ejercicio con dos nombres y medios distintos; duplicado declarado. |
| 1759 | single leg squat (pistol) male | sentadilla pistol a una pierna | El dataset omite los paréntesis de `(male)`; se corrige en `name-fixes.yaml` y se asigna `demo_sex = male`. |

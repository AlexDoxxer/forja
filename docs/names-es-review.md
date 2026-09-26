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

## Resolución (revisión F1b, C11)

De los 31 casos dudosos, el experto aprobó 16 y marcó 15 para cambio. Los 15 cambios están
aplicados en `specs/overrides/names_es.json` (columna «Nombre ES final»); los 16 aprobados quedan
registrados como definitivos (`0641` se aprobó con el matiz «lastrado», ya incorporado).
Además se aplicaron las correcciones del §5.3 del informe: `1288` (sin «variante de apoyo»),
`1305` («pase de pecho con balón medicinal y rebote simple»: el nombre propuesto colisionaba con
`1302`), `0043`/`1461`/`1462` («sentadilla trasera con barra», todo el grupo de variantes), `3562`
(«hip thrust con barra (espalda apoyada en banco)», con excepción de glosario) y `0628`
(«caminata lateral con banda (monster walk)»). Sin aplicar, por ser sugerencias de estilo:
«sit-up» (el glosario fija «abdominal completo») y unificar la «extensión de codos» de `0057`
(colisiona con `0061`). `0100` y `0543` deben excluirse de la auto-selección (competencia del
motor).

## Casos dudosos y decisión final

| Id | Nombre inglés | Propuesta inicial | Duda | Veredicto (F1b) | Nombre ES final |
|---|---|---|---|---|---|
| 0003 | air bike | crunch bicicleta | En el dataset es un crunch bicicleta (abdominales), no la bicicleta de aire. | APROBADO | crunch bicicleta |
| 0100 | barbell skier | esquiador con barra | Nombre poco habitual; ¿«tirón de esquiador con barra»? | APROBADO | esquiador con barra |
| 0138 | bottoms-up | elevación de cadera invertida (bottoms-up) | Término sin equivalente asentado. | APROBADO | elevación de cadera invertida (bottoms-up) |
| 0137 | body-up | body-up (extensión de codos desde plancha) | Se conserva el anglicismo con explicación. | CAMBIO | extensión de tríceps con peso corporal, manos en banco (body-up) |
| 0172 | cable incline pushdown | extensión de hombros en polea en banco inclinado | El objetivo es el dorsal; no es un «pushdown» de tríceps. | CAMBIO | jalón con brazos rectos en polea, en banco inclinado |
| 0260 | cocoons | crunch capullo (cocoons) | Nombre poco conocido. | CAMBIO | crunch con manos en la nuca (cocoons) |
| 0276 | dead bug | bicho muerto (dead bug) | ¿Mantener solo «dead bug»? | CAMBIO | dead bug (bicho muerto) |
| 0316 | dumbbell incline breeding | press inclinado con mancuernas y codos a 90° (breeding) | «Breeding» parece una errata del dataset; las instrucciones describen un press. | CAMBIO | press inclinado con mancuernas (breeding) |
| 0543 | kettlebell pirate supper legs | piernas de pirata con kettlebell | Nombre original confuso. | CAMBIO | elevación con kettlebell a una mano en bisagra (pirate supper legs) |
| 0555 | kick out sit | patada sentado para isquiotibiales | Traducción descriptiva. | CAMBIO | extensión de rodillas sentado (kick out) |
| 0609 | london bridge | puente de Londres con cuerda | Nombre propio de un ejercicio con cuerda (remo). | CAMBIO | remo de pie con cuerda en polea alta (london bridge) |
| 0641 | otis up | abdominal Otis con disco | — | APROBADO | abdominal Otis lastrado con disco |
| 0777 | spell caster | lanzador de hechizos con mancuernas (spell caster) | ¿Mantener el anglicismo? | CAMBIO | giro de tronco con mancuerna hacia el pie contrario (spell caster) |
| 0844 | weighted round arm | círculos de brazos inclinado lastrados | Las instrucciones describen elevaciones inclinado (clasificado como `rear_delt`). | CAMBIO | elevación lateral inclinado lastrada con mancuernas (weighted round arm) |
| 0858 | wind sprints | sprints de piernas tumbado | Es un ejercicio abdominal tumbado. | CAMBIO | sprints (wind sprints) |
| 1352 | lower back curl | extensión lumbar boca abajo | No es un curl de brazos (excepción de glosario). | APROBADO | extensión lumbar boca abajo |
| 1355 | one arm against wall | estiramiento de dorsal a una mano contra la pared | Traducción descriptiva. | APROBADO | estiramiento de dorsal a una mano contra la pared |
| 1362 | sphinx | postura de la esfinge | Postura de yoga. | APROBADO | postura de la esfinge |
| 1417 | exercise ball one legged diagonal kick hamstring curl | curl femoral con patada diagonal a una pierna sobre fitball | Nombre largo. | APROBADO | curl femoral con patada diagonal a una pierna sobre fitball |
| 1604 | world greatest stretch | el mejor estiramiento del mundo | ¿Mantener «world's greatest stretch»? | CAMBIO | estiramiento dinámico de zancada con rotación torácica (world's greatest stretch) |
| 2203 | roller seated shoulder flexor depresor retractor | movilidad de hombro sentado con rodillo (flexores, depresores y retractores) | Nombre técnico. | APROBADO | movilidad de hombro sentado con rodillo (flexores, depresores y retractores) |
| 2271 | left hook. boxing | gancho de izquierda (boxeo) | Clasificado como cardio. | APROBADO | gancho de izquierda (boxeo) |
| 3119 | potty squat | sentadilla profunda en cuclillas | — | CAMBIO | sentadilla con peso corporal hasta paralelo (potty squat) |
| 3234 | hyght dumbbell fly | aperturas altas con mancuernas (hyght) | «Hyght» no es una palabra inglesa; las instrucciones describen aperturas planas. | CAMBIO | aperturas planas con mancuernas (hyght) |
| 3292 | elevator | ascensor (bisagra de cadera con peso corporal) | Nombre original poco descriptivo. | CAMBIO | bisagra de cadera con peso corporal (elevator) |
| 3304 | skin the cat | despellejar al gato (skin the cat) | Elemento gimnástico conocido por su nombre inglés. | APROBADO | despellejar al gato (skin the cat) |
| 3533 | quads | sentadilla con peso corporal (cuádriceps) | El nombre original es solo el músculo. | APROBADO | sentadilla con peso corporal (cuádriceps) |
| 3665 | power point plank | plancha power point | — | APROBADO | plancha power point |
| 3669 | standing archer | arquero de pie (rotación de tronco) | Movilidad dinámica, no la dominada/flexión arquero. | APROBADO | arquero de pie (rotación de tronco) |
| 0653 / 1307 | push-up (bosu ball) / push up on bosu ball | flexión sobre bosu | Mismo ejercicio con dos nombres y medios distintos; duplicado declarado. | APROBADO | flexión sobre bosu |
| 1759 | single leg squat (pistol) male | sentadilla pistol a una pierna | El dataset omite los paréntesis de `(male)`; se corrige en `name-fixes.yaml` y se asigna `demo_sex = male`. | APROBADO | sentadilla pistol a una pierna |

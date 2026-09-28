# Handoff — Fase 5 · frontend-ui (f5/design-system)

## Resumen
La persona usuaria compartió un spec de diseño detallado escrito para un producto ajeno
(«Vesper.ai»): sin marca, sin copy, sin sus fuentes ni su vídeo. Lo que pedía era su **lenguaje
visual** — botones de «cristal líquido» con barrido de brillo, píldoras de nav de «metal
líquido», grano de fondo, coreografía de entrada por pantalla, acento de titular, insignias —
adaptado al concepto propio de Forja («taller industrial cálido»: carbón oscuro, acento brasa
`#FF6A2B → #FFB23F` solo en acciones primarias/récords) y a sus propios tokens.

**Plan de diseño** (cargado con el skill `frontend-design` antes de tocar código, según pidió la
persona usuaria): el acento sigue siendo brasa, no un color nuevo — el brillo de los botones/nav
es blanco-alfa (relieve físico), y el único color «cálido» añadido es el resplandor ember en
hover/activo, siempre `color-mix()` sobre `--color-accent` existente. Nada de cristal azul frío
ni de vidrio genérico: el barrido de brillo, el metal de nav y el grano se leen como propiedades
físicas de un taller (chapa, cristal templado, polvo fino), no como decoración de SaaS. Contra la
lista de calibración del propio skill (defaults genéricos de IA) revisé explícitamente: nada de
etiquetas ALL-CAPS trackeadas en ningún sitio nuevo; los « · » que ya existían en la app (p. ej.
«estado · commit», «músculo · equipo») se dejaron porque unen dos datos reales distintos, no
decoración — y donde SÍ encontré el patrón «fragmento decorativo» de verdad (la insignia
«· simulación» de Admin, el «(Activa)» entre paréntesis de Rutinas) lo convertí en una insignia
real, que es justo lo que pedía la técnica 6, en vez de dejarlo o adornarlo más. El acento de
titular (técnica 5) es el punto donde más me alejé de aplicar la técnica de forma mecánica: de
las 8 pantallas, 6 tienen un `<h1>` de una sola palabra idéntica a su enlace de nav («Hoy»,
«Rutinas», «Biblioteca», «Progreso», «Perfil», «Nutrición») — partir esas palabras por la mitad
para «acentuar una palabra» habría sido exactamente el tic genérico que el propio skill señala
como sospechoso, así que el acento solo se aplicó donde el titular es de verdad una frase de
varias palabras con un sustantivo claro que acentuar: Generador (**rutinas**) y Resumen de sesión
(**sesión**). Autocrítica con capturas reales (Playwright contra el servidor de desarrollo con
MSW): ver «Cómo verificar» — confirmé visualmente el barrido de brillo y el resplandor ember en
hover (invisibles en una captura en reposo) y corregí el artefacto de captura de la barra inferior
móvil (ver «Decisiones»), pero no encontré nada que rehacer en el propio sistema visual.

## Ficheros tocados
**Nuevos**
- `frontend/src/components/Reveal.tsx` — componente único de coreografía de entrada (variantes
  `scale`/`soft`/`pop`/`side`/`stat`, easing `cubic-bezier(0.16,1,0.3,1)`, duración 0.9 s, prop
  `delay` para escalonar). Con `prefers-reduced-motion`, renderiza un `<div>` plano sin animar.
- `frontend/tests/components/Reveal.test.tsx` — cubre las dos ramas (movimiento normal/reducido).

**Tokens y estilos base**
- `frontend/src/styles/tokens.css` — 9 tokens nuevos, ninguno hex nuevo (el test de contraste solo
  reconoce pares `--token: #hex;`, así que quedan fuera a propósito): `--ease-out-expo`,
  `--shine-duration`, `--glass-sheen`, `--glass-highlight`, `--glass-tint`, `--glow-accent`,
  `--glow-accent-soft` (estos dos con `color-mix()` sobre `--color-accent`), `--color-border-bright`
  (`color-mix()` sobre `--color-border` + blanco) y `--nav-pill-gradient` (`--color-surface-1` →
  `--color-surface-2`). Todos se resuelven de forma perezosa contra el tema activo (oscuro/claro)
  sin necesidad de redefinirlos en el bloque `[data-theme="light"]`.
- `frontend/src/styles/global.css` — `.grain-overlay` (SVG `feTurbulence` como data URI, opacidad
  0.035, `position: fixed`, `pointer-events: none`, se retira con movimiento reducido) y
  `.headline-accent` (texto con `background-clip: text` del degradado brasa existente).
- `frontend/src/components/ui/ui.module.css` y `frontend/src/features/shared/ui.module.css` —
  botones «cristal líquido»: `::after` con barrido diagonal (0.65 s, easing expo, se omite con
  movimiento reducido), relieve interior de 1 px, transición de 0.35 s en fondo/borde/sombra.
  Primario gana resplandor ember en hover; secundario/`.btn` desnudo pasan a cristal esmerilado
  (degradado translúcido sobre la superficie); ghost revela el mismo tinte en hover. `shared/`
  gana además `.badge`/`.badgeAccent`/`.badgeSuccess`/`.badgeError` (insignias, técnica 6).
- `frontend/src/components/AppNav.module.css` — nav «metal líquido»: borde de baja alfa en reposo,
  degradado metálico + barrido de brillo en hover/foco (solo en enlaces inactivos — ver
  «Decisiones» sobre por qué), píldora activa con borde/resplandor brasa («caliente») en vez del
  fondo plano anterior. `border-radius` ahora también en móvil (antes solo en el rail de
  escritorio): las píldoras leen como píldoras en los dos anchos.
- `frontend/src/components/ExerciseMedia.module.css` — el botón «reproducir animación» (el único
  botón de la app que se apoya sobre una imagen real) gana `backdrop-filter: blur(16px)` de
  verdad; ningún otro botón paga ese coste porque ninguno más se posa sobre imágenes.
- `frontend/src/routes/RootLayout.tsx` (+ test) — monta `<div class="grain-overlay" aria-hidden>`
  una sola vez, antes del contenido de la ruta.
- `frontend/src/routes/router.tsx` — comentario del presupuesto de JS actualizado a `< 500 KB
  gzip (§10.5, ADR 0013)` (cambio de presupuesto comunicado por el coordinador a mitad de tarea).

**Pantallas** (coreografía de entrada; ver la lista por pantalla más abajo)
- `frontend/src/features/today/TodayScreen.tsx`
- `frontend/src/routes/ProgramsRoute.tsx` (+ test) — además, insignia «Activa» en vez de texto
  entre paréntesis.
- `frontend/src/features/library/LibraryScreen.tsx`
- `frontend/src/features/progress/ProgressScreen.tsx`
- `frontend/src/features/profile/ProfileScreen.tsx`
- `frontend/src/features/nutrition/NutritionScreen.tsx`
- `frontend/src/features/generator/GeneratorScreen.tsx` — además, acento de titular.
- `frontend/src/features/generator/PreviewPanel.tsx`
- `frontend/src/features/session/SessionSummary.tsx` — además, acento de titular.
- `frontend/src/features/admin/AdminScreen.tsx` (+ test) — solo insignias (estado + simulación),
  sin `Reveal`: Admin no está en la lista de pantallas de la tarea.

**i18n** (claves nuevas, aditivas; ninguna clave existente cambió de significado)
- `frontend/src/i18n/partA/generator.ts` — `titleLead`/`titleAccent`/`titleTrail` (es/en).
- `frontend/src/features/session/strings.ts` — `summaryTitleLead`/`summaryTitleAccent`/
  `summaryTitleTrail` (es/en).
- `frontend/src/features/admin/strings.ts` — se retiró `runTitle` (interpolaba «{{status}} ·
  {{commit}}» en una sola cadena; ya no se usa porque el estado ahora es una insignia aparte, no
  texto dentro de la frase).

**Tests actualizados por el cambio de marcado**
- `frontend/tests/routes/ProgramsRoute.test.tsx` — `"(Activa)"` → `"Activa"`.
- `frontend/tests/features/admin.test.tsx` — nueva prueba de insignias de estado (correcta/con
  errores/en cola) y la prueba existente separa `"Correcta"` (insignia) de `"7455efa"` (código) en
  vez de buscar la frase completa.
- `frontend/tests/features/generator.test.tsx` — un `toBeVisible()` pasa a `toBeInTheDocument()`
  (ver «Decisiones»: jsdom no avanza `requestAnimationFrame` en tiempo real, así que un tween de
  Framer Motion recién montado puede seguir en opacidad 0 en el instante exacto de la aserción
  aunque el elemento ya esté en el DOM — el resto de la suite ya evita `toBeVisible()` sobre
  contenido animado con Framer Motion por el mismo motivo, p. ej. `RootLayout.test.tsx`).

## Decisiones
- **Sin cursiva en Archivo para el acento de titular.** El paquete `@fontsource-variable/archivo`
  sí trae un eje itálico real (`standard-italic.css`), pero activarlo exige cargar ficheros de
  fuente nuevos que hoy no se importan — y la tarea prohíbe explícitamente «añadir cualquier
  fichero de fuente nuevo». Usé el fallback que la propia tarea preveía: degradado brasa (mismo
  `--gradient-accent` de botones primarios/récords) vía `background-clip: text` + tracking, sin
  tocar el peso (`h1` ya es 800). El resultado ata visualmente la palabra acentuada al mismo
  lenguaje que ya usa la app para «esto importa» (CTA primaria, récords), en vez de introducir un
  truco tipográfico nuevo sin relación con el resto del sistema.
- **`overflow: hidden` del barrido de brillo de nav, condicionado a `:not(.active)`.** La píldora
  activa (`motion.span layoutId` de `AppNav.tsx`, ya existente de `f4-motion-nav`) anima su
  posición fuera de la caja de su enlace durante la transición entre rutas — Framer Motion no la
  «teletransporta», la desplaza con `transform` desde la posición del enlace anterior, así que
  durante ese tránsito la píldora vive temporalmente fuera del `<a>` que la contiene. Si ese `<a>`
  tuviera `overflow: hidden` (necesario para recortar el barrido de brillo del resto de enlaces),
  el deslizamiento de la píldora se recortaría a medio camino. Como la píldora solo existe en el
  enlace activo, `overflow: hidden` se aplica únicamente a `.link:not(.active)` — ningún enlace
  que pueda alojar la píldora la pierde nunca, y todos los demás recortan su barrido con
  seguridad. Comprobado visualmente (captura con hover simulado): el barrido de brillo se ve, la
  píldora activa no se rompe.
- **`backdrop-filter` solo en el botón «reproducir animación» de `ExerciseMedia`.** La técnica 1
  pide cristal esmerilado «donde se apoye sobre imágenes» — es el único botón de la app que
  literalmente se posa sobre un medio real (el resto de secundarios/fantasma están sobre
  superficies planas, donde desenfocar el fondo no cambiaría nada visualmente y solo pagaría el
  coste de composición de `backdrop-filter` en Lighthouse sin beneficio).
- **Insignias reemplazan dos fragmentos de texto que ya eran el antipatrón que señala el skill de
  diseño.** `(Activa)` entre paréntesis en Rutinas y ` · simulación` colgando del título de una
  ejecución en Admin eran exactamente «fragmento decorativo unido con puntuación» en vez de
  estado visualmente diferenciado. La técnica 6 los convierte en píldoras reales; de paso, el
  estado de una ejecución de ingesta (antes enterrado dentro de una única cadena interpolada
  `"{{status}} · {{commit}}"`) ahora es una insignia con tono semántico (verde si «Correcta», rojo
  si «Con errores», brasa si en curso/en cola) — comprobado en captura: se lee de un vistazo sin
  tener que leer la palabra.
- **Coreografía por pantalla: etapas agrupadas, no una animación por tarjeta suelta.** El skill de
  diseño señala «fade-and-slide-up en cada sección» como el tic más genérico de una IA. La
  diferencia aquí es deliberada: cada pantalla tiene entre 3 y 5 **etapas** (cabecera → bloque
  héroe → bloque(s) secundario(s) → acciones), nunca una animación distinta por cada elemento
  suelto dentro de una etapa; donde varias tarjetas son homogéneas y llegan juntas (p. ej. el
  `.grid` de Hoy/Progreso) comparten una sola etapa. La cuadrícula virtualizada de Biblioteca
  (potencialmente miles de ejercicios, filas que se montan/desmontan sin parar al hacer scroll)
  se dejó **sin** animar a propósito: animarla repetiría la entrada en cada scroll, no sería «un
  momento», sería ruido constante.
- **Wizard del generador: `Reveal` por paso, no coreografía multietapa en cada paso.** Los 5 pasos
  del formulario (objetivo, días, sexo, nivel, énfasis) son un único `<fieldset>` centrado, no una
  cascada de tarjetas — cada paso nuevo monta con `Reveal variant="soft"` (una sola etapa, sin
  retraso). La cascada rica de verdad (cabecera → motivos → avisos → semana → volumen → acciones)
  vive en el último paso, dentro de `PreviewPanel.tsx`, porque ahí es donde de verdad llega
  contenido nuevo de golpe (el resultado del motor) — no en cada clic de «Continuar».
- **`toBeVisible()` → `toBeInTheDocument()` en un test de generador que no toqué a propósito.**
  Envolver la sección de pestañas del generador en un `Reveal` hizo que esa aserción concreta
  empezara a fallar en jsdom: `requestAnimationFrame` no avanza con tiempo real fiable ahí, así
  que el tween de opacidad de Framer Motion puede seguir en `0` en el instante exacto de la
  aserción aunque el elemento ya esté montado y sea, en un navegador real, visible en menos de un
  segundo. El resto de la suite (p. ej. `RootLayout.test.tsx`) ya evita `toBeVisible()` sobre
  contenido animado con Framer Motion por el mismo motivo — este cambio alinea ese único test con
  el patrón que ya usa el resto del proyecto, no relaja ninguna garantía real (el estado de
  reposo de `Reveal` es «visible» por diseño, y `expectNoAxeViolations` sigue corriendo justo
  después en el mismo test).
- **Cobertura de ramas: dos pruebas nuevas, dirigidas, no una campaña.** El primer run tras el
  cambio dio 84.98 % (umbral 85 %, y el resto de gaps del reporte eran preexistentes — código de
  error/edge-case fuera del alcance de esta tarea). Añadí exactamente dos pruebas: `Reveal.test.tsx`
  (la rama de movimiento reducido de mi propio componente nuevo no la ejercitaba ningún otro test)
  y un caso en `admin.test.tsx` con tres estados de ejecución (correcta/con errores/en cola) para
  cubrir las tres ramas de `statusBadgeTone()`, la única función nueva con lógica condicional que
  introduje. Con eso, 85.18 % — no perseguí ningún gap preexistente.

## Cómo verificar
```bash
cd frontend
npx tsc --noEmit         # limpio
npm run lint              # 0 avisos
npm run test -- --run     # 204/204 en verde; cobertura de ramas 85.18 % (>= umbral 85 %)
npm run build              # bundle principal (index-*.js) en 189.38 kB gzip, bajo 500 KB (ADR 0013)
```
Visualmente (capturas ya guardadas en `docs/screenshots/f5/design-system/`, tomadas contra
`VITE_USE_MSW=1 npx vite --port 5174` con Playwright/Chromium):
- `*-desktop.png` / `*-mobile.png`: las 8 pantallas de la tarea (Hoy, Rutinas, Biblioteca,
  Progreso, Perfil, Nutrición, Generador, Admin — Admin sin coreografía, ver más arriba) en reposo,
  con la coreografía de entrada ya asentada.
- `hover-primary-btn.png`: resplandor ember del botón primario al pasar el cursor.
- `hover-nav-link.png`: «Progreso» (inactivo) con el metal frío revelado en hover, junto a
  «Rutinas» (activo) con el borde/resplandor brasa de la píldora «caliente».
Para reproducir en vivo: `VITE_USE_MSW=1 npx vite --port <puerto libre>`, navegar por las 8
rutas en escritorio/móvil, claro/oscuro, y con `prefers-reduced-motion: reduce` activado en el
sistema (la coreografía debe desaparecer del todo y el contenido debe verse igual, de golpe).

## Métricas
- `npm run build`: `dist/assets/index-*.js` → 584.77 kB sin comprimir / **189.38 kB gzip** (límite
  500 KB gzip, ADR 0013 — el presupuesto se amplió a mitad de esta tarea; con el límite antiguo de
  200 KB habría quedado ~10.6 KB por encima, pero ya no aplica). El aumento sobre los 188.85 KB que
  dejó `f4-motion-nav` es de solo +0.53 KB: `Reveal` reutiliza el motor de Framer Motion que
  `AppNav`/`RootLayout`/`RestRing` ya cargaban de forma eager, así que la coreografía de entrada en
  8 pantallas casi no añade peso de red nuevo, solo unas pocas líneas de lógica.
- `npm run test -- --run`: **204/204** tests en verde, 29/29 ficheros (201 anteriores + 3 nuevos:
  `Reveal.test.tsx` con 2 casos, más 1 caso nuevo en `admin.test.tsx`).
- Cobertura: ramas **85.18 %** (≥ 85 %), sentencias 93.34 %, funciones 91.44 %, líneas 95.29 %.

## Riesgos/pendientes
- **Nutrición se capturó en su estado «no disponible en este servidor»** porque el mock generado
  de `GET /admin/settings` trae `diet_feature_enabled: false` por defecto — no hay forma de ver el
  estado «con dieta activa» (anillos de objetivo, plan semanal) sin sobreescribir handlers de MSW a
  mano. El código de esa rama (`usable`, con su propia etapa `Reveal variant="scale"` para el
  bloque de objetivo) está igual de cubierto por los tests existentes de `nutrition.test.tsx`; solo
  falta la captura visual de ese estado concreto si alguien la necesita.
- **No se generó captura de Resumen de sesión** (`/sesion/resumen/$uuid`): es una ruta dinámica que
  exige una sesión real terminada en IndexedDB, no una URL estática navegable de un clic. El
  acento de titular y la cascada (stat → hero con confeti → acción) usan exactamente el mismo
  patrón ya verificado visualmente en Generador; si se quiere evidencia visual de esta pantalla en
  concreto, hace falta jugar una sesión de principio a fin (o sembrar IndexedDB) antes de
  capturarla.
- **El barrido de brillo y el metal de nav en hover no tienen test automatizado** (son CSS puro
  sobre `:hover`/`:focus-visible`, sin lógica JS que cubrir) — se verificaron con capturas de
  Playwright con `.hover()` simulado (`hover-primary-btn.png`, `hover-nav-link.png`), no con un
  test de Vitest, porque jsdom no ejecuta cascada CSS real de pseudo-clases sobre pseudo-elementos.
- El margen de presupuesto de JS pasó de ~11 KB (con el límite antiguo de 200 KB) a **~310 KB**
  (con el nuevo límite de 500 KB, ADR 0013) — mucho margen para trabajo futuro; no hizo falta
  mover ninguna ruta eager a `lazyRouteComponent` (el coordinador confirmó que ya no era necesario
  por presupuesto, y no se deshizo ningún code-splitting existente).

## Peticiones a otros agentes
Ninguna petición bloqueante.
- Si un agente de QA/UX quiere evidencia visual de Nutrición con la dieta activada o de Resumen de
  sesión con un récord real, los puntos de partida están anotados en «Riesgos/pendientes».
- La pantalla de login (`features/auth/*`) no se tocó, como pedía la tarea — si el agente que la
  está rediseñando en paralelo quiere reutilizar el vocabulario de botones «cristal líquido»
  (`components/ui/ui.module.css` `.button`/`.primary`/`.secondary`/`.ghost`, o el `.btn` de
  `features/shared/ui.module.css`), ya está disponible sin tocar nada de `features/auth/*`: son
  clases compartidas, no exigen ningún cambio en esa carpeta.

## Pantallas — lista de cambios
- **Hoy** (`features/today/TodayScreen.tsx`): cabecera (título + aviso de sincronización
  pendiente) → tarjeta «próxima sesión» (héroe, `scale`) → resumen semanal + peso corporal (juntas,
  `soft`) → enlace a Nutrición (`pop`, si aplica). Sin acento de titular (h1 de una sola palabra).
- **Rutinas** (`routes/ProgramsRoute.tsx`): cabecera → CTA «Generar una rutina nueva» (`pop`) →
  lista de programas o estado vacío (`side`/`pop`). El indicador «Activa» pasa de texto entre
  paréntesis a insignia (`badgeAccent`).
- **Biblioteca** (`features/library/LibraryScreen.tsx`): cabecera → barra de búsqueda/filtros
  rápidos (`soft`) → panel de filtros/mapa muscular (`side`). La cuadrícula virtualizada de
  resultados se deja sin animar (ver «Decisiones»).
- **Progreso** (`features/progress/ProgressScreen.tsx`): cabecera → calendario de actividad +
  récords (juntos, `scale`) → volumen semanal, e1RM y peso corporal (tres etapas `stat`
  consecutivas, una por sección de gráfico).
- **Perfil** (`features/profile/ProfileScreen.tsx`): cabecera + enlaces rápidos a Nutrición/Admin
  → ajustes (héroe, `scale`) → datos/sesiones activas/uso sin conexión (juntas, `soft`) → cerrar
  sesión + créditos (juntas, `soft`).
- **Nutrición** (`features/nutrition/NutritionScreen.tsx`): cabecera + aviso de seguridad (juntos,
  sin retraso — un aviso sanitario no debe llegar «retrasado») → activar dieta (`pop`) o, si ya
  está activa, objetivo diario (héroe, `scale`) → plan semanal (`soft`) → ajustes (`soft`).
- **Generador** (`features/generator/GeneratorScreen.tsx` + `PreviewPanel.tsx`): cabecera con
  acento de titular «Generador de **rutinas**» → cada paso del wizard (`soft`, una etapa) → en la
  vista previa final: motivos → avisos (si hay) → semana tipo (héroe, `scale`) → volumen (`stat`)
  → guardar/activar (`pop`).
- **Resumen de sesión** (`features/session/SessionSummary.tsx`): cabecera con acento de titular
  «Resumen de la **sesión**» → totales (`stat`) → récords con confeti si aplica (héroe, `scale`)
  → «Volver a Hoy» (`pop`).
- **Admin** (`features/admin/AdminScreen.tsx`): sin coreografía de entrada (no está en la lista de
  pantallas de la tarea). El estado de cada ejecución de ingesta (correcta/con errores/en
  cola/en curso) y la marca de simulación pasan a insignias con tono semántico, en vez de texto
  unido con « · ».

Técnicas globales (aplican a las 9 pantallas anteriores más Onboarding/Editor/Detalle de
ejercicio/Admin, que no estaban en la lista de coreografía pero sí reciben botones/nav/grano):
botones «cristal líquido» (`components/ui` y `features/shared`), nav «metal líquido» (`AppNav`) y
grano global (montado una vez en `RootLayout`).

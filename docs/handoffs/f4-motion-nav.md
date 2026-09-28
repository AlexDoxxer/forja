# Handoff — Fase 4 · frontend-ui (f4/motion-nav)

## Resumen
Segunda pasada sobre el pulido de `f4/visual-polish`: se añadió `framer-motion` y se usó en
**exactamente** los cuatro momentos pedidos (nada más), y se reagrupó `AppNav` en dos secciones.
Plan de diseño de partida (antes de tocar código): Forja ya tiene un concepto propio —
taller industrial cálido, brasa como acento raro y deliberado — así que el criterio no era
«añadir Framer Motion a todo lo que se mueva» sino elegir dos momentos con carácter propio del
concepto (el anillo de descanso «enfriándose» y un confeti-brasa de récord) y dos utilidades
discretas que cualquier app pulida necesita (píldora de nav que desliza en vez de parpadear,
crossfade de ruta) sin añadir capas de decoración genérica (nada de números 01/02/03, nada de
`→`, nada de mayúsculas trackeadas en los grupos de nav — «Entrenar»/«Cuenta» en minúsculas
normales, como ya escribe el resto de la app).

## Ficheros tocados
- `frontend/package.json` / `package-lock.json` — nueva dependencia `framer-motion@^11.18.2`
  (única añadida; nada de librerías de confeti de terceros).
- `frontend/src/components/AppNav.tsx` / `AppNav.module.css` **(reescritos)**:
  - Píldora activa: `motion.span` con `layoutId="app-nav-active-pill"` compartido entre todos
    los enlaces. Al cambiar de ruta, dos DOM distintos (viejo enlace activo → nuevo) comparten
    `layoutId`; Framer Motion mide el rectángulo del que desaparece y anima el nuevo desde esa
    posición/tamaño hasta la suya con un spring (`stiffness: 380, damping: 32`) — el efecto es
    un deslizamiento «magnético» a lo largo del riel, no un fundido. La píldora ahora cubre el
    enlace entero (antes solo el icono en móvil); en CSS tiene `z-index: -1` así que el icono y
    la etiqueta (elementos estáticos, sin `position`) siempre pintan encima sin necesidad de
    darles su propio `z-index`.
  - Con `prefers-reduced-motion`, la píldora se renderiza como un `<span>` normal sin
    `layoutId`: aparece/desaparece con el cambio de clase, sin ninguna animación de posición.
  - Reagrupado en «Entrenar» (Hoy, Rutinas, Biblioteca, Progreso) y «Cuenta» (Nutrición si está
    disponible, Perfil, Admin si es admin). El marcado tiene siempre los dos `<div class="group">`
    con un subtítulo cada uno y un separador entre ellos; en el rail de escritorio (`≥1024px`)
    esos `<div>` son `flex-direction: column` reales con el subtítulo visible y el separador
    como línea; en la barra inferior móvil, `.group { display: contents }` los «aplana» (sus
    hijos pasan a ser hijos flex directos de `.nav`) y el subtítulo/separador quedan en
    `display: none` — una sola fila, sin agrupado visual, como pedía la tarea. El orden lógico
    de los enlaces no cambió (nunca se quitó ni se renombró ninguna ruta).
  - `isItemActive()` sustituye a `activeProps`/`activeOptions` de `Link`: se necesitaba el
    booleano en JS (no solo la clase CSS) para decidir si se monta la píldora, así que se
    calcula con `useRouterState` igual que hace `RootLayout`. Misma semántica que antes (exacta
    solo para «Hoy», prefijo por segmento para el resto).
- `frontend/src/i18n/resources.ts` — `nav.groupTrain`/`nav.groupAccount` (es: «Entrenar»/
  «Cuenta»; en: «Train»/«Account»).
- `frontend/src/routes/RootLayout.tsx` — el `<Outlet/>` se envuelve en
  `AnimatePresence mode="wait"` + `motion.div` con `key={pathname}`: fundido de opacidad
  0→1 en 150 ms (`ease: "easeInOut"`), sin desplazamiento ni escala — una sola fase, no una
  coreografía. Con movimiento reducido, `initial`/`exit` valen `1` y la duración es `0`
  (equivalente a no animar nada, pero sin ramas de código separadas para el JSX).
- `frontend/src/features/session/RestRing.tsx` **(reescrito)** — el momento con más «carácter»
  de esta tarea:
  - El progreso (`strokeDashoffset`) ahora se anima con `motion.circle` (`duration: 0.25s`,
    `ease: "linear"`, sincronizado con el intervalo de `useNow`) en vez de saltar entre
    lecturas del reloj cada 250 ms: se ve como un barrido continuo, no como un tictac.
  - En los **últimos 5 segundos**, el anillo entero (`motion.div` envolvente) hace una
    respiración sutil: `scale` 1 → 1.04 → 1 y un `drop-shadow` que crece y decrece entre
    transparente y un halo naranja de 16 px, en un ciclo de 1.1 s que se repite
    (`repeat: Infinity`, `ease: "easeInOut"`) hasta que el descanso termina. A la vez, el trazo
    del anillo (`stroke`) cicla entre `#ff6a2b` y `#ffb23f` (los mismos tonos de
    `--color-accent`/`--color-accent-2`; Framer Motion necesita valores literales para
    interpolar color, así que están como constantes con un comentario que remite a
    `tokens.css` — **no se tocó ningún token**). La lectura pretendida: una brasa que se enfría
    /recalienta mientras cuenta atrás, no un parpadeo de alerta genérico.
  - Con `prefers-reduced-motion`, no hay pulso ni ciclo de color (el anillo se queda en
    `#ff6a2b` fijo) y el `strokeDashoffset` salta sin transición; el conteo numérico y el
    `aria-live` (sin cambios) siguen siendo la señal accesible principal.
- `frontend/src/features/session/session.module.css` — se quitó el `stroke` fijo de
  `.ringValue` (ahora lo anima `RestRing.tsx`) y se añadió `.trophyWrap` (ancla de posición
  para el confeti, ver debajo).
- `frontend/src/components/PrConfetti.tsx` / `PrConfetti.module.css` **(nuevos)** — el «confeti
  discreto solo en récord personal» que pedía MASTER_PROMPT §10.1 y que aún no existía: 8 motas
  de 4–7 px en los dos tonos brasa, cada una estalla desde el centro hacia un ángulo/distancia
  con algo de aleatoriedad (`Math.random`, sin sembrar: es decorativo, no necesita ser
  determinista) y se desvanece en 0.85 s (`ease: "easeOut"`). Menos de 1.5 s en total. `aria-hidden`
  (no aporta información que el texto del récord no dé ya). Export **por defecto** para poder
  cargarlo con `React.lazy()`.
- `frontend/src/features/session/SessionSummary.tsx` — `PrConfetti` se importa con
  `lazy(() => import("../../components/PrConfetti"))` y se monta (envuelto en
  `<Suspense fallback={null}>`) junto al icono de trofeo de la sección «Récords» **solo** cuando
  `remote.new_records.length > 0` y no hay `prefers-reduced-motion`. Como la consulta de récords
  deja de refrescarse en cuanto llega el primer resultado con datos (`refetchInterval` ya
  existente), el confeti se dispara una sola vez, no en cada refetch.
- `frontend/tests/setup.ts` — el mock global de `window.matchMedia` gana `addListener`/
  `removeListener` (API heredada, además de `addEventListener`/`removeEventListener`): Framer
  Motion usa internamente su propio `useReducedMotion` (distinto del hook del proyecto) y esa
  API heredada para suscribirse, y sin ella cualquier `motion.*` que monte en un test lanzaba
  `motionMediaQuery.addListener is not a function` — esto rompía 6 ficheros de test que no
  tienen nada que ver con esta tarea (montaban `AppNav`/`RootLayout` de forma indirecta). Es un
  arreglo de infraestructura de test necesario por la dependencia nueva, no un cambio de
  comportamiento.
- `frontend/tests/components/AppNav.test.tsx` — dos casos nuevos: los subtítulos de grupo están
  en el DOM, y el enlace activo lleva `aria-current="page"` (con movimiento reducido, para cubrir
  también esa rama).
- `frontend/tests/components/PrConfetti.test.tsx` **(nuevo)** — renderiza el componente suelto y
  comprueba que las motas (6–10) están dentro de un contenedor `aria-hidden`.
- `frontend/tests/routes/RootLayout.test.tsx` **(nuevo)** — monta `RootLayout` con un router de
  memoria mínimo y dos rutas de prueba; un caso con movimiento normal y otro con
  `prefers-reduced-motion`, ambos comprueban que el contenido de la ruta activa se muestra.
- `docs/TASKS.md` — fila `F4-FE-02` añadida a la Fase 4.

## Decisiones
- **La píldora cubre el enlace entero, no solo el icono.** El diseño anterior (visual-polish)
  tenía un fondo pequeño solo alrededor del icono en móvil y un fondo de fila completa en
  escritorio — dos formas distintas para la misma cosa. Unificarlo a «toda la caja del enlace,
  en ambos anchos» simplifica el CSS a una sola regla (`inset: 0`) y hace que la animación
  `layoutId` tenga una única geometría que interpolar en vez de tener que reconciliar dos formas
  cuando cambia el breakpoint. Es un target de toque ligeramente más grande en móvil, no un
  cambio de jerarquía visual (mismo color, mismo radio).
- **El agrupado de nav es CSS puro (`display: contents`), no dos layouts de React distintos.**
  Con una sola estructura de marcado y `display: contents` en móvil, los dos `<div>` de grupo
  «desaparecen» del árbol de caja y sus hijos se convierten en flex items directos de `.nav` —
  la fila queda exactamente igual que antes de esta tarea, sin lógica condicional de
  renderizado por ancho de pantalla (que además sería incorrecta en SSR/hidratación). El coste
  es que en móvil, para las cuentas con Nutrición y Admin, el orden visual pasa de
  «Hoy·Rutinas·Biblioteca·Progreso·Perfil·Nutrición·Admin» a
  «Hoy·Rutinas·Biblioteca·Progreso·Nutrición·Perfil·Admin» (Perfil se mueve junto a Nutrición y
  Admin, su grupo lógico). Para una cuenta normal (sin dieta ni admin) el orden móvil no cambia
  en absoluto. No hay test que fije el orden anterior, así que no se rompe nada, pero se deja
  anotado por si el equipo de producto prefiere el orden viejo en móvil.
- **`z-index: -1` en la píldora en vez de `z-index: 1` en el icono/etiqueta.** Un descendiente
  posicionado con `z-index` negativo pinta *detrás* del contenido estático del mismo contexto de
  apilamiento (regla del CSS 2.1 §E), así que ni el icono ni la etiqueta necesitan su propio
  `position`/`z-index` para quedar por encima — menos reglas CSS, mismo resultado.
- **`RestRing` y `PrConfetti` usan valores de color literales (`#ff6a2b`/`#ffb23f`), no
  `var(--color-accent)`.** Framer Motion interpola color animando valores JS; no puede
  interpolar una custom property de CSS directamente. Los literales están comentados y remiten
  a `tokens.css` para que quede claro que son el mismo acento «brasa», no un color nuevo —
  **no se ha tocado ningún valor hex en `tokens.css`**.
- **El confeti vive en `session/SessionSummary.tsx`, no en `progress/ProgressScreen.tsx`.** La
  tarea permitía cualquiera de los dos sitios («session summary / progress»). El resumen de
  sesión es el único de los dos que es de verdad un *momento*: se ve una sola vez, justo después
  de conseguir el récord. La sección de récords de Progreso es una lista histórica que la
  persona puede visitar cualquier día — lanzar confeti cada vez que alguien mira su lista de
  PRs antiguos sería ruido, no celebración. El componente `PrConfetti` se dejó en
  `src/components/` (no dentro de `features/session/`) precisamente para que Progreso pueda
  reutilizarlo si un agente futuro decide que también quiere el momento ahí (ver «Peticiones»).
- **`isItemActive()` sustituye al cálculo de actividad de `Link`.** Se necesitaba el booleano en
  JS para decidir si montar `motion.span` o `<span>` plano; `activeProps`/`activeOptions` de
  TanStack Router solo aplican una clase condicionalmente, no exponen el booleano a un hijo de
  forma sencilla. La función replica la misma semántica que ya había (exacta solo en «Hoy»,
  prefijo de segmento en el resto) — no es un cambio de comportamiento de navegación.
- **`framer-motion` se importa de forma estática (no `LazyMotion`) en `AppNav`, `RootLayout` y
  `RestRing`.** Se evaluó `LazyMotion` + `domAnimation`/`domMax` (los paquetes «ligeros» de
  Framer Motion) para reducir el peso, pero la píldora de nav necesita animación de `layout`
  (`layoutId`), que solo está en el paquete `domMax` — de tamaño casi idéntico al import
  completo. Como además `AppNav` está siempre montado (no es una ruta perezosa) y `RestRing`
  vive dentro de `SessionRoute`, que ya se importaba de forma **eager** en `router.tsx` antes de
  esta tarea (a diferencia de Biblioteca/Editor/Generador/Nutrición/Admin, que sí son
  `lazyRouteComponent`), no había forma de sacar `framer-motion` del bundle principal sin
  reestructurar ese enrutado — fuera del alcance de esta tarea. Lo que sí se diseñó como
  perezoso genuino es `PrConfetti` (único uso realmente condicional/raro): se importa con
  `React.lazy()` y aparece como chunk propio en el build (`PrConfetti-*.js`, 0.54 kB gzip) — se
  ve en «Métricas».

## Cómo verificar
```bash
cd frontend
npx tsc --noEmit         # limpio
npm run lint              # 0 avisos
npm run test -- --run     # 201/201 tests en verde, cobertura de ramas 85.03 % (>= umbral)
npm run build              # bundle principal (index-*.js) en 188.85 kB gzip, bajo 200 KB
```
Visualmente (móvil y escritorio, claro y oscuro):
- Navegar entre `/`, `/rutinas`, `/biblioteca`, `/progreso`, `/perfil`: la píldora del enlace
  activo debe deslizarse hasta el nuevo enlace (no aparecer de golpe) y el contenido de la
  pantalla debe hacer un fundido corto (≈150 ms) al cambiar de ruta.
- En escritorio (`≥1024px`), el rail lateral debe mostrar «Entrenar» como subtítulo sobre
  Hoy/Rutinas/Biblioteca/Progreso, una línea divisoria, y «Cuenta» sobre
  Nutrición (si aplica)/Perfil/Admin (si aplica). En móvil, la barra inferior sigue siendo una
  sola fila sin subtítulos.
- Con `prefers-reduced-motion: reduce` activado en el sistema/navegador, repetir lo anterior: la
  píldora debe cambiar de sitio sin deslizamiento, el fundido de ruta debe desaparecer, y el
  anillo de descanso no debe pulsar en los últimos 5 s.
- Iniciar una sesión, hacer una serie con descanso configurado y esperar a los últimos 5 s: el
  anillo debe respirar (escala + halo) y el trazo debe ciclar entre los dos tonos brasa.
- Terminar una sesión que produzca un récord nuevo (o usar el ejemplo de
  `player.test.tsx`/MSW): en el resumen, junto al icono de trofeo de «Récords», deben saltar
  unas motas brasa que se desvanecen en menos de 1.5 s.

## Métricas
- `npm run build`: `dist/assets/index-*.js` → 582.50 kB sin comprimir / **188.85 kB gzip**
  (< 200 KB, con ~11 KB de margen — bajó de los ~50 KB de margen que dejaba `f4/visual-polish`
  porque `framer-motion` se suma al bundle principal; ver «Decisiones» sobre por qué no se pudo
  diferir más sin tocar el enrutado). `PrConfetti-*.js` es un chunk aparte de **0.54 kB gzip**
  (confirma que el `React.lazy()` funciona: solo se descarga cuando hace falta).
- `npm run test -- --run`: **201/201** tests en verde, 28/28 ficheros (196 anteriores + 5
  nuevos: 2 en `AppNav.test.tsx`, `PrConfetti.test.tsx`, 2 en `RootLayout.test.tsx`).
- Cobertura de ramas global: **85.03 %**, por encima del umbral del 85 % configurado en
  `vite.config.ts`. Esto **cierra** el hueco preexistente que `f4-visual-polish.md` dejó
  documentado (84.80 % en esa rama, 84.66 % en `main`): los tests nuevos de `RootLayout` y
  `AppNav` (movimiento reducido) cubrieron ramas de `useReducedMotion`/`RootLayout` que antes
  nunca se ejercitaban con `prefers-reduced-motion: reduce`, y el test de `PrConfetti` evitó que
  el componente nuevo se quedara en 0 % arrastrando la media hacia abajo.

## Riesgos/pendientes
- El margen de presupuesto de JS inicial bajó de ~50 KB a ~11 KB gzip. Si una tarea futura añade
  más peso al bundle principal (otra librería, más código en `AppNav`/`RootLayout`/rutas
  eager), puede superar los 200 KB. La palanca más clara para recuperar margen sin tocar esta
  tarea: convertir `sessionRoute`/`progressRoute`/`profileRoute`/`programsRoute` en
  `lazyRouteComponent` en `router.tsx` (como ya lo son Biblioteca/Editor/Generador/
  Nutrición/Admin) — eso sacaría `RestRing` (y por tanto buena parte del uso de
  `framer-motion`) del chunk principal. No se hizo aquí porque es un cambio de arquitectura de
  enrutado fuera del alcance de «añadir Framer Motion a 4 sitios concretos», y tocar qué rutas
  son perezosas tiene su propio radio de impacto (tiempos de Lighthouse LCP en `/` vs. en
  sesión) que merece su propia verificación.
- El orden de los enlaces en la barra inferior móvil cambia ligeramente para cuentas con
  Nutrición **y** Admin a la vez (Perfil pasa a estar junto a Nutrición/Admin en vez de antes de
  ellos) — ver «Decisiones». Ningún test fija el orden anterior; si el equipo de producto lo
  quiere igual que antes, es un cambio de una línea (mover el objeto de Perfil de vuelta al
  array de `TRAIN_ITEMS` en `AppNav.tsx`, con el coste de que entonces «Perfil» ya no viviría
  bajo el subtítulo «Cuenta» en escritorio).
- No se generaron capturas (Playwright) de las animaciones nuevas — son movimiento, no estado
  estático, así que una captura no las representa bien; la sección «Cómo verificar» describe el
  timing exacto en su lugar. Si se necesita evidencia en vídeo, un agente con navegador (o
  `run`) puede grabarlas contra esta rama.
- No se tocó `ProgressScreen.tsx`: sigue sin confeti en su sección de récords (decisión
  deliberada, ver «Decisiones»). Si un agente de producto decide que Progreso también debe
  celebrar records recientes (p. ej. solo los de los últimos 7 días), `PrConfetti` ya está listo
  para importarse ahí con el mismo patrón `React.lazy` + `Suspense`.

## Peticiones a otros agentes
Ninguna petición bloqueante.
- Si un agente de rendimiento/DevOps quiere recuperar margen de presupuesto de JS inicial, la
  vía más directa es la que se apunta en «Riesgos»: hacer perezosas `sessionRoute`/
  `progressRoute`/`profileRoute`/`programsRoute` en `frontend/src/routes/router.tsx`.
- Si el equipo de producto/UX revisa el nuevo orden de la barra inferior móvil (cuentas con
  Nutrición y Admin) y prefiere el orden anterior, avisar para revertir esa línea de
  `AppNav.tsx` (ver «Riesgos»).

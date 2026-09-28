# Handoff — Fase 5 · frontend-ui (f5/login-landing)

## Resumen
`LoginScreen.tsx` (antes: un formulario desnudo y un enlace «Crear cuenta») se convierte en la
landing de Forja — la app es autoalojada y solo accesible tras iniciar sesión, así que este es el
único «momento cero» que existe, no hay sitio de marketing aparte. Se adaptan las técnicas de un
spec de landing de un producto ajeno («Vesper.ai», que el usuario compartió como referencia de
técnicas, no de marca) al sistema de diseño propio de Forja (MASTER_PROMPT §10.1: taller
industrial cálido, carbón + brasa) — sin su marca, su copy, sus fuentes ni su vídeo de CloudFront
(no se usa ningún `<video>` ni URL externa en ningún punto). Toda la lógica de acceso existente
(`POST /auth/login`, mensajes de error por estado HTTP, enlace a `/onboarding`, aria) se conserva
intacta; solo cambia la presentación.

**Plan de diseño** (escrito antes de tocar código, con la skill `frontend-design`, usando solo
tokens existentes de `tokens.css`):
> Color: carbón `--color-bg` de fondo, superficies `--color-surface-1`/`--color-surface-2` para
> el vidrio esmerilado, brasa `--color-accent`→`--color-accent-2` (`--gradient-accent`) reservada
> **solo** para el botón primario, la palabra de acento del titular y el icono de la insignia —
> nunca para las tres estadísticas ni el cuerpo de texto, siguiendo la regla ya establecida en
> `f4-motion-nav.md` de que la brasa es un acento raro y deliberado. Tipografía: `--font-display`
> (Archivo Variable autoalojada) en el titular, con la palabra «Forja» en itálica real (el
> paquete `@fontsource-variable/archivo` trae un eje itálico completo — se comprobó en
> `node_modules` antes de usarlo) más el degradado brasa vía `background-clip:text`; `--font-body`
> (Inter Variable) en todo lo demás. Maquetación: rejilla de tres filas de viewport completo en
> escritorio (barra superior · hero anclado abajo-centro · pie de estadísticas), todo centrado
> —Forja no tiene un rail de navegación que alinear a la izquierda en esta pantalla, y un único
> «momento de entrada» centrado encaja con el concepto de un golpe de yunque cayendo en el
> centro—, con la barra superior como única fila de borde a borde (marca a la izquierda, acción
> secundaria a la derecha, como una cabecera de taller). Principios: un único acento deliberado
> (la palabra «Forja», que es a la vez la marca y el imperativo de «forjar» — el tratamiento
> tipográfico representa lo que la palabra ya significa, no decora una palabra cualquiera); el
> resplandor de fondo es la temperatura ambiente de la escena, nunca el mensaje — muy lento, de
> baja opacidad, con velo hacia el texto; las estadísticas son tres frases cortas con icono de
> línea, no fichas de KPI con números gigantes (Forja no tiene métricas de crecimiento que
> presumir: es software autoalojado, no un SaaS con un dashboard de negocio — un número enorme
> sería fingir una categoría de dato que estos hechos no tienen).

**Revisión contra la lista de «tics genéricos» de la skill** (pedida explícitamente por el
usuario antes de construir): sin fondo crema+serif+terracota ni «SaaS card kit» (no hay tarjetas
en esta pantalla); el dúo carbón+brasa está anclado por MASTER_PROMPT §10.1 desde antes de esta
tarea, no es un valor por defecto elegido aquí; sin eyebrow en mayúsculas trackeadas (la insignia
«Entrenamiento autoalojado» va en minúsculas normales); sin cadenas unidas por «·» ni etiquetas
«PALABRA — fragmento»; sin «→» en ningún botón o enlace; sin marcadores 01/02/03 (las
estadísticas no son una secuencia); sin monoespaciada para datos pequeños (los números usan
`--nums-tabular`, ya en `global.css`). El único punto de la lista que sí se usa a propósito —
acentuar una sola palabra del titular— es una instrucción explícita del encargo, no un default: se
hizo que la palabra elegida (el propio nombre de marca, que además es gramaticalmente el verbo de
la frase) se ganara el tratamiento en vez de caer sobre una palabra cualquiera.

## Ficheros tocados
- `frontend/src/features/auth/LoginScreen.tsx` **(reescrito)** — misma función `submit` byte a
  byte (estado `email`/`password`/`error`/`busy`, `POST /auth/login`, `queryClient.clear()`,
  `navigate("/")`, mensajes por `status` 429/401-422/otro, `catch` → mensaje genérico). Nuevo:
  - `reveal()`: helper que construye `initial`/`animate`/`transition` de Framer Motion a partir
    de un `initial`/`animate` objetivo y un `delay`; con `useReducedMotion()` a `true` devuelve
    `{ initial: false }` (Framer Motion monta directamente en el estado de reposo, sin animar).
  - `GlassField`: reimplementación local del patrón accesible de `ui/Field.tsx` (`useId`, label
    `htmlFor`/`id`, `aria-invalid`, `aria-describedby` → id del error, `role="alert"`) con las
    clases de vidrio esmerilado propias — no se reutilizó `TextField`/`Button` de
    `components/ui` a propósito (ver «Decisiones»).
  - Estructura: `<section aria-labelledby="hero-title">` → capas de fondo (`.glow`/`.scrim`/
    `.grain`, `aria-hidden`) → barra superior (`motion.div`: marca «Forja» + enlace fantasma
    «Crear una cuenta» a `/onboarding`) → hero (`motion.p` insignia, `<h1 id="hero-title">` con
    las dos líneas enmascaradas y la palabra de acento, `motion.p` bajada, `<h2>` oculto con
    `auth.loginTitle` — ver «Decisiones» —, `motion.form` con los dos `GlassField` y el botón
    primario, `motion.p` enlace secundario) → `<footer>` con las tres estadísticas.
- `frontend/src/features/auth/LoginScreen.module.css` **(nuevo)** — todo el CSS de esta pantalla
  (fondo, rejilla, vidrio esmerilado, botón con barrido de brillo, tipografía, media queries).
  Solo variables de `tokens.css`; ningún hex nuevo. Detalle en «Decisiones».
- `frontend/src/features/auth/strings.ts` — añadido `auth.landing.{badge,headlineRest,
  headlineLine2,lede,stat1,stat2,stat3}` en `es` y `en` (claves nuevas; ninguna existente se ha
  tocado ni renombrado). Copy exacto más abajo.
- `frontend/src/components/icons.tsx` (**solo aditivo**) — `IconEmber` (brasa/ember para la
  insignia) e `IconServer` (servidor, para la estadística de privacidad); mismo estilo que el
  resto del fichero (24×24, trazo 1.8, `currentColor`, `aria-hidden`). Ningún icono existente se
  ha modificado.
- `frontend/tests/features/loginLanding.test.tsx` **(nuevo)** — contenido de la landing (insignia,
  titular con el acento, bajada, tres estadísticas), la rama de `prefers-reduced-motion` de
  `reveal()` (sin la cual `LoginScreen.tsx` se quedaba en 95.45 % de ramas), que los dos enlaces
  «Crear una cuenta» (barra superior y secundario) apuntan a `/onboarding`, y que los campos
  siguen siendo accesibles por su etiqueta. La lógica de envío (errores por estado, redirección)
  ya estaba cubierta en `tests/features/auth.test.tsx`, que **no ha necesitado ningún cambio**
  (sigue pasando tal cual contra la pantalla nueva — ver «Decisiones»).
- `docs/screenshots/f5/login/` **(nuevo)** — capturas de autocrítica (Playwright, ver «Cómo
  verificar»): `login-1920x1080.png`, `login-1440x900.png`, `login-1280x720.png`,
  `login-390x844.png`, `login-1440x900-mid-animation.png`, `login-1024-skiplink-focus.png`.
- `docs/TASKS.md` — fila `F5-FE-01` añadida a la Fase 4 · Cierre.

## Decisiones
- **No se reutilizan `Button`/`TextField` de `components/ui`.** El encargo pedía un tratamiento
  muy específico (vidrio esmerilado con `backdrop-filter`, veta superior, barrido de brillo en
  `::after`, halo cálido) que no existe en esos componentes y que habría exigido sobrescribir por
  fuera casi todas sus reglas — con el riesgo añadido de que otro agente está rediseñando
  `components/ui/*` en paralelo, así que depender de los nombres de clase internos de su CSS
  module (en vez de solo de sus props públicas) podía romperse en silencio. `GlassField` replica
  exactamente el cableado accesible de `Field.tsx` y el `<button type="submit">` es manual; toda
  la superficie pública de `components/ui` queda sin tocar.
- **`auth.loginTitle` («Iniciar sesión») no ha desaparecido: es ahora un `<h2>` visualmente
  oculto** justo antes del `<form>`, y el titular grande y animado (`Forja tu rutina / con datos,
  no con suposiciones.`) pasa a ser el `<h1>` (con `aria-labelledby` del `<section>` apuntando a
  él, más correcto ahora que esta pantalla es también la landing). `getByRole("heading", {name})`
  de Testing Library encuentra un heading por su nombre accesible sin importar el nivel ni si está
  oculto por CSS (un `clip:rect(0 0 0 0)` de 1×1 no es `display:none`), así que
  `tests/features/auth.test.tsx` sigue en verde sin tocarlo — se decidió así explícitamente para
  minimizar el radio de cambio en un test que también cubre `AuthGate`/redirecciones.
- **Rejilla de tres filas con las capas de fondo como *grid items* explícitos, no
  `position:absolute`.** `RootLayout.module.css` (`.main`, fuera de mi zona) da a esta ruta un
  padding pensado para cuando `AppNav` está montado — pero `AppNav` nunca se monta en `/login`
  (`isPublicPath`). Sin corregirlo, la pantalla no podría ocupar un único viewport sin scroll. La
  corrección vive entera en `LoginScreen.module.css`, con los mismos tokens que usa esa regla
  (`margin-left` cancela el hueco reservado para el rail de escritorio a partir de 1024px;
  `min-height: calc(100dvh - <padding de `.main` en ese punto de corte>)` sustituye a un
  `100dvh` literal, que se habría desbordado). El primer intento de las capas de fondo
  (`.glow`/`.scrim`/`.grain`) usaba `position:absolute` — se cambió a `grid-row:1/-1` +
  `grid-column:1` como *grid items* normales (`position:static`) por dos razones: (a) así ni el
  fondo ni la barra superior (donde vive la marca «Forja», justo en la esquina donde aparece el
  enlace «saltar al contenido» de `RootLayout` al enfocarlo) pueden llegar a pintarse por encima
  de ese enlace — `position:static` se pinta siempre por detrás de cualquier elemento posicionado,
  así que el enlace nunca queda tapado sin necesidad de tocar su z-index (verificado con capturas,
  ver «Cómo verificar»); (b) evita depender de `opacity`/`filter`/`transform` a nivel de elemento
  en el fondo, que crean su propio contexto de apilamiento — el resplandor usa
  `color-mix(in srgb, var(--color-accent) …%, transparent)` en los propios *stops* del degradado
  (no `opacity` del contenedor) y la deriva se anima con `background-position` en vez de
  `transform`, precisamente para no reabrir ese problema. **Este mismo cambio de `position` a
  `grid-column` explícito arregló también un bug real**: sin `grid-column:1` en `.topbar`/
  `.heroMid`/`.stats`, la rejilla creaba una segunda columna implícita para evitar solaparlos con
  las capas de fondo (que sí tenían `grid-column:1` explícito) y todo el contenido visible quedaba
  apretado en una columna de ~130 px de ancho — se detectó con una captura a 1920×1080 antes de
  llegar a comprobar el fondo, y se confirmó con `getBoundingClientRect()`/`gridTemplateColumns`
  por Playwright antes de corregirlo.
- **Corte adicional por altura de viewport (`max-height`), no solo por anchura.** La primera
  versión solo tenía en cuenta el ancho (≥901px / ≥1024px) para «sin scroll»; a 1280×720 (uno de
  los tamaños pedidos explícitamente para probar esto) el contenido a tamaño normal necesitaba
  ≈870px y el botón, el enlace secundario y las tres estadísticas quedaban fuera del viewport sin
  forma de hacer scroll. Se añadió una media query de `max-height` que compacta espaciados y
  reduce el titular (nunca `--tap-target-min`, que es de accesibilidad) — con **dos cortes
  distintos** porque `.main` reserva un padding vertical distinto a cada lado de 1024px (112px
  entre 901–1023px de ancho, solo 48px desde 1024px): un único corte habría sido demasiado
  agresivo para 1440×900 (que no lo necesita) o insuficiente para el rango 901–1023px. Verificado
  con `document.documentElement.scrollHeight` por Playwright en más de diez combinaciones
  ancho×alto alrededor de ambos cortes (ver «Cómo verificar»); el único caso que sigue
  desbordando por poco (14px) es 901×700 — más estrecho y más bajo a la vez que cualquiera de los
  tamaños pedidos — documentado en «Riesgos».
- **`color-mix()` en vez de duplicar hex.** El fondo, el borde de la insignia, el vidrio de los
  campos y el barrido del botón necesitan versiones de baja opacidad de tokens existentes
  (`--color-accent`, `--color-text`, blanco). En vez de hardcodear `rgba(255,106,43,0.2)` (que
  MASTER_PROMPT prohibiría cambiar sin más si `--color-accent` cambiara alguna vez), se usa
  `color-mix(in srgb, var(--token) X%, transparent)` en cada sitio — sigue derivando del token en
  tiempo real. Es distinto del caso de `RestRing.tsx` (f4), donde los valores literales eran
  obligatorios porque Framer Motion interpola *color* en JS y no puede leer una custom property;
  aquí todo es CSS puro, así que no hace falta esa excepción.
- **Grano: SVG `feTurbulence` en un data URI, alfa en la propia matriz de color del filtro.** Así
  la opacidad baja del ruido no depende de `opacity` del elemento (mismo motivo que el punto
  anterior sobre contextos de apilamiento) y no hay ningún binario nuevo en el repo.
- **Fuente itálica importada en el CSS module de esta pantalla, no en `global.css`.** `global.css`
  es de otro agente (regla del encargo). El paquete autoalojado `@fontsource-variable/archivo`
  **sí** trae un eje itálico completo (`standard-italic.css`, con las mismas familias/ejes que la
  variante normal ya cargada) — se confirmó mirando `node_modules` antes de decidir usarlo, tal y
  como pedía el encargo. Al ser la única pantalla que necesita itálica, el `@import` vive en
  `LoginScreen.module.css`, dentro del chunk perezoso de esta ruta — no pesa nada en el bundle
  inicial y el navegador solo descarga el `.woff2` (~100 KB, ninguno de los tres subconjuntos)
  cuando de verdad hay texto en itálica que pintar.

## Copy exacto (es)
- Insignia: «Entrenamiento autoalojado»
- Titular: «**Forja** tu rutina» / «con datos, no con suposiciones.» (con «Forja» en itálica +
  degradado brasa — es a la vez la marca y el imperativo de «forjar»)
- Bajada: «Genera tu rutina con un motor determinista, entrena con el reproductor sin conexión y
  sigue tu progreso semana a semana.»
- Estadísticas: «1.324 ejercicios con GIF de demostración» · «Tus datos no salen de tu servidor» ·
  «Rutinas generadas sin IA generativa» (las tres verificadas contra `README.md`/`MASTER_PROMPT.md`
  §3, §7 y §10.1 antes de escribirlas — cifra de ejercicios, motor determinista propio y
  despliegue autoalojado sin CDN)
- Botón / enlaces: «Entrar» (sin cambios), «Crear una cuenta» (sin cambios, reutilizada tal cual
  en la barra superior y bajo el formulario), «¿Aún no tienes cuenta?» (sin cambios)

## Cómo verificar
```bash
cd frontend
npx tsc --noEmit -p tsconfig.json && npx tsc --noEmit -p tsconfig.node.json  # limpio
npm run lint                                                                 # 0 avisos
npm run test -- --run                                                        # 205/205, ramas 85.12 %
npm run build                                                                # index-*.js: 189.33 kB gzip
```
Visual (Playwright, `VITE_USE_MSW` **desactivado** para poder simular «sin sesión»: el mock por
defecto de `/auth/me` autentica, y `page.route()` no intercepta de forma fiable una petición que
ya captura el Service Worker de MSW — mejor sin MSW en el navegador y con `page.route()` sirviendo
un 401 directamente):
```bash
cd frontend
npx vite --host 127.0.0.1 --port 5175   # sin VITE_USE_MSW
# en otra sesión: un script Playwright que intercepta GET /api/v1/auth/me → 401 y navega a /login
```
- Capturas en `docs/screenshots/f5/login/`: 1920×1080, 1440×900 y 1280×720 (viewport único, sin
  scroll, hero anclado abajo-centro); 390×844 (apilado natural, con scroll permitido); una
  captura a 1440×900 tomada ~0.5s tras la navegación para revisar la coreografía de entrada
  (**con matiz**: en Chromium headless sin compositor visible, `requestAnimationFrame` puede no
  dispararse a tiempo real y Framer Motion —que no usa la Web Animations API nativa aquí, se
  comprobó con `document.getAnimations()`— renderiza directamente el estado final la primera vez
  que sí pinta; la captura muestra la pantalla ya asentada en vez de una interpolación a medias,
  así que no es prueba visual de la coreografía — sí lo es la lectura del código y
  `LoginScreen.tsx`/`.module.css`, y los `delay`/`duration` están para quien quiera comprobarlos
  en un navegador real con la pestaña visible); y una captura a 1024px de ancho con el enlace
  «Saltar al contenido» enfocado por teclado, que confirma que sigue visible por encima de la
  pantalla (ver «Decisiones» sobre por qué se evitó `position`/`opacity`/`filter`/`transform` en
  las capas de fondo).
- Con `prefers-reduced-motion: reduce`: todo debe aparecer ya en su posición final, sin ningún
  desplazamiento ni máscara (cubierto por `tests/features/loginLanding.test.tsx`).
- Tema claro (`data-theme="light"`): no se ha capturado por separado; todos los colores nuevos
  vienen de tokens que ya cambian con el tema salvo `--color-accent`/`--color-accent-2` (no se
  redefinen en claro, igual que en el resto de la app — p. ej. `.active` de `AppNav`), así que el
  acento del titular y el icono de la insignia mantienen el mismo naranja sobre hueso.

## Métricas
- `npm run build`: `index-*.js` (bundle inicial) → 583.79 kB sin comprimir / **189.33 kB gzip**.
  Presupuesto vigente `< 500 KB gzip` (ADR 0013 / MASTER_PROMPT §10.5, commit `a5337fb` en
  `main`, no fusionado aquí): **310 KB de margen**. Contra el presupuesto anterior de 200 KB que
  regía en `f4-motion-nav.md` (188.85 kB gzip, ~11 KB de margen) el aumento es de solo **+0.48 KB
  gzip** — `LoginScreen` no pesa casi nada en el chunk principal porque ya era una
  `lazyRouteComponent` antes de esta tarea (`router.tsx`, sin tocar); la subida viene de los dos
  iconos nuevos en `icons.tsx`, que sí es un módulo cargado por `AppNav` de forma eager.
  `LoginScreen-*.js` (chunk propio, perezoso): 4.64 kB / **1.74 kB gzip**.
  `LoginScreen-*.css` (chunk propio, perezoso): 8.59 kB / **2.56 kB gzip**.
  Las fuentes itálicas nuevas (~100 KB de `.woff2` en tres subconjuntos) no cuentan para este
  presupuesto (no son JS) y solo se descargan al visitar `/login`.
- `npm run test -- --run`: **205/205** tests en verde, 29/29 ficheros (201 anteriores + 4 nuevos
  en `loginLanding.test.tsx`; `auth.test.tsx` no se ha tocado).
- Cobertura de ramas global: **85.12 %** (por encima del umbral del 85 %; subió desde el 85.06 %
  de `f4-motion-nav.md` — el margen global sigue siendo estrecho, no es algo que esta tarea haya
  empeorado). `LoginScreen.tsx` queda sin líneas/ramas sin cubrir (comprobado en el reporte
  `text` de v8: no aparece como fila con huecos); `src/features/auth` en conjunto pasa de 98.03 %
  a **100 %** de ramas.
- Lighthouse: no se ha ejecutado en este agente (no está en la lista de verificación obligatoria
  del encargo, y requeriría el pipeline de LHCI de `f3-qa-tests.md`/`docs/adr/0010-*`); el diseño
  evita a propósito lo que más suele penalizar LCP/CLS en una pantalla así — nada de imagen/vídeo
  de fondo, ninguna fuente nueva bloquea el primer pintado (itálica con `font-display: swap`,
  igual que ADR 0007), sin layout shift por fuentes (mismo alto de línea aproximado que la
  variante normal ya cargada).

## Riesgos/pendientes
- **901×700 (ancho mínimo de «escritorio» + más bajo que cualquier tamaño pedido) sigue
  desbordando 14px verticales.** Los tamaños que sí pedía la tarea (1280×720 incluido) están
  verificados sin scroll; este caso extremo (más estrecho que 901 y más bajo que 720 a la vez) no
  se ha perseguido más para no comprimir de más el caso que sí importa (1280×720, que ya queda
  ajustado pero legible). Si algún dispositivo real cae en ese hueco, la vía más directa es bajar
  un poco más el `font-size` del titular en la media query de `max-height` de
  `LoginScreen.module.css`.
- **La captura «a mitad de animación» no demuestra la coreografía** por el motivo técnico
  explicado en «Cómo verificar» (headless sin compositor visible). Si se necesita evidencia real
  del `delay`/`duration` de cada elemento, hace falta un navegador con pestaña visible (o grabar
  vídeo) — el código y `tests/features/loginLanding.test.tsx` (rama de movimiento reducido) son
  la verificación disponible aquí.
- **No se ha capturado el tema claro.** Ningún test ni captura fija el aspecto en
  `data-theme="light"`; por construcción (todo vía tokens salvo el acento, ver «Cómo verificar»)
  debería verse coherente, pero no se ha comprobado visualmente.
- **`auth.landing.*` no tiene test de paridad `es`/`en` automático** — no existe ese test en el
  repo pese al comentario de `i18nB.ts` que lo menciona (se comprobó: no hay
  `tests/features/i18nB.test.ts`). Las claves nuevas están completas en ambos idiomas a mano; si
  se añade ese test en el futuro, `auth.landing.*` ya está listo.

## Peticiones a otros agentes
Ninguna petición bloqueante.
- El agente que rediseña `components/ui/*` en paralelo no necesita coordinar nada con esta
  pantalla: `LoginScreen.tsx` ya no importa `Button`/`TextField` (ver «Decisiones»), así que un
  cambio en `ui.module.css` no puede romper `/login`.
- Si el equipo de contenido/QA revisa el copy nuevo (`auth.landing.*` en `strings.ts`) y quiere
  ajustar el tono, son 8 claves `es`/`en` en un único bloque, fáciles de tocar sin afectar a la
  lógica.

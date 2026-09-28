# Handoff — Fase 5 · frontend-ui (f5/login-polish)

## Resumen
El orquestador revisó `docs/screenshots/f5/login/login-1440x900.png`, `login-390x844.png` y
`login-1280x720.png` (capturas de `f5-login-landing.md`) y encontró cuatro defectos en la landing
de acceso (`LoginScreen.tsx`, única pantalla «momento cero» de esta app autoalojada). Los cuatro
quedan corregidos:

1. **Cortes rectos en el resplandor de fondo.** `.glow` pintaba un `radial-gradient(circle, …)`
   sin sizing explícito (por tanto `farthest-corner`) dentro de un `background-size` **menor**
   que su propio contenedor (62%/58%). En una caja no cuadrada y descentrada eso deja alfa > 0 en
   algunas esquinas antes de llegar al borde de ese *tile*; justo donde el *tile* termina
   (`background-repeat: no-repeat`) se veía un corte recto — y, al ser un porcentaje fijo, el
   punto exacto donde ocurre depende de la proporción del viewport, así que aparecía en sitios
   distintos según el tamaño. Solución: las tres capas de fondo (`.glow`/`.scrim`/`.grain`) pasan
   a `position: fixed; inset: 0` (cubren el viewport completo, no la caja de `.hero`) y el
   resplandor usa un `background-size` **mayor** que el propio viewport (180%/168%) — así, en
   cualquier punto de la deriva (`background-position`), la imagen sobresale del viewport por los
   cuatro lados y el borde de su propio degradado queda siempre fuera de la pantalla, sea cual sea
   el tamaño o la proporción del viewport (no depende de una cifra ajustada a un solo tamaño).
2. **La landing quedaba encajonada.** Se renderizaba dentro de `.main` (`RootLayout.module.css`):
   padding + `max-width: 72rem` pensados para convivir con `AppNav`, que `/login` nunca monta. El
   agente anterior lo sabía (lo documentó en `f5-login-landing.md`) pero no podía tocar
   `RootLayout` (fuera de su zona); compensaba con hacks en `LoginScreen.module.css` (`margin-left`
   negativo + `min-height: calc(100dvh - …)` con dos cortes distintos a cada lado de 1024px). Esta
   tarea sí puede tocar `RootLayout`: ahora es consciente de la ruta (`isFullBleedPath`) y `/login`
   recibe un contenedor sin padding/ancho máximo — los hacks de compensación en `LoginScreen`
   desaparecen porque ya no hay nada que cancelar.
3. **«Entrar» parecía muerto al llegar.** `disabled={busy || email === "" || password === ""}` +
   `.submit:disabled { opacity: 0.55 }` apagaban el degradado brasa del CTA principal de la
   landing nada más cargar (campos siempre vacíos en la primera visita). Ahora el botón solo se
   deshabilita mientras `busy` (el `required` nativo de los campos + los mensajes de error ya
   existentes cubren el envío con campos vacíos, como pedía el encargo) y, mientras se envía,
   cambia de texto (`auth.submitting`, «Entrando…»/«Signing in…», ya existía en `strings.ts`) en
   vez de atenuar el degradado — el estado deshabilitado pasa a una superficie plana neutra
   (`--color-surface-2` + texto apagado, sin degradado ni `opacity`).
4. **«Crear una cuenta» aparecía dos veces en el mismo viewport.** Enlace fantasma en la barra
   superior + enlace bajo el formulario. Se retira el de la barra superior (que ahora solo lleva
   la marca «Forja») y se mantiene el inline — ver «Decisiones» por qué.

## Ficheros tocados
- `frontend/src/features/auth/LoginScreen.tsx` — quita el `<Link>` «Crear una cuenta» de
  `.topbar` (solo queda el `<p className={styles.wordmark}>`); `disabled={busy}` en el botón de
  envío (antes `busy || email === "" || password === ""}`). Ningún otro cambio de JSX.
- `frontend/src/features/auth/LoginScreen.module.css` — reescrito el bloque de fondo (`.hero`,
  `.glow`/`.scrim`/`.grain`, ver «Decisiones»); `.topbar` sin `justify-content: space-between`/
  `gap` (un único hijo); `.ghostLink`/`.ghostLink:hover` eliminadas (ya no se usan);
  `.submit:disabled` reescrita (superficie plana, sin `opacity`); la media query de escritorio
  con poca altura pasa de dos cortes (901–1023px / ≥1024px) a uno solo (`min-width: 901px` +
  `max-height: 780px`), ya innecesaria la asimetría porque `.main` ya no aporta padding a esta
  ruta. El `@import` de la itálica y el resto de la pantalla (insignia, titular, campos,
  estadísticas) no se han tocado.
- `frontend/src/features/auth/session.ts` — añadido `FULL_BLEED_PATHS`/`isFullBleedPath`, mismo
  patrón que `PUBLIC_PATHS`/`isPublicPath` ya existentes.
- `frontend/src/routes/RootLayout.tsx` — `<main>` usa `styles.fullBleed` en vez de `styles.main`
  cuando `isFullBleedPath(pathname)`; import de `isFullBleedPath` añadido. Resto sin cambios.
- `frontend/src/routes/RootLayout.module.css` — nueva regla `.fullBleed` (`padding: 0; max-width:
  none; margin-inline: 0`). `.main` no se toca (ninguna pantalla autenticada cambia).
- `frontend/tests/routes/RootLayout.test.tsx` — nueva ruta `/login` en `buildRouter`; nuevo test
  que confirma que `/login` usa `styles.fullBleed` (y no `styles.main`) y no monta `<AppNav>`;
  assertion añadida al test existente de `/` confirmando que sigue usando `styles.main`.
- `frontend/tests/features/loginLanding.test.tsx` — el test que exigía **dos** enlaces «Crear una
  cuenta» ahora exige **uno solo** (el inline, con `href="/onboarding"`); nuevo test que confirma
  que «Entrar» no está deshabilitado con los campos vacíos.
- `docs/screenshots/f5/login/` — las cinco capturas sustituidas (mismo nombre de fichero:
  `login-1920x1080.png`, `login-1440x900.png`, `login-1280x720.png`, `login-390x844.png`,
  `login-1024-skiplink-focus.png`); `login-1440x900-mid-animation.png` eliminada (ya documentada
  como no probatoria en `f5-login-landing.md` — Chromium headless sin compositor visible renderiza
  el estado final, no una interpolación a medias).
- `docs/TASKS.md` — fila `F5-FE-03` añadida en Fase 4 · Cierre, a continuación de `F5-FE-01`.
- `docs/handoffs/f5-login-polish.md` — este documento.

No se ha tocado `frontend/src/features/today/`, `frontend/src/features/shared/ui.module.css` ni
`frontend/src/components/ui/ui.module.css` (zona del agente en paralelo). No se ha añadido ninguna
dependencia npm ni ningún hex nuevo en `tokens.css` (se sigue usando solo `color-mix()` sobre
tokens existentes, igual que en `f5-login-landing.md`).

## Decisiones
- **Capas de fondo a `position: fixed` con `background-size` mayor que el viewport, en vez de
  ajustar el porcentaje de `transparent NN%` dentro de la caja pequeña.** Se consideró primero
  solo bajar el *stop* del degradado (de `68%` a algo más conservador) manteniendo el `.glow`
  acotado a la caja de `.hero`. Se descartó: la caja no es cuadrada y su proporción cambia con
  cada viewport pedido (1920×1080, 1440×900, 1280×720, 390×844); un *stop* que deja alfa 0 en las
  cuatro esquinas de una caja ancha (escritorio) puede no bastar para una caja estrecha y alta
  (móvil), y el borde real de un `radial-gradient(circle, …)` no es solo las cuatro esquinas sino
  todo el perímetro (el punto más cercano de un lado al centro puede estar más cerca que ambas
  esquinas de ese lado). Ajustar un porcentaje fijo para que funcione en las cuatro proporciones
  pedidas a la vez es fràgil y exactamente el tipo de ajuste que ya había fallado una vez. La
  solución elegida es independiente de la proporción del viewport por construcción: con
  `background-size` mayor que el 100% en ambos ejes (180%/168%) y el `background-position` de la
  deriva siempre alejado de los extremos 0%/100% (14–21% y 80–88%, igual que antes), la imagen
  sobresale del viewport por los cuatro lados en todo el rango de la animación — el borde del
  propio degradado (donde antes se veía el corte) queda siempre fuera de la pantalla, sin
  necesidad de calcular el *stop* exacto para cada proporción. Verificado visualmente en las
  cuatro capturas pedidas (1920×1080, 1440×900, 1280×720, 390×844): sin ningún corte recto.
  `.scrim` y `.grain` pasan al mismo esquema (`position: fixed; inset: 0`) por consistencia — no
  tenían el problema del *tile* (`.scrim` ya pintaba a tamaño completo del contenedor; `.grain` es
  un patrón repetido, sin borde propio) pero mezclar un esquema de posicionamiento por capa habría
  sido más confuso que ganancia.
- **`z-index` explícito y bajo en vez de depender del orden de pintado.** El agente anterior evitó
  `position`/`opacity`/`filter`/`transform` en las capas de fondo precisamente para que
  `position: static` las mantuviera detrás de cualquier elemento posicionado (el enlace «saltar al
  contenido» de `RootLayout`, z-index 100 en `global.css`) sin tener que gestionar z-index. El
  encargo de esta tarea autoriza explícitamente `position: fixed`/`absolute` con z-index bajo y
  explícito, así que se usa ese camino: `.glow`/`.scrim`/`.grain` → `z-index: 0`; `.topbar`/
  `.heroMid`/`.stats` (contenido) ya tenían `z-index: 1` de la versión anterior (no ha hecho falta
  subirlo). Verificado con una captura de teclado (`login-1024-skiplink-focus.png`): el enlace
  sigue perfectamente visible y por encima de las capas de fondo tras enfocarlo con Tab.
- **`RootLayout` consciente de la ruta (`isFullBleedPath`) en vez de seguir compensando desde
  `LoginScreen.module.css`.** Ahora que `RootLayout.tsx`/`.module.css` están dentro de la zona de
  esta tarea, la corrección correcta es que el shell no le dé a `/login` un padding que de todas
  formas no necesita (en vez de que `/login` cancele ese padding con matemática de `margin-left`
  negativo atada a los mismos *breakpoints* que `.main`, que era lo único posible en la tarea
  anterior). Con `.fullBleed` (`padding: 0; max-width: none; margin-inline: 0`) aplicado por
  `RootLayout` cuando `isFullBleedPath(pathname)`, `.hero` en `LoginScreen.module.css` vuelve a
  ser un simple `min-height: 100dvh` sin ningún cálculo — los hacks de la tarea anterior
  desaparecen porque ya no hay nada que cancelar.
- **`/onboarding` se queda con `.main` (no entra en `isFullBleedPath`).** El encargo decía
  «`/onboarding` solo si queda bien». Se miró `OnboardingScreen.tsx`/`Onboarding.module.css`: es
  un asistente de formulario de 4 pasos con `.root { max-width: 40rem; margin: 0 auto; }` que
  reutiliza `Button`/`TextField`/`Chip`/`ChoiceCard` de `components/ui` — depende del padding de
  `.main` para su respiro (arriba, a los lados y para el rail de escritorio); no es un hero de un
  único viewport como `/login`. Quitarle ese padding dejaría el contenido pegado a los bordes del
  viewport sin ganar nada (no es una pantalla de «un solo golpe de vista» como la landing). Por
  eso `FULL_BLEED_PATHS = ["/login"]` (subconjunto de `PUBLIC_PATHS`, que sigue incluyendo
  `/onboarding` para `AppNav`/`AuthGate`) y `.main` no cambia en absoluto.
- **Único disparador de `:disabled` = `busy`; sin nuevo copy.** `auth.submitting` («Entrando…»/
  «Signing in…») ya existía en `strings.ts` y ya estaba cableado en el JSX
  (`{busy ? t("auth.submitting") : t("auth.submit")}`) desde `f5-login-landing.md` — no hacía
  falta ninguna clave nueva, solo quitar la condición de campos vacíos del `disabled` y reescribir
  `.submit:disabled` (superficie plana `--color-surface-2` + `--color-text-muted`, sin `opacity`
  ni degradado, `cursor: progress`). El formulario ya tiene `required` nativo en ambos campos
  (`GlassField`) y el `submit` del navegador no dispara con campos vacíos/no válidos antes de que
  `onSubmit` (y por tanto `submit()`) se ejecute — `event.preventDefault()` dentro del handler solo
  evita la navegación por defecto, no salta la validación nativa, que ocurre antes de que el
  evento `submit` llegue a dispararse. El envío con campos vacíos sigue, por tanto, sin poder
  llegar nunca a `POST /auth/login`.
- **Se mantiene el enlace inline, se retira el de la barra superior.** El inline
  («¿Aún no tienes cuenta? Crear una cuenta», bajo el formulario) es el que responde al momento
  exacto en que alguien se hace esa pregunta — después de ver el formulario, no antes — sin que la
  mirada tenga que saltar a la esquina superior. Con él fuera, la barra superior queda solo con la
  marca «Forja», más silenciosa (un único acento deliberado, coherente con el principio ya fijado
  en `f5-login-landing.md` de que esta pantalla tiene «un único momento de entrada»). Se ha
  simplificado `.topbar` en consecuencia (sin `justify-content: space-between`/`gap`, que solo
  tenían sentido con dos hijos) y se ha borrado `.ghostLink`/`.ghostLink:hover` (CSS muerto).
- **Corte único en la media query de poca altura, retunado a `max-height: 780px`.** La versión
  anterior tenía dos cortes (`920px` entre 901–1023px de ancho, `860px` desde 1024px) porque
  `.main` reservaba un padding vertical distinto a cada lado de esa frontera (112px / 48px). Esa
  asimetría ya no existe para esta ruta (padding 0 a cualquier ancho), así que un único corte
  basta; el número (`780px`) se ha verificado con las propias capturas pedidas: a 1280×720 se
  compacta y cabe sin *scroll* (visible en `login-1280x720.png`), a 1440×900 no se compacta y se
  ve idéntica a antes. No se ha repetido el barrido de más de diez combinaciones ancho×alto que
  hizo el agente anterior — ver «Riesgos».
- **Metodología de capturas: `VITE_USE_MSW=1` (pedido por el encargo) + contexto de Playwright con
  `serviceWorkers: "block"` para `/login`.** El mock por defecto de `GET /auth/me`
  (`src/mocks/handlers.generated.ts`) autentica (usuaria «Lucía», `onboarding_completed: true`).
  `AuthGate` renderiza `LoginScreen` de inmediato para cualquier ruta pública (antes de que la
  sesión resuelva), pero en cuanto `GET /auth/me` resuelve con éxito, `redirectTarget("/login",
  sesiónOk)` devuelve `"/"` y un `useEffect` dispara la navegación — con MSW activo de verdad
  habría una carrera contra ese redirect. En vez de repetir la solución de `f5-login-landing.md`
  (`VITE_USE_MSW` desactivado del todo + `page.route()` sirviendo un 401), que ya no encajaba con
  el `VITE_USE_MSW=1` explícito de este encargo, se ha abierto el contexto de Playwright para
  `/login` con `serviceWorkers: "block"`: sin el *service worker* de MSW, `GET /auth/me` llega de
  verdad al proxy de Vite hacia un backend que no existe en este entorno, falla con un error
  genérico (no `UnauthenticatedError`) y `redirectTarget` devuelve `null` para cualquier error en
  una ruta pública — `AuthGate` nunca redirige y `/login` se queda quieta para la captura, sin
  ninguna carrera. La captura de «Hoy» (prueba de que el shell autenticado no cambia) se ha hecho
  en un contexto Playwright normal (sin bloquear *service workers*), donde MSW sí responde con
  datos realistas. El servidor sigue arrancando con `VITE_USE_MSW=1` en ambos casos, tal y como
  pedía el encargo — lo que cambia es si el *navegador* (el contexto de Playwright) deja que su
  *service worker* se registre, no la variable de entorno del servidor.
- **La captura de «Hoy» no se ha versionado.** El encargo pide tomarla y mirarla («para probar que
  el shell autenticado no cambia»), pero solo pide sustituir el contenido de
  `docs/screenshots/f5/login/` con las capturas de login — «Hoy» no es una captura de login. Se ha
  usado como verificación (revisada con la herramienta `Read`, ver más abajo) y luego descartada
  junto con el resto de ficheros temporales, en vez de añadir un fichero nuevo a un directorio que
  el encargo no menciona.

## Cómo verificar
```bash
cd frontend
npm ci                                    # este worktree no traía node_modules
./node_modules/.bin/tsc --noEmit -p tsconfig.json
./node_modules/.bin/tsc --noEmit -p tsconfig.node.json   # ambos limpios
./node_modules/.bin/eslint . --max-warnings 0            # 0 avisos
./node_modules/.bin/vitest run --coverage                # 210/210, ramas 85.27 %
npm run build                                             # index-*.js: 189.92 kB gzip
```
Visual (Playwright, `VITE_USE_MSW=1`, ver «Decisiones» sobre el contexto sin *service worker*
para `/login`):
```bash
cd frontend
VITE_USE_MSW=1 ./node_modules/.bin/vite --host 127.0.0.1 --port 5177
# en otra sesión: script Playwright (borrado tras usarlo, ver «Ficheros tocados») que abre
# 127.0.0.1:5177/login en un contexto con serviceWorkers:"block" a 1920×1080/1440×900/1280×720/
# 390×844 (~2.7s de espera tras el <h1> para que la coreografía de Framer Motion se asiente del
# todo, evitando repetir la captura "a mitad de animación" ya descartada) + una quinta a 1024×800
# con Tab pulsado para el foco del skip-link; y 127.0.0.1:5177/ en un contexto normal a 1440×900.
```
Las cinco capturas de `/login` se revisaron con la herramienta `Read` (zoom mental en los bordes
del resplandor en las cuatro esquinas y en el punto medio de cada lado): ningún corte recto en
ningún tamaño. `login-1024-skiplink-focus.png` confirma el enlace «Saltar al contenido» visible y
por encima del fondo tras Tab. La captura de «Hoy» a 1440×900 confirma nav lateral + tarjetas con
el padding/ancho habituales del shell, sin ningún cambio visible.

## Métricas
- `npm run build`: `index-*.js` (chunk principal, eager) → 586.20 kB sin comprimir / **189.92 kB
  gzip** (antes 189.33 kB gzip en `f5-login-landing.md`; +0.59 kB gzip — `isFullBleedPath` en
  `session.ts` y la nueva rama en `RootLayout.tsx` son eager, `LoginScreen` sigue sin serlo).
  Presupuesto `< 500 KB gzip` (ADR 0013): **310.08 KB de margen**.
  `LoginScreen-*.js` (chunk propio, perezoso): 4.50 kB / **1.71 kB gzip** (antes 4.64 kB / 1.74 kB
  — más pequeño: se ha quitado un `<Link>`).
  `LoginScreen-*.css` (chunk propio, perezoso): 7.80 kB / **2.39 kB gzip** (antes 8.59 kB / 2.56 kB
  — más pequeño: se han quitado `.ghostLink`/`.ghostLink:hover` y un corte de la media query).
- `./node_modules/.bin/vitest run --coverage`: **210/210** tests en verde, 30/30 ficheros (205
  anteriores + 5 nuevos/editados: 2 en `RootLayout.test.tsx`, 2 en `loginLanding.test.tsx` con una
  reescrita en vez de sumar, y ningún test roto en el resto de la suite).
- Cobertura de ramas global: **85.27 %** (por encima del umbral del 85 %; subió desde el 85.12 %
  de `f5-login-landing.md`).

## Riesgos/pendientes
- **El nuevo corte único de la media query de poca altura (`max-height: 780px`) se ha verificado
  solo en los tamaños que pide este encargo** (1280×720 compactado y sin *scroll*; 1440×900 sin
  compactar), no con el barrido de más de diez combinaciones ancho×alto que hizo el agente
  anterior alrededor de los dos cortes antiguos. Como esta ruta ya no lleva el padding vertical de
  `.main` (48–112px recuperados a cualquier ancho ≥ 901px), el margen solo puede haber mejorado
  respecto a antes, pero no se ha re-verificado el caso límite ya documentado en
  `f5-login-landing.md` (901×700, que desbordaba 14px) — con más margen disponible ahora, es
  probable que ya quepa, pero no se ha comprobado.
- **Tema claro (`data-theme="light"`) sigue sin capturarse**, igual que en `f5-login-landing.md` —
  no es parte de los defectos reportados por el orquestador ni de los tamaños pedidos en este
  encargo. Por construcción (todo vía tokens salvo `--color-accent`/`--color-accent-2`, que no
  cambian de tema) debería seguir viéndose coherente, pero sigue sin comprobación visual.
- **La coreografía de entrada (delays/duration de Framer Motion) no se ha tocado** y sigue sin
  poder demostrarse con una captura de Chromium headless (mismo motivo técnico que
  `f5-login-landing.md`: sin compositor visible, la primera pintura ya muestra el estado final).
  Las capturas de esta tarea se toman ~2.7s después de que aparece el `<h1>`, tiempo de sobra para
  que toda la coreografía haya terminado (última entrada a los 1.44 s + 1.05 s de duración) — es
  intencional, para evitar repetir el error de la captura «a mitad de animación» que se ha
  borrado, no una demostración de la coreografía en sí.

## Peticiones a otros agentes
Ninguna petición bloqueante.
- El agente en paralelo en `frontend/src/features/today/`, `frontend/src/features/shared/
  ui.module.css` y `frontend/src/components/ui/ui.module.css` no necesita coordinar nada: esta
  tarea no ha tocado ninguno de esos ficheros (confirmado con la captura de «Hoy», que muestra el
  shell autenticado sin cambios).
- `RootLayout.tsx`/`RootLayout.module.css` quedan con una nueva rama de comportamiento
  (`isFullBleedPath`) — cualquier agente futuro que añada una ruta pública nueva y quiera que
  también ocupe el viewport completo solo necesita añadirla a `FULL_BLEED_PATHS` en
  `features/auth/session.ts`; si en cambio necesita el padding normal del shell (como
  `/onboarding` hoy), no necesita tocar nada.

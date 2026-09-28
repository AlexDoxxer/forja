# Handoff — f5/hoy-polish · frontend-ui

## Resumen
El orquestador revisó `hoy-desktop.png`/`hoy-mobile.png` de `f5/design-system` y encontró cuatro
defectos concretos en Hoy (primera pantalla tras iniciar sesión). Los cuatro están corregidos:

1. **Estadísticas de la semana con estilo `<dl>` por defecto** («Sesiones completadas» y luego «0»
   sangrado ~40 px en la línea siguiente, por el `margin-inline-start: 40px` que el navegador aplica
   a `<dd>`). Ahora es una cuadrícula 2×2 (también en móvil): valor grande en fuente de titulares
   con números tabulares (`--nums-tabular`) y peso 700, etiqueta pequeña y atenuada encima. El
   marcado sigue siendo `<dl>`/`<dt>`/`<dd>` — solo cambió el estilo. «Último récord» dejó de ser un
   `<h3>` suelto: ahora es una línea propia, pequeña y con un filo brasa a la izquierda (etiqueta
   atenuada + «sentadilla con barra: 79,2 kg» en negrita).
2. **Botón primario deshabilitado con aspecto sucio**: «Guardar peso» con opacidad 0.55 sobre el
   degradado brasa daba una mancha parda. Ahora `.primary:disabled` (en `components/ui/ui.module.css`
   y `features/shared/ui.module.css`) es una superficie plana `--color-surface-2`, texto
   `--color-text-muted`, borde `--color-border`, sin degradado, sin resplandor, sin barrido de
   brillo, `cursor: not-allowed`. Contraste del texto verificado (ver «Decisiones»).
3. **Título duplicado**: el `<h1>` de la pantalla y el `<h2>` de la primera tarjeta decían los dos
   «Hoy». La tarjeta ahora se llama «Sesión de hoy» / «Today's session» (clave nueva
   `todayB.sessionCardTitle`).
4. **Las tres tarjetas eran indistinguibles** (mismo tamaño/radio/borde/sombra — el «kit de tarjetas
   SaaS genérico» que señala el skill de diseño). La tarjeta de sesión (CTA primaria «Empezar»/
   «Continuar», o el estado vacío «crea una rutina») es ahora la protagonista: columna más ancha en
   escritorio (`minmax(0,1fr)` vs `minmax(16rem,22rem)`, ≥1024 px; una sola columna apilada en
   móvil, la sesión siempre primero), relleno mayor (`--space-6`/`--space-5` vs `--space-4`) y un
   filo brasa de 3 px en el borde superior (`--gradient-accent`, el mismo degradado del propio botón
   «Empezar»). Resumen semanal y peso corporal quedan con relleno reducido, más discretas.

Plan de diseño cargado con el skill `frontend-design` antes de tocar código. Autocrítica relevante:
la primera versión de la tarjeta héroe combinaba el filo superior con un resplandor radial ember de
fondo (`radial-gradient` con `--glow-accent-soft`); al repasar la lista de calibración del propio
skill («gradient washes as decoration» es justo el antipatrón #4 del kit SaaS que esta tarea pedía
corregir) lo quité y dejé solo el filo — un único gesto deliberado, no dos acumulados.

## Ficheros tocados
- `frontend/src/features/today/TodayScreen.tsx` — reestructura la cuadrícula de tarjetas (héroe +
  columna secundaria con resumen semanal y peso corporal agrupados), aplica `Today.module.css` a las
  tres tarjetas, reescribe el marcado de estadísticas y de «Último récord», renombra el título de la
  tarjeta de sesión. La coreografía `Reveal` (variantes, `delay`, agrupación de etapas) no cambió.
- `frontend/src/features/today/Today.module.css` (nuevo) — `.grid`/`.secondaryStack` (layout héroe +
  columna angosta), `section.hero`/`section.secondary` (tamaño y calidez, ver «Decisiones» sobre por
  qué usan selector de etiqueta), `.statGrid`/`.stat`/`.statLabel`/`.statValue` (cuadrícula de
  estadísticas), `.lastRecord`/`.lastRecordLabel`/`.lastRecordValue` (línea de récord).
- `frontend/src/components/ui/ui.module.css` — `.primary:disabled` plano (botón base del sistema de
  diseño; no se usa directamente en Hoy, pero la tarea pedía corregirlo también aquí por
  consistencia con `features/shared`).
- `frontend/src/features/shared/ui.module.css` — mismo `.primary:disabled` para `.btn` (el que sí
  usa Hoy en «Empezar»/«Continuar»/«Guardar peso»).
- `frontend/src/features/session/strings.ts` — clave `todayB.sessionCardTitle` (es: «Sesión de hoy»,
  en: «Today's session»). Es donde ya vivía todo el espacio de nombres `todayB` (incluido
  `weekSummary`, `lastRecord`, etc.), registrado vía `registerBundle` e importado por
  `TodayScreen.tsx` — no en `i18n/resources.ts`, que solo cubre la parte A.
- `frontend/tests/design-tokens.test.ts` — añade el par `color-text-muted`/`color-surface-2` (oscuro
  y claro) a las tablas de contraste AA existentes: es el texto del botón primario deshabilitado.
- `docs/screenshots/f5/design-system/hoy-desktop.png` y `hoy-mobile.png` — recapturados.

No se tocó `frontend/src/features/auth/*` ni `frontend/src/components/icons.tsx` (otro agente
trabaja ahí en paralelo), tal como pedía la tarea.

## Decisiones
- **`section.hero` / `section.secondary` con selector de etiqueta, no solo de clase.** Ambas
  necesitan pisar `padding`/`background` de `.card` (`shared/ui.module.css`), que también se aplica
  en el mismo elemento (`className={cx(shared.card, today.hero)}`) para heredar borde/radio/sombra y,
  sobre todo, las reglas de espaciado entre hijos (`.card > * + *`, `.card h2,h3{margin-bottom:0}`)
  que las tres tarjetas siguen necesitando. Una clase de un solo nivel (`.hero`) tiene la misma
  especificidad que `.card` (0,1,0): cuál gana dependería del orden en que Vite concatene los dos
  módulos CSS en el bundle final, algo que no quise dejar al azar. Añadir el selector de etiqueta
  (`section.hero`, especificidad 0,1,1) gana de forma determinista sin tocar `shared/ui.module.css`
  ni duplicar sus reglas de espaciado.
- **Filo superior en vez de resplandor + filo.** Ver «Resumen» — un resplandor radial detrás del
  contenido de la tarjeta es literalmente el antipatrón «gradient washes as decoration» que el skill
  de diseño señala. El filo de 3 px reutiliza `--gradient-accent` tal cual (el mismo degradado del
  botón «Empezar» que la tarjeta contiene) en vez de inventar un ángulo o color nuevo.
- **Sin `border-color` cálido en la tarjeta héroe.** Consideré teñir también el borde completo con
  `color-mix(in srgb, var(--color-accent) X%, var(--color-border))` (como ya hacen `.badgeAccent` /
  `.badgeSuccess` / `.badgeError`) para reforzar el filo superior. Lo descarté: el filo ya es el gesto
  cálido deliberado de la tarjeta; teñir además todo el borde habría sido un segundo accesorio sobre
  el mismo elemento sin necesidad real.
- **Sin `height`/`align-items: stretch` forzado entre la tarjeta héroe y la columna secundaria.** En
  escritorio, la tarjeta de sesión resulta más corta que la pila resumen+peso (menos contenido) y
  termina antes verticalmente — es intencional, no un bug: forzar que el héroe estire su altura para
  igualar la columna habría significado o bien una tarjeta con mucho hueco vacío dentro (si el
  contenido no crece con ella) o volver a depender de un relleno/fondo decorativo para rellenar ese
  hueco (el mismo antipatrón que se evitó arriba). El ancho —no el alto— es lo que pide la tarea
  («spanning more of the row»), y ya es visible en las dos capturas.
- **`.primary:disabled` en ambas hojas de botones, aunque Hoy solo usa la de `features/shared`.** La
  tarea lo pedía explícitamente («both `components/ui` Button `.primary:disabled` and the shared
  `.btn.primary:disabled`») para que el arreglo de contraste/mancha parda sea consistente en todo el
  sistema de diseño, no solo donde hoy se nota. Mismo bloque de reglas en los dos ficheros
  (superficie 2 plana, texto atenuado, borde neutro, sin sombra/brillo), colocado justo después de la
  regla `:disabled` genérica existente en cada hoja para ganar por orden de aparición sin necesitar
  más especificidad (misma especificidad que `.button:disabled`/`.btn:disabled`: 0,2,0 en los dos
  casos).
- **Contraste: un único par nuevo, no una campaña de re-verificación.** El único texto/fondo
  genuinamente nuevo que introduce esta tarea es `--color-text-muted` sobre `--color-surface-2` (el
  botón deshabilitado). Lo añadí a `tests/design-tokens.test.ts`: 7.17:1 en oscuro, 5.90:1 en claro
  (ambos ≥ 4.5:1 AA texto normal, calculado con la misma fórmula del test antes de tocar código). Las
  etiquetas de la cuadrícula de estadísticas también usan `--color-text-muted`, pero sobre
  `--color-surface-1` (el fondo de la propia tarjeta) — es el mismo patrón `.muted` que ya usa el
  resto de la pantalla (p. ej. la media de 7 días en «Peso corporal») sin par de test dedicado; no
  añadí uno nuevo para no duplicar cobertura de un patrón ya extendido y no señalado por la tarea.
- **Clave i18n en `features/session/strings.ts`, no en `i18n/resources.ts`.** El namespace `todayB`
  completo (incluidas todas las cadenas que ya usaba Hoy: `weekSummary`, `lastRecord`,
  `bodyWeightSave`…) ya vivía ahí antes de esta tarea, registrado en tiempo de ejecución vía
  `registerBundle`. `sessionCardTitle` sigue ese mismo patrón por consistencia — está dentro de «los
  recursos i18n del título renombrado» que permitían los límites de escritura, aunque el fichero esté
  en la carpeta `session/`.

## Cómo verificar
```bash
cd frontend
npm ci                     # node_modules no estaba instalado en este worktree
npx tsc --noEmit            # limpio
npm run lint                 # 0 avisos
npm run test -- --run        # 206/206 en verde; cobertura de ramas 85.18 % (>= umbral 85 %)
npm run build                  # bundle principal 585.77 kB / 189.67 kB gzip (< 500 KB, ADR 0013)
```
Visualmente (capturas ya reemplazadas en `docs/screenshots/f5/design-system/hoy-desktop.png` y
`hoy-mobile.png`, tomadas contra `VITE_USE_MSW=1 npx vite --host 127.0.0.1 --port 5176` con un script
Playwright desechable, ya borrado): cuadrícula de estadísticas 2×2, «Último récord» como línea propia
con filo brasa, «Guardar peso» deshabilitado plano y atenuado (sin mancha parda), título de tarjeta
«Sesión de hoy» distinto del `<h1>` «Hoy», tarjeta de sesión más ancha/con filo superior vs. resumen
semanal y peso corporal más discretos. En móvil, la captura se toma redimensionando el viewport a la
altura real del contenido (no con `fullPage: true`): Chromium expande el viewport para las capturas
de página completa, lo que reposiciona la barra de navegación inferior (`position: fixed`) respecto a
esa altura expandida en vez de a los 390×844 reales, y queda flotando a mitad de la tarjeta de peso
corporal — con el viewport ya del tamaño exacto del contenido no hace falta expandir nada y la barra
queda anclada al pie, como en un dispositivo real.

## Métricas
- `npm run build`: `dist/assets/index-*.js` → 585.77 kB sin comprimir / **189.67 kB gzip** (límite
  500 KB gzip, ADR 0013). Solo +0.29 KB gzip sobre el punto de partida de `f5/design-system`
  (189.38 kB) — el cambio es casi todo CSS (un fichero de módulo nuevo, pequeño) y unas pocas líneas
  de JSX reordenadas, sin lógica ni dependencias nuevas.
- `npm run test -- --run`: **206/206** tests en verde, 29/29 ficheros (sin tests nuevos: los cuatro
  arreglos son de estilo/marcado sobre rutas ya cubiertas por `tests/routes/TodayRoute.test.tsx`, que
  sigue en verde sin modificar).
- Cobertura: ramas **85.18 %** (≥ 85 %, idéntica al punto de partida de `f5/design-system` — esta
  tarea no cambia ninguna rama de lógica, solo estilo/marcado), sentencias 93.34 %, funciones
  91.44 %, líneas 95.29 %.

## Riesgos/pendientes
- **`.empty` (estado «sin programa activo») dentro de la tarjeta héroe agranda el relleno vertical
  dos veces** (el propio `padding: var(--space-6) var(--space-4)` de `.empty`, más el nuevo
  `padding: var(--space-6) var(--space-5)` de `section.hero`). No se ve en las capturas actuales
  (el mock de `GET /sessions/next` usado por MSW devuelve `status: "scheduled"`, no
  `no_active_program`), así que no se ha podido verificar visualmente ese estado concreto. El
  relleno combinado no rompe nada (sigue centrado, sin desbordar), pero puede leerse como
  demasiado aire si alguien lo revisa con ese estado concreto activado a mano.
- **Ninguna prueba nueva.** Los cuatro arreglos son de estilo/marcado (clases CSS, cambio de
  etiqueta de calor/heading, reordenación de JSX) sobre comportamiento ya cubierto por
  `tests/routes/TodayRoute.test.tsx` (5 casos, todos en verde sin tocar el fichero) — no se ha
  añadido cobertura porque no hay rama de lógica nueva que cubrir, siguiendo la preferencia de
  pruebas acotadas en vez de una campaña.
- `node_modules` no estaba instalado en este worktree; se ejecutó `npm ci` antes de verificar (no
  versionado, no aparece en el diff).

## Peticiones a otros agentes
Ninguna petición bloqueante.
- El agente que rediseña `features/auth/*` en paralelo no se ve afectado: no se tocó esa carpeta ni
  `components/icons.tsx`.
- `.primary:disabled` ahora existe en `components/ui/ui.module.css` (el `Button` compartido) además
  de `features/shared/ui.module.css`; cualquier pantalla que use un `<Button variant="primary" disabled>`
  fuera de Hoy hereda automáticamente el mismo tratamiento plano sin cambios adicionales.

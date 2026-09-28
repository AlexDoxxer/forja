# Handoff — Fase 4 · frontend-ui (f4/visual-polish)

## Resumen
Pasada de pulido visual real sobre toda la app (sin cambiar rutas, contratos ni el
significado de ningún texto). El problema de partida: las pantallas «parte A» (onboarding,
generador, editor, biblioteca) ya usaban `components/ui/Button` con `variant="primary"` y el
degradado brasa correctamente, pero las pantallas «parte B» (Hoy, sesión, nutrición, perfil,
admin, rutinas) usaban casi siempre la clase plana `shared/ui.module.css` `.btn` sin
`.primary`, por lo que CTAs como «Guardar peso» o «Crear una rutina» salían grises y sin
jerarquía — exactamente lo descrito en la captura adjunta. Se auditaron los botones primarios
de cada pantalla, se añadieron iconos de línea dibujados a mano (`components/icons.tsx`), se
le dio a `AppNav` un icono por enlace y un estado activo en forma de píldora, y se dio más
respiro y una cabecera con icono a las tarjetas de `Card`-like markup repetido en varias
features. Los tokens de `styles/tokens.css` no se han tocado.

## Ficheros tocados
- `frontend/src/components/icons.tsx` **(nuevo)** — 22 iconos de línea 20×20 (`viewBox 0 0 24
  24`, trazo `currentColor`, sin dependencias, `aria-hidden` porque son decorativos).
- `frontend/src/components/AppNav.tsx` / `AppNav.module.css` — icono por enlace (Hoy, Rutinas,
  Biblioteca, Progreso, Perfil), enlaces a Nutrición/Admin que ahora aparecen condicionados a
  `useSession().diet_available` / `role === "admin"` (antes no existían en la nav en absoluto),
  y una píldora de fondo (`--color-surface-2`) en el ítem activo en vez de solo color de texto.
- `frontend/src/i18n/resources.ts` — añadidas `nav.nutrition` / `nav.admin` (es/en).
- `frontend/src/styles/global.css` — `h1` en peso 800 y `letter-spacing: -0.01em` en
  titulares, siguiendo la tipografía Archivo ya definida en tokens (§10.1).
- `frontend/src/features/shared/ui.module.css` — respiro de tarjeta (`padding` a
  `--space-5`, con `> * + * { margin-top: --space-3 }` en vez de flexbox para no romper
  layouts internos como `<dl>`/`grid` o texto en línea), `.cardHeader`/`.cardIcon` (icono +
  título), `.empty`/`.emptyIcon` (estado vacío centrado), hover en `.btn` y `.primary` en
  negrita.
- Auditoría de CTA primario + iconos de cabecera de tarjeta en:
  - `frontend/src/features/today/TodayScreen.tsx` — «Empezar»/«Continuar sesión»/«Crear una
    rutina» y «Guardar peso» ahora usan `.primary`; icono por tarjeta (calendario, barras,
    báscula); estado vacío «Aún no tienes un programa activo» con icono de bandeja + frase.
  - `frontend/src/routes/ProgramsRoute.tsx` — de HTML plano a tarjetas (`shared["card"]`) con
    icono de mancuerna, CTA «Generar una rutina nueva» primaria, estado vacío con icono.
  - `frontend/src/features/nutrition/NutritionScreen.tsx` y `ShoppingList.tsx` — CTAs
    «Activar dieta», «Generar plan» y «Guardar ajustes» primarias; icono por cabecera (diana,
    portapapeles, ajustes).
  - `frontend/src/features/profile/ProfileScreen.tsx` — «Guardar ajustes» primaria; icono por
    cabecera (ajustes, descarga, dispositivos, nube, información).
  - `frontend/src/features/admin/AdminScreen.tsx` — icono por cabecera (ajustes, personas,
    refrescar); sin CTA primaria nueva (el panel no tiene una acción «positiva» clara: activar
    ingesta real es una acción de mantenimiento, no una acción de producto).
  - `frontend/src/features/progress/ProgressScreen.tsx` — icono por cabecera (cuadrícula,
    barras, tendencia, trofeo, báscula).
  - `frontend/src/features/session/SessionSummary.tsx` — «Volver a Hoy» primaria; icono de
    trofeo en «Récords».
- `frontend/tests/components/AppNav.test.tsx` **(nuevo)** — cubre los dos enlaces
  condicionales de `AppNav` (con y sin `diet_available`/`role: admin`).

## Decisiones
- **No se creó un componente `Card` en React.** `features/shared/ui.module.css` `.card` ya
  hacía de facto ese papel en 6 features distintas; convertirlo en un componente habría
  significado tocar la firma de una decena de sitios sin ganar nada que la clase CSS + un
  par de sub-clases (`cardHeader`, `cardIcon`, `empty`, `emptyIcon`) no dieran ya. Se amplió
  esa hoja de estilos en vez de duplicar un segundo sistema de tarjetas.
- **`.card` no pasó a `display: flex; flex-direction: column; gap: ...`** como primer intento:
  varias tarjetas anidan un `<dl>` con su propio `display: grid` (resumen de sesión) o texto
  en línea que debe seguir fluyendo junto (p. ej. «Título · Dry run» en el panel de ingesta de
  Admin). Forzar flex en el contenedor habría convertido ese texto en línea en bloques
  apilados. Se usó `> * + * { margin-top: var(--space-3) }` en su lugar: da el mismo respiro
  entre bloques sin tocar el modo de caja de los hijos.
- **Los iconos son puramente decorativos** (`aria-hidden`), nunca la única fuente de
  información — el texto de cada botón/cabecera ya dice lo mismo, así que no hace falta texto
  alternativo ni tocar accesibilidad.
- **Admin no recibió una CTA primaria nueva.** A diferencia de Nutrición/Perfil, ninguna
  acción de ese panel es un «momento positivo» del usuario (activar dieta, guardar ajustes);
  son operaciones de mantenimiento (ingesta, cambiar rol). Forzar un degradado ahí habría sido
  cosmético sin sentido de producto.
- **Reemplazado el patrón `` `${shared["btn"] ?? ""} ${shared["primary"] ?? ""}` `` por
  `cx(shared["btn"], shared["primary"])`** (helper ya existente en `lib/cx.ts`, usado por
  `AppNav`). Cada `??` inline es una rama nueva de cobertura por sitio de llamada; con 10 CTAs
  nuevas marcadas como primarias esto añadía ~20 ramas no cubiertas y hacía caer el build.
  `cx()` ya está cubierto una vez en su propia definición.

## Cómo verificar
```bash
cd frontend
npm run lint        # 0 avisos
npx tsc --noEmit     # limpio
npm run test -- --run   # 196/196 tests en verde (ver «Métricas» sobre el umbral de cobertura)
npm run build        # bundle principal (index-*.js) en 150.20 kB gzip, bajo el límite de 200 KB
```
Visualmente: abrir `/`, `/rutinas`, `/nutricion` (con `diet_enabled`), `/perfil` y `/admin`
(con `role: admin`) en móvil y escritorio, oscuro y claro, y confirmar que cada pantalla tiene
como máximo un par de CTAs con el degradado brasa y que la nav inferior/lateral muestra icono
+ píldora activa.

## Métricas
- `npm run build`: `dist/assets/index-*.js` → 466.00 kB sin comprimir / **150.20 kB gzip**
  (< 200 KB). Los chunks por ruta (Editor, Library, Generator, Nutrition, Admin, gráficos)
  siguen en lazy-load aparte, sin cambios de tamaño relevantes por los iconos (SVG inline, sin
  peso de red).
- `npm run test -- --run`: 196/196 tests en verde, 26/26 ficheros.
- Cobertura de ramas global: **84.80 %** tras este cambio, frente a un umbral configurado de
  **85 %** en `vite.config.ts`. Esto **ya fallaba en `origin/main` antes de esta tarea**
  (84.66 % en la misma medición, comprobado revirtiendo temporalmente los cambios de este
  branch y volviendo a correr `npm run test -- --run`). Esta tarea deja la cobertura de ramas
  ligeramente mejor que como la encontró (+0.14 pp: un test nuevo de `AppNav` y la eliminación
  del patrón `?? ""` repetido), pero no cierra el hueco preexistente porque las ramas no
  cubiertas que quedan viven en lógica de negocio fuera del alcance de esta tarea (p. ej.
  `lib/theme.ts`, `lib/reducedMotion.ts`, rutas de error de `session/scheduler.ts`,
  `profile/queries.ts`, ramas de SSR en `getApiBaseUrl` de `ProgramsRoute`). Statements
  (93.21 %), functions (91.33 %) y lines (95.2 %) siguen por encima de su umbral del 85 %.

## Riesgos/pendientes
- El umbral de cobertura de ramas (85 %) en `vite.config.ts` está fallando de forma
  preexistente (ver «Métricas»); recomiendo una tarea de QA dedicada a subir la cobertura de
  ramas de `lib/theme.ts`, `lib/reducedMotion.ts`, `session/scheduler.ts` y
  `profile/queries.ts`, o bajar el umbral a un valor que refleje el estado real del código si
  se prefiere no perseguir cada rama de error poco probable.
- No se tocó `EditorScreen`/`DayEditor`/`GeneratorScreen`/`OnboardingScreen`/`LibraryScreen`
  más allá de la auditoría: ya usaban `Button variant="primary"` correctamente y tenían su
  propio CTA en degradado (`.cta`/`.addLink`), así que no había nada que arreglar ahí; se
  dejan como estaban para no arriesgar sus tests existentes.
- Los iconos de `components/icons.tsx` se dibujaron a mano con formas geométricas simples
  (círculos, líneas, rects) para no depender de ningún set de iconos con licencia de terceros;
  si el equipo de diseño quiere un set más elaborado más adelante, esta capa es fácil de
  sustituir porque cada pantalla importa los iconos por nombre semántico, no por forma.
- No se generaron capturas de pantalla (Playwright) en este pase; si se necesitan para el
  changelog visual, un agente con navegador (o `run`) puede generarlas contra esta rama.

## Peticiones a otros agentes
Ninguna petición bloqueante. Si un agente de QA/tests quiere cerrar el hueco de cobertura de
ramas preexistente, los ficheros señalados en «Riesgos/pendientes» son el punto de partida.

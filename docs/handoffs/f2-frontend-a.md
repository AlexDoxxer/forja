# Handoff · Fase 2 · frontend-ui parte A

Rama: `f2/frontend-a` (sin fusionar; contrato 1.1.0 ya fusionado y cliente/mocks regenerados). Modo rápido: solo Vitest + lint + tsc + build; sin E2E ni Lighthouse.

## Resumen

- **F1-FE-04** Librería base sobre Radix (`src/components/ui/`): Button, Chip, Dialog, Sheet, Tabs, Select, Slider, Toast (+`useToast`), NumberPad, TextField, CheckField, Card, ChoiceCard. Tests con axe-core sin violaciones.
- **Onboarding** (4 pasos + PAR-Q + «activar dieta»): registro, perfil, PAR-Q y primer peso. Perfil se guarda antes que el PAR-Q para que un «sí» fije `beginner` (contrato).
- **Biblioteca**: búsqueda con consulta normalizada (sin acentos/mayúsculas), chips (zona, equipamiento, patrón, dificultad, favoritos), mapa muscular SVG propio clicable (frontal/posterior, teclado), cuadrícula virtualizada (`@tanstack/react-virtual`) con paginación por cursor infinita, vista previa GIF al hover/foco. **Detalle**: pasos en 10 idiomas, variantes (ángulo/demostrador), músculos secundarios en el mapa, alternativas, historial (e1RM), favorito.
- **Generador**: wizard de 6 pasos; sexo preseleccionado del perfil con explicación (énfasis, descansos, demostrador; «nunca excluye ni limita cargas»); vista previa con GIFs, series×reps, descansos, minutos, gráfico de volumen (Recharts diferido + tabla accesible), `rationale_es`, `warnings`; regenerar día, regenerar con otra semilla, cambiar ejercicio (Sheet con alternativas o automático), guardar / guardar y activar.
- **Editor**: días en pestañas, dnd-kit accesible (puntero + teclado, anuncios en español) más botones subir/bajar, superseries/circuitos (unir/separar), campos por ejercicio con validación de forma, validación del motor «en vivo» (guardado diferido 700 ms de `PUT /programs/{id}/days/{day_id}`; muestra `warnings` y `violations` de `plan_invalid`), deshacer/rehacer, buscador lateral.
- **Code-splitting**: todas mis rutas con `lazyRouteComponent`; Recharts y el editor en chunks propios.

## Ficheros tocados

- `frontend/src/components/ui/*`, `src/features/{onboarding,library,generator,editor,shared}/*`
- i18n: `src/i18n/partA.ts` + `src/i18n/partA/*` (paquetes registrados con `addResourceBundle`; una línea en `src/i18n/index.ts`)
- Cableado: `src/routes/router.tsx` (rutas `/onboarding`, `/biblioteca/$exerciseId`, `/rutinas/nueva`, `/rutinas/$programId/editar`; biblioteca ahora lazy), `src/App.tsx` (`ToastProvider`), `src/routes/ProgramsRoute.tsx` (enlaces a generador/editor)
- Eliminados: `src/routes/LibraryRoute.tsx`, `src/features/library/useExerciseList.ts` y su test antiguo (sustituidos)
- Tests: `tests/features/*`, `tests/components/ui/*`, `tests/{axe,radixPolyfills}.ts`, `tests/fixtures/catalog.ts`, `tests/routes/renderWithRouter.tsx`; `docs/TASKS.md`

## Decisiones

- i18n de parte A en paquetes propios para no chocar con `resources.ts` (parte B). Etiquetas de enums (`enums.*`) compartidas.
- Búsqueda: el filtrado tolerante a acentos lo hace la API; el cliente envía `q` plegado (`foldText`).
- Editor: el motor valida al guardar (no se duplica lógica de negocio); en cliente solo rangos del esquema. Arrastrar entre dos bloques de un ejercicio reordena bloques; la superserie es explícita («Unir con el siguiente»). Editor trabaja sobre la semana 0 con opción «aplicar a todas las semanas».
- Sin ADR nuevo.

## Cómo verificar

```bash
cd frontend
npm run lint && npm run typecheck && npm run test && npm run build
```

## Métricas

- lint y typecheck: 0 errores. Vitest: 98 tests verdes; cobertura global stmts 92,9 % · ramas 85,6 % · funcs 91,2 % · líneas 94,8 % (umbral 85 %).
- Build: JS inicial `index-*.js` 126,6 KB gzip (< 200 KB). Chunks diferidos: VolumeChart/Recharts 110,6 KB, Editor 20,6 KB, Detalle 17,1 KB, Biblioteca 10,0 KB, Generador 9,6 KB, Onboarding 2,9 KB.

## Riesgos/pendientes

- Sin capturas ni E2E/Lighthouse (modo rápido). Cambio a API real (F2-FE-16) pendiente de `backend-api`; probado solo con MSW.
- No hay redirección automática a `/onboarding` para usuarios sin `onboarding_completed` ni pantalla de login (guardas de sesión: parte B/orquestador).
- Arrastre real con teclado de dnd-kit no probado en jsdom (sin layout); cubierto por botones subir/bajar y tests del reducer.
- «Añadir a rutina» desde el detalle enlaza a la lista de rutinas; el editor añade desde su buscador.
- Mocks generados devuelven `exercise_id: null` en planes; los tests usan fixtures propios.

## Peticiones a otros agentes

- **backend-api**: confirmar que `PUT /programs/{id}/days/{day_id}` devuelve `warnings` recalculados y `422 plan_invalid` con `violations`; la búsqueda `q` acepta texto ya plegado.
- **orquestador / parte B**: guarda de sesión y redirección a `/onboarding`.

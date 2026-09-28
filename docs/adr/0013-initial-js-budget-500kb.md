# ADR 0013 · Presupuesto de JS inicial: 500 KB gzip

- **Estado**: Aceptado · **Fecha**: 2026-09-28 · **Autor**: orquestador (decisión del propietario del proyecto)

## Contexto
MASTER_PROMPT §10.5 fijaba el JS inicial en < 200 KB gzip. Tras las pasadas visuales de la fase 4
(`f4/visual-polish` y `f4/motion-nav`, que añadió Framer Motion) el bundle principal quedó en
188,85 KB gzip, con unos 11 KB de margen. El propietario pidió además un lenguaje visual más rico
en toda la app (efectos, coreografía de entrada, transiciones; trabajo `f5/*`).

## Decisión
El presupuesto de JS inicial pasa a **< 500 KB gzip**. El resto de §10.5 se mantiene: Lighthouse
móvil ≥ 90 en Rendimiento, Accesibilidad y Buenas prácticas, y LCP < 2,5 s en 4G simulada. El
code-splitting existente (rutas diferidas, Recharts y editor en chunks aparte) se conserva: tener
más margen no es motivo para deshacerlo.

## Alternativas
- Mantener 200 KB y diferir más rutas (`sessionRoute`, `progressRoute`, `profileRoute`,
  `programsRoute`, como proponía `docs/handoffs/f4-motion-nav.md`): viable, pero limita los
  efectos visuales que pide el propietario.
- Quitar el límite: descartado; sin tope, el peso crece sin control y castiga a los móviles con
  mala red, justo donde se usa el reproductor de sesión.

## Consecuencias
- El presupuesto que citan las consecuencias de ADR 0007 (< 200 KB, §10.5) queda sustituido por
  este. ADR 0007 no se edita (regla de este registro).
- Con más JS permitido, la restricción real pasan a ser Lighthouse Rendimiento ≥ 90 y LCP < 2,5 s,
  que vigila el trabajo `lighthouse` de CI.
- Los handoffs anteriores citan 200 KB porque era el límite vigente entonces; no se reescriben.

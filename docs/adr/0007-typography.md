# ADR 0007 · Tipografía autoalojada

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
§10.1 pide titulares en «Archivo» (condensada/expandida, pesos 700–800), texto en «Inter» o
«Atkinson Hyperlegible» (a decidir por ADR) y números tabulares para series y cronómetros.
Las fuentes deben autoalojarse (sin CDNs: CSP `default-src 'self'`, PWA offline, privacidad).

## Decisión
- **Titulares**: **Archivo** variable (ejes `wght` 100–900 y `wdth` 62–125), usada a 700–800
  y con anchura condensada (`font-stretch: 75%–87.5%`) en cabeceras y cifras grandes.
- **Texto e interfaz**: **Inter** variable (`wght` 100–900).
  - Tiene cifras tabulares reales (`font-variant-numeric: tabular-nums`, OpenType `tnum`),
    imprescindibles para series, pesos y el temporizador sin «bailes» de anchura. Atkinson
    Hyperlegible (versión original) no ofrece `tnum`.
  - Cobertura amplia de latín extendido y cirílico, útil para mostrar nombres en otros idiomas.
  - `font-feature-settings: "cv11", "ss01"` opcionales para mejorar la distinción de `1/l/I`
    (la ventaja principal de Atkinson), a criterio de `frontend-ui`.
- **Distribución**: paquetes npm `@fontsource-variable/archivo` y `@fontsource-variable/inter`
  (licencia SIL OFL 1.1), empaquetados por Vite en `/assets` con hash; subconjuntos `latin` y
  `latin-ext` cargados con `font-display: swap`; se precachean en el service worker.
  Licencias OFL incluidas en «Créditos».
- **Respaldo**: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` con
  `size-adjust` para minimizar el salto de maquetación.

## Alternativas
- **Atkinson Hyperlegible** como texto: excelente legibilidad para baja visión, pero sin cifras
  tabulares; obligaría a mezclar dos familias en la misma línea (series/pesos).
- **Fuentes del sistema**: cero bytes, pero apariencia inconsistente entre plataformas y sin
  garantía de `tnum`.
- **Google Fonts por CDN**: prohibido por CSP, privacidad y uso offline.

## Consecuencias
- Presupuesto aproximado: ~70 KB woff2 (Inter latin variable) + ~50 KB (Archivo latin
  variable), fuera del JS inicial (< 200 KB gzip, §10.5).
- `frontend-ui` define tokens tipográficos (`--font-display`, `--font-body`, `--nums-tabular`).

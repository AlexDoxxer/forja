import type { SVGProps } from "react";

/**
 * Iconos de línea, dibujados a mano (sin dependencias externas, CSP `default-src 'self'`;
 * MASTER_PROMPT §11). Trazo fino de 1.8, 24×24 con esquinas y uniones redondeadas para que
 * combinen con la estética general. Puramente decorativos: `aria-hidden` por defecto, la
 * información que transmiten siempre está también en el texto de la etiqueta que acompañan.
 */
export type IconProps = SVGProps<SVGSVGElement>;

const base = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

/** Nav «Hoy»: sol (jornada de hoy). */
export function IconSun(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </svg>
  );
}

/** Nav «Rutinas» / tarjetas de programa: mancuerna. */
export function IconDumbbell(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <line x1="5" y1="12" x2="19" y2="12" />
      <rect x="2.5" y="9" width="4" height="6" rx="1.2" />
      <rect x="17.5" y="9" width="4" height="6" rx="1.2" />
    </svg>
  );
}

/** Nav «Biblioteca»: libro abierto. */
export function IconBook(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M4 5.5c2-1 5-1 7 0v14c-2-1-5-1-7 0z" />
      <path d="M20 5.5c-2-1-5-1-7 0v14c2-1 5-1 7 0z" />
    </svg>
  );
}

/** Nav «Progreso» / gráfico E1RM: línea ascendente. */
export function IconTrendingUp(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <polyline points="3,17 9,11 13,15 21,6" />
      <polyline points="15,6 21,6 21,12" />
    </svg>
  );
}

/** Nav «Perfil»: persona en círculo. */
export function IconUserCircle(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="10" r="3" />
      <path d="M6.5 18.2c1.1-2.3 3.1-3.7 5.5-3.7s4.4 1.4 5.5 3.7" />
    </svg>
  );
}

/** Nav «Nutrición»: hoja. */
export function IconLeaf(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M20 4c-8 0-14 5-14 13 0 1 .4 2 1 2 8 0 13-6 13-14 0-.4 0-.7 0-1z" />
      <path d="M8 18c2-4 5-7 9-10" />
    </svg>
  );
}

/** Nav «Admin»: escudo. */
export function IconShield(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l7 3v6c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6z" />
      <path d="M9 12.2l2 2 4-4.4" />
    </svg>
  );
}

/** Tarjeta «próxima sesión»: calendario con marca. */
export function IconCalendar(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4" />
      <path d="M8.5 13.5l2 2 4-4" />
    </svg>
  );
}

/** Tarjetas de resumen/volumen: barras. */
export function IconChartBar(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" strokeLinecap="round" />
    </svg>
  );
}

/** Tarjeta «peso corporal»: báscula. */
export function IconScale(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" />
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 8.8v1.1" />
    </svg>
  );
}

/** Récords / mejores marcas: trofeo. */
export function IconTrophy(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
      <path d="M8 5.5H5.5a2 2 0 0 0 0 4H8M16 5.5h2.5a2 2 0 0 1 0 4H16" />
      <path d="M10 15.5v2M14 15.5v2M8 20h8M9.5 17.5h5" />
    </svg>
  );
}

/** Objetivos de nutrición: diana. */
export function IconTarget(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4.2" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Plan / listas de tareas: portapapeles. */
export function IconClipboardList(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <rect x="5" y="4.5" width="14" height="16" rx="2" />
      <path d="M9 4.5V3.8a1.3 1.3 0 0 1 1.3-1.3h3.4A1.3 1.3 0 0 1 15 3.8v.7" />
      <path d="M8.5 10.5h7M8.5 14h7M8.5 17.5h4" />
    </svg>
  );
}

/** Ajustes: engranaje. */
export function IconSettings(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5v2.4M12 18.1v2.4M4.5 8.2l2.1 1.2M17.4 14.6l2.1 1.2M4.5 15.8l2.1-1.2M17.4 9.4l2.1-1.2M3.5 12h2.4M18.1 12h2.4" />
    </svg>
  );
}

/** Mapa de actividad (heatmap): cuadrícula. */
export function IconGrid(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="3.5" width="6" height="6" rx="1" />
      <rect x="14.5" y="3.5" width="6" height="6" rx="1" />
      <rect x="3.5" y="14.5" width="6" height="6" rx="1" />
      <rect x="14.5" y="14.5" width="6" height="6" rx="1" />
    </svg>
  );
}

/** Exportar / descargar datos. */
export function IconDownload(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5v11.5M8 11l4 4 4-4" />
      <path d="M4.5 17v2a1.5 1.5 0 0 0 1.5 1.5h12a1.5 1.5 0 0 0 1.5-1.5v-2" />
    </svg>
  );
}

/** Sesiones activas / dispositivos. */
export function IconDevices(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="4.5" width="13" height="9" rx="1.4" />
      <path d="M6 17h7" />
      <rect x="15.5" y="10" width="6" height="9.5" rx="1.2" />
      <path d="M18.5 17.3h.01" />
    </svg>
  );
}

/** Descarga para uso sin conexión: nube. */
export function IconCloudDownload(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M7 17.5a4 4 0 0 1-.5-7.97 5 5 0 0 1 9.7-1.6 4.2 4.2 0 0 1 1.3 8.17" />
      <path d="M12 10.5V17M9.2 14.2 12 17l2.8-2.8" />
    </svg>
  );
}

/** Créditos y licencias: información. */
export function IconInfo(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8.2h.01M11.6 11.5h.8v5.3h-1" />
    </svg>
  );
}

/** Administración de personas. */
export function IconUsers(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8.5" r="3" />
      <path d="M3.5 19c.7-3 2.9-4.8 5.5-4.8s4.8 1.8 5.5 4.8" />
      <path d="M16 6.2a3 3 0 0 1 0 5.8M18 19c-.4-1.9-1.4-3.4-2.8-4.2" />
    </svg>
  );
}

/** Reingesta / recalcular: flechas circulares. */
export function IconRefresh(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M4.5 12a7.5 7.5 0 0 1 12.6-5.5M19.5 12a7.5 7.5 0 0 1-12.6 5.5" />
      <path d="M17.5 3.5v3.5H14M6.5 20.5V17H10" />
    </svg>
  );
}

/** Estado vacío genérico: bandeja. */
export function IconInbox(props: IconProps): React.JSX.Element {
  return (
    <svg {...base} {...props}>
      <path d="M4 12.5 6.2 5h11.6l2.2 7.5" />
      <path d="M4 12.5h5l1.3 2.5h3.4l1.3-2.5h5v5A2 2 0 0 1 18 19.5H6A2 2 0 0 1 4 17.5z" />
    </svg>
  );
}

import { Link, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";

import { useSession } from "../features/auth/session";
import { cx } from "../lib/cx";
import { useReducedMotion } from "../lib/useReducedMotion";
import styles from "./AppNav.module.css";
import {
  IconBook,
  IconDumbbell,
  IconLeaf,
  IconShield,
  IconSun,
  IconTrendingUp,
  IconUserCircle,
  type IconProps,
} from "./icons";

interface NavItem {
  to: string;
  labelKey: "nav.today" | "nav.programs" | "nav.library" | "nav.progress" | "nav.profile" | "nav.nutrition" | "nav.admin";
  Icon: (props: IconProps) => React.JSX.Element;
}

/** Grupo «Entrenar» (MASTER_PROMPT §10.1): siempre disponible, orden fijo. */
const TRAIN_ITEMS: readonly NavItem[] = [
  { to: "/", labelKey: "nav.today", Icon: IconSun },
  { to: "/rutinas", labelKey: "nav.programs", Icon: IconDumbbell },
  { to: "/biblioteca", labelKey: "nav.library", Icon: IconBook },
  { to: "/progreso", labelKey: "nav.progress", Icon: IconTrendingUp },
];

const NAV_PILL_LAYOUT_ID = "app-nav-active-pill";

/** Misma regla de coincidencia que usaba `activeOptions` de `Link`: exacta solo para «Hoy». */
function isItemActive(pathname: string, to: string): boolean {
  if (to === "/") return pathname === "/";
  return pathname === to || pathname.startsWith(`${to}/`);
}

interface NavLinkProps {
  item: NavItem;
  isActive: boolean;
  reducedMotion: boolean;
}

/**
 * Un enlace de nav. La píldora activa es un `motion.span` con `layoutId` compartido entre
 * todos los enlaces: al cambiar de ruta, Framer Motion anima su posición/tamaño de un enlace
 * al otro («magnetic slide») en vez de solo aparecer. Con `prefers-reduced-motion` se omite el
 * `layoutId` y la píldora aparece/desaparece sin transición.
 */
function NavLink({ item, isActive, reducedMotion }: NavLinkProps): React.JSX.Element {
  const { t } = useTranslation();
  const { to, labelKey, Icon } = item;
  return (
    <Link
      to={to}
      className={cx(styles["link"], isActive && styles["active"])}
      aria-current={isActive ? "page" : undefined}
    >
      {isActive &&
        (reducedMotion ? (
          <span className={styles["pill"]} />
        ) : (
          <motion.span
            layoutId={NAV_PILL_LAYOUT_ID}
            className={styles["pill"]}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
          />
        ))}
      <span className={styles["iconWrap"]}>
        <Icon className={styles["icon"]} />
      </span>
      <span className={styles["label"]}>{t(labelKey)}</span>
    </Link>
  );
}

/**
 * Navegación principal: inferior en móvil, lateral en escritorio (misma marca de navegación,
 * reposicionada por CSS; MASTER_PROMPT §10.1). Objetivos táctiles >= 48 px. Se agrupa en
 * «Entrenar» y «Cuenta» en el rail de escritorio (subtítulo + separador); en la barra inferior
 * móvil no hay sitio para dos grupos, así que se muestra como una sola fila (el CSS colapsa el
 * agrupado con `display: contents`, sin tocar el orden lógico de los enlaces). «Nutrición» y
 * «Admin» solo aparecen cuando la sesión los tiene disponibles (el servidor sigue siendo quien
 * autoriza el acceso real; esto solo evita mostrar enlaces sin uso).
 */
export function AppNav(): React.JSX.Element {
  const { t } = useTranslation();
  const session = useSession();
  const me = session.data;
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const reducedMotion = useReducedMotion();

  const accountItems: readonly NavItem[] = [
    ...(me?.diet_available === true ? [{ to: "/nutricion", labelKey: "nav.nutrition" as const, Icon: IconLeaf }] : []),
    { to: "/perfil", labelKey: "nav.profile" as const, Icon: IconUserCircle },
    ...(me?.role === "admin" ? [{ to: "/admin", labelKey: "nav.admin" as const, Icon: IconShield }] : []),
  ];

  return (
    <nav className={styles["nav"]} aria-label={t("app.name")}>
      <div className={styles["group"]}>
        <p className={styles["groupLabel"]}>{t("nav.groupTrain")}</p>
        {TRAIN_ITEMS.map((item) => (
          <NavLink key={item.to} item={item} isActive={isItemActive(pathname, item.to)} reducedMotion={reducedMotion} />
        ))}
      </div>
      <div className={styles["divider"]} />
      <div className={styles["group"]}>
        <p className={styles["groupLabel"]}>{t("nav.groupAccount")}</p>
        {accountItems.map((item) => (
          <NavLink key={item.to} item={item} isActive={isItemActive(pathname, item.to)} reducedMotion={reducedMotion} />
        ))}
      </div>
    </nav>
  );
}

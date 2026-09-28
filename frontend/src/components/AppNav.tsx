import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { useSession } from "../features/auth/session";
import { cx } from "../lib/cx";
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

const NAV_ITEMS: readonly NavItem[] = [
  { to: "/", labelKey: "nav.today", Icon: IconSun },
  { to: "/rutinas", labelKey: "nav.programs", Icon: IconDumbbell },
  { to: "/biblioteca", labelKey: "nav.library", Icon: IconBook },
  { to: "/progreso", labelKey: "nav.progress", Icon: IconTrendingUp },
  { to: "/perfil", labelKey: "nav.profile", Icon: IconUserCircle },
];

/**
 * Navegación principal: inferior en móvil, lateral en escritorio (misma marca de navegación,
 * reposicionada por CSS; MASTER_PROMPT §10.1). Objetivos táctiles >= 48 px. «Nutrición» y
 * «Admin» solo aparecen cuando la sesión los tiene disponibles (el servidor sigue siendo quien
 * autoriza el acceso real; esto solo evita mostrar enlaces sin uso).
 */
export function AppNav(): React.JSX.Element {
  const { t } = useTranslation();
  const session = useSession();
  const me = session.data;

  const items: readonly NavItem[] = [
    ...NAV_ITEMS,
    ...(me?.diet_available === true ? [{ to: "/nutricion", labelKey: "nav.nutrition" as const, Icon: IconLeaf }] : []),
    ...(me?.role === "admin" ? [{ to: "/admin", labelKey: "nav.admin" as const, Icon: IconShield }] : []),
  ];

  return (
    <nav className={styles["nav"]} aria-label={t("app.name")}>
      {items.map(({ to, labelKey, Icon }) => (
        <Link
          key={to}
          to={to}
          className={styles["link"]}
          activeOptions={{ exact: to === "/" }}
          activeProps={{
            className: cx(styles["link"], styles["active"]),
            "aria-current": "page",
          }}
        >
          <span className={styles["iconWrap"]}>
            <Icon className={styles["icon"]} />
          </span>
          <span className={styles["label"]}>{t(labelKey)}</span>
        </Link>
      ))}
    </nav>
  );
}

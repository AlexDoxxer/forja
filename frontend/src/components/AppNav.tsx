import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { cx } from "../lib/cx";
import styles from "./AppNav.module.css";

interface NavItem {
  to: string;
  labelKey: "nav.today" | "nav.programs" | "nav.library" | "nav.progress" | "nav.profile";
}

const NAV_ITEMS: readonly NavItem[] = [
  { to: "/", labelKey: "nav.today" },
  { to: "/rutinas", labelKey: "nav.programs" },
  { to: "/biblioteca", labelKey: "nav.library" },
  { to: "/progreso", labelKey: "nav.progress" },
  { to: "/perfil", labelKey: "nav.profile" },
];

/**
 * Navegación principal: inferior en móvil, lateral en escritorio (misma marca de navegación,
 * reposicionada por CSS; MASTER_PROMPT §10.1). Objetivos táctiles >= 48 px.
 */
export function AppNav(): React.JSX.Element {
  const { t } = useTranslation();

  return (
    <nav className={styles["nav"]} aria-label={t("app.name")}>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={styles["link"]}
          activeOptions={{ exact: item.to === "/" }}
          activeProps={{
            className: cx(styles["link"], styles["active"]),
            "aria-current": "page",
          }}
        >
          {t(item.labelKey)}
        </Link>
      ))}
    </nav>
  );
}

import { Outlet } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { AppNav } from "../components/AppNav";
import styles from "./RootLayout.module.css";

/**
 * App shell (MASTER_PROMPT §10.1): enlace para saltar al contenido, navegación
 * inferior/lateral responsiva y el contenido de la ruta activa.
 */
export function RootLayout(): React.JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <a href="#main-content" className="skip-link">
        {t("nav.skipToContent")}
      </a>
      <AppNav />
      <main id="main-content" className={styles["main"]}>
        <Outlet />
      </main>
    </>
  );
}

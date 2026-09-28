import { Outlet, useRouterState } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "react-i18next";

import { AppNav } from "../components/AppNav";
import { AuthGate } from "../features/auth/AuthGate";
import { isPublicPath } from "../features/auth/session";
import { useReducedMotion } from "../lib/useReducedMotion";
import styles from "./RootLayout.module.css";

/**
 * App shell (MASTER_PROMPT §10.1): enlace para saltar al contenido, navegación
 * inferior/lateral responsiva y el contenido de la ruta activa. El cambio de ruta hace un
 * único crossfade discreto (150 ms; §10.1 «microinteracciones sobrias») en vez de una
 * transición con varias fases; con `prefers-reduced-motion` se omite del todo.
 */
export function RootLayout(): React.JSX.Element {
  const { t } = useTranslation();
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const reducedMotion = useReducedMotion();

  return (
    <>
      {/* Grano global (F5): una sola capa, montada una vez aquí (nunca por pantalla). */}
      <div className="grain-overlay" aria-hidden="true" />
      <a href="#main-content" className="skip-link">
        {t("nav.skipToContent")}
      </a>
      {isPublicPath(pathname) ? null : <AppNav />}
      <main id="main-content" className={styles["main"]}>
        <AuthGate>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={pathname}
              initial={{ opacity: reducedMotion ? 1 : 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: reducedMotion ? 1 : 0 }}
              transition={{ duration: reducedMotion ? 0 : 0.15, ease: "easeInOut" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </AuthGate>
      </main>
    </>
  );
}

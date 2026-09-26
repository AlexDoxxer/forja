import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { isPublicPath, redirectTarget, useSession } from "./session";
import "./strings";

/**
 * Guarda de sesión de todas las rutas de la app: sin sesión (401 en `GET /auth/me`) lleva a
 * `/login`; con sesión pero sin onboarding completado, a `/onboarding`.
 */
export function AuthGate({ children }: { children: ReactNode }): React.JSX.Element {
  const { t } = useTranslation();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const session = useSession();
  const target = redirectTarget(pathname, session);

  useEffect(() => {
    if (target !== null) void navigate({ to: target, replace: true });
  }, [target, navigate]);

  if (isPublicPath(pathname)) return <>{children}</>;
  if (session.isLoading || target !== null) return <p role="status">{t("auth.checking")}</p>;
  if (session.isError) {
    // Error de red o 5xx: no expulsamos a la persona; se le indica y puede reintentar.
    return (
      <p role="alert">
        {t("auth.unreachable")}{" "}
        <button type="button" onClick={() => void session.refetch()}>
          {t("auth.retry")}
        </button>
      </p>
    );
  }
  return <>{children}</>;
}

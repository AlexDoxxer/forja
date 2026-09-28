import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type CurrentUser = components["schemas"]["CurrentUser"];

/** Sin sesión válida (`GET /auth/me` → 401). */
export class UnauthenticatedError extends Error {
  constructor() {
    super("No hay una sesión activa.");
  }
}

/** Rutas que se pueden ver sin sesión (la cuenta se crea en el primer paso de onboarding). */
export const PUBLIC_PATHS = ["/login", "/onboarding"] as const;

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/**
 * De las rutas públicas, cuáles además ocupan el viewport completo, sin el padding/ancho máximo
 * del shell (`RootLayout.module.css` `.main`, pensado para convivir con `AppNav`). `/login` es
 * una landing de un único momento de pantalla completa (F5-FE-02); `/onboarding` sigue siendo
 * pública pero es un asistente de formulario estándar (`OnboardingScreen`, `max-width: 40rem`
 * propio) que depende de ese padding para su respiro visual, así que no entra aquí — ver
 * «Decisiones» en `docs/handoffs/f5-login-polish.md`.
 */
export const FULL_BLEED_PATHS = ["/login"] as const;

export function isFullBleedPath(pathname: string): boolean {
  return FULL_BLEED_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Usuario actual. Una sola consulta compartida por la guarda de sesión y las pantallas. */
export function useSession(): UseQueryResult<CurrentUser> {
  return useQuery({
    queryKey: ["auth", "me"],
    retry: false,
    queryFn: async () => {
      const result = await api.GET("/auth/me");
      if (result.response.status === 401) throw new UnauthenticatedError();
      return unwrapApi(result);
    },
  });
}

/** Destino al que hay que redirigir según sesión y onboarding, o `null` si se puede seguir. */
export function redirectTarget(
  pathname: string,
  session: { isLoading: boolean; error: unknown; data: CurrentUser | undefined },
): "/login" | "/onboarding" | "/" | null {
  if (session.isLoading) return null;
  const isPublic = isPublicPath(pathname);
  if (session.error instanceof UnauthenticatedError) return isPublic ? null : "/login";
  if (session.data !== undefined && !session.data.onboarding_completed && !isPublic) return "/onboarding";
  if (session.data !== undefined && pathname === "/login") return "/";
  return null;
}

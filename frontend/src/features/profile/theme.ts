import type { components } from "../../lib/api/schema";
import type { Theme } from "../../lib/theme";

/** Resuelve la preferencia de tema («system» sigue al sistema operativo). */
export function resolveTheme(pref: components["schemas"]["ThemePreference"]): Theme {
  if (pref !== "system") return pref;
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

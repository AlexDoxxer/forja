export type Theme = "dark" | "light";

const STORAGE_KEY = "forja-theme";
const DEFAULT_THEME: Theme = "dark";

function isTheme(value: string | null): value is Theme {
  return value === "dark" || value === "light";
}

/** Tema guardado por la persona, si lo cambió en ajustes; si no, oscuro (§10.1). */
export function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isTheme(stored) ? stored : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Almacenamiento no disponible; el tema seguirá aplicado solo en esta carga.
  }
}

/** Aplica el tema guardado (u oscuro por defecto) al arrancar la aplicación. */
export function bootstrapTheme(): void {
  applyTheme(readStoredTheme());
}

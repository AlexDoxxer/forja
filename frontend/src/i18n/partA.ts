import type { i18n as I18n } from "i18next";

import { editor } from "./partA/editor";
import { enums } from "./partA/enums";
import { generator } from "./partA/generator";
import { library } from "./partA/library";
import { onboarding } from "./partA/onboarding";
import { programs } from "./partA/programs";
import { ui } from "./partA/ui";

/**
 * Recursos de i18n de las pantallas de la parte A (onboarding, biblioteca, generador, editor)
 * y de los componentes base `components/ui`. Se registran como paquetes adicionales para no
 * mezclar ficheros con `resources.ts` (compartido con la parte B).
 */
export const partABundles = {
  ui,
  enums,
  onboarding,
  // `library` amplía el paquete existente de la Fase 1 (mismo espacio de nombres).
  library,
  generator,
  editor,
  programs,
} as const;

export function registerPartA(instance: I18n): void {
  for (const language of ["es", "en"] as const) {
    for (const [namespace, bundle] of Object.entries(partABundles)) {
      instance.addResourceBundle(language, "translation", { [namespace]: bundle[language] }, true, true);
    }
  }
}

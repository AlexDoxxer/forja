import { i18next } from "../../i18n";

export interface Tree {
  [key: string]: string | Tree;
}

/**
 * Registra las cadenas de las pantallas de la parte B (sesión, progreso, nutrición, perfil,
 * admin) sin tocar `i18n/resources.ts`. Las claves de `es` y `en` deben coincidir
 * (`tests/features/i18nB.test.ts`).
 */
export function registerBundle(name: string, es: Tree, en: Tree): void {
  i18next.addResourceBundle("es", "translation", { [name]: es }, true, true);
  i18next.addResourceBundle("en", "translation", { [name]: en }, true, true);
}

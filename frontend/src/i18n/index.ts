import i18next from "i18next";
import { initReactI18next } from "react-i18next";

import { registerPartA } from "./partA";
import { DEFAULT_LANGUAGE, resources } from "./resources";

const STORAGE_KEY = "forja-locale";

function readStoredLanguage(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

void i18next.use(initReactI18next).init({
  resources,
  lng: readStoredLanguage() ?? DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false },
  returnNull: false,
});

registerPartA(i18next);

i18next.on("languageChanged", (language) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // El almacenamiento no está disponible (privacidad del navegador); se ignora.
  }
});

export { i18next };

import { describe, expect, it } from "vitest";

import { resources, SUPPORTED_LANGUAGES } from "../src/i18n/resources";

/** Recoge todas las rutas de clave (`a.b.c`) de un árbol de traducciones anidado. */
function collectKeyPaths(node: unknown, prefix = ""): string[] {
  if (typeof node !== "object" || node === null) {
    return [prefix];
  }
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    collectKeyPaths(value, prefix === "" ? key : `${prefix}.${key}`),
  );
}

describe("i18n — recursos es/en (MASTER_PROMPT §10.4)", () => {
  it("declara español e inglés como únicos idiomas de la interfaz, con es por defecto", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["es", "en"]);
  });

  it("no deja cadenas sin traducir: las claves de es y en coinciden exactamente", () => {
    const esKeys = collectKeyPaths(resources.es.translation).sort();
    const enKeys = collectKeyPaths(resources.en.translation).sort();
    expect(enKeys).toEqual(esKeys);
  });

  it("ninguna cadena de es o en está vacía", () => {
    for (const lang of SUPPORTED_LANGUAGES) {
      const values = collectKeyPaths(resources[lang].translation).map((path) =>
        path.split(".").reduce<unknown>((node, segment) => {
          if (typeof node !== "object" || node === null) return node;
          return (node as Record<string, unknown>)[segment];
        }, resources[lang].translation),
      );
      for (const value of values) {
        expect(typeof value).toBe("string");
        expect((value as string).trim().length).toBeGreaterThan(0);
      }
    }
  });
});

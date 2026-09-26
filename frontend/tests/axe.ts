import axe from "axe-core";
import { expect } from "vitest";

/** Ejecuta axe-core sobre un nodo y falla con la lista de violaciones (regla del rol: a11y en componentes clave). */
export async function expectNoAxeViolations(container: Element): Promise<void> {
  const results = await axe.run(container, {
    // jsdom no calcula colores ni diseño; el contraste se verifica en tests/design-tokens.test.ts.
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
  });
  const summary = results.violations.map((violation) => `${violation.id}: ${violation.help} (${String(violation.nodes.length)})`);
  expect(summary).toEqual([]);
}

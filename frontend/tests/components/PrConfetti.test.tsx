import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PrConfetti from "../../src/components/PrConfetti";

/**
 * Confeti discreto de récord personal (MASTER_PROMPT §10.1): puramente decorativo
 * (`aria-hidden`), así que se prueba por estructura (número de motas) en vez de por rol/texto.
 */
describe("PrConfetti", () => {
  it("dibuja un puñado de motas decorativas sin exponer nada a los lectores de pantalla", () => {
    const { container } = render(<PrConfetti />);
    const burst = container.querySelector('[aria-hidden="true"]');
    expect(burst).not.toBeNull();
    const particles = container.querySelectorAll('[aria-hidden="true"] > span');
    expect(particles.length).toBeGreaterThanOrEqual(6);
    expect(particles.length).toBeLessThanOrEqual(10);
  });
});

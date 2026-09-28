import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Reveal } from "../../src/components/Reveal";

function mockReducedMotion(reduced: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion") ? reduced : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
}

/**
 * Coreografía de entrada reutilizable (F5, técnica 4). El estado de reposo siempre debe ser
 * visible: con movimiento normal, se monta como `motion.div` con la variante pedida; con
 * `prefers-reduced-motion`, se salta la animación por completo (MASTER_PROMPT §10.1, §10.4).
 */
describe("Reveal", () => {
  it("con movimiento normal, muestra los hijos (motion.div con la variante pedida)", () => {
    mockReducedMotion(false);
    render(
      <Reveal variant="scale" delay={0.1} className="mi-clase">
        <p>Contenido revelado</p>
      </Reveal>,
    );
    expect(screen.getByText("Contenido revelado")).toBeInTheDocument();
  });

  it("con movimiento reducido, muestra los hijos sin animación (div plano)", () => {
    mockReducedMotion(true);
    render(
      <Reveal variant="pop" className="mi-clase">
        <p>Contenido sin animar</p>
      </Reveal>,
    );
    const text = screen.getByText("Contenido sin animar");
    expect(text).toBeInTheDocument();
    expect(text.parentElement).toHaveClass("mi-clase");
  });
});

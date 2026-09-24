import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { ProgressRoute } from "../../src/routes/ProgressRoute";
import { renderWithQuery } from "./renderWithQuery";

describe("ProgressRoute", () => {
  it("muestra el volumen semanal por grupo muscular", async () => {
    renderWithQuery(<ProgressRoute />);

    expect(await screen.findByText("2026-09-23")).toBeInTheDocument();
    expect(screen.getByText(/chest: 0 · 0 kg/)).toBeInTheDocument();
  });
});

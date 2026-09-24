import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { LibraryRoute } from "../../src/routes/LibraryRoute";
import { renderWithQuery } from "./renderWithQuery";

describe("LibraryRoute", () => {
  it("lista los ejercicios con su medio y la atribución de Gym visual", async () => {
    renderWithQuery(<LibraryRoute />);

    expect(await screen.findByText("1 ejercicio encontrado")).toBeInTheDocument();
    expect(screen.getByText("sentadilla con barra")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "© Gym visual" })).toHaveAttribute(
      "href",
      "https://gymvisual.com/",
    );
  });
});

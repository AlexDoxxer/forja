import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { ProfileRoute } from "../../src/routes/ProfileRoute";
import { renderWithQuery } from "./renderWithQuery";

describe("ProfileRoute", () => {
  it("muestra los créditos: commit del dataset, nº de ejercicios y atribución de medios", async () => {
    renderWithQuery(<ProfileRoute />);

    expect(await screen.findByText("7455efae41b330c265e7cd4b78dfa848e7ce5ebd")).toBeInTheDocument();
    expect(screen.getByText("1324")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "© Gym visual" })).toHaveAttribute(
      "href",
      "https://gymvisual.com/",
    );
    expect(
      screen.getByText("Forja no sustituye el consejo de profesionales sanitarios ni de entrenamiento."),
    ).toBeInTheDocument();
  });
});

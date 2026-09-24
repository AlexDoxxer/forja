import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/App";

describe("App", () => {
  it("monta la navegación principal y la pantalla «Hoy» por defecto", async () => {
    render(<App />);

    expect(screen.getByRole("navigation", { name: "Forja" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Hoy" })).toBeInTheDocument();
  });

  it("incluye un enlace para saltar al contenido principal", () => {
    render(<App />);

    const skipLink = screen.getByRole("link", { name: "Saltar al contenido" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/App";

describe("App", () => {
  it("monta la navegación principal y la pantalla «Hoy» por defecto", async () => {
    render(<App />);

    expect(await screen.findByRole("navigation", { name: "Forja" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Hoy" })).toBeInTheDocument();
  });

  it("incluye un enlace para saltar al contenido principal", async () => {
    render(<App />);

    const skipLink = await screen.findByRole("link", { name: "Saltar al contenido" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
  });
});

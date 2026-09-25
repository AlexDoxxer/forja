import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("main", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    document.documentElement.removeAttribute("data-theme");
    vi.resetModules();
  });

  it("monta la aplicación en #root y aplica el tema oscuro por defecto", async () => {
    const root = document.createElement("div");
    root.id = "root";
    document.body.append(root);

    await import("../src/main");

    expect(await screen.findByRole("heading", { level: 1, name: "Hoy" })).toBeInTheDocument();
    expect(document.documentElement.dataset["theme"]).toBe("dark");
  });

  it("falla con un mensaje claro si falta #root", async () => {
    await expect(import("../src/main")).rejects.toThrow("#root");
  });
});

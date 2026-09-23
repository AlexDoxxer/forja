import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("main", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.resetModules();
  });

  it("monta la aplicación en #root", async () => {
    const root = document.createElement("div");
    root.id = "root";
    document.body.append(root);

    await import("../src/main");

    expect(await screen.findByRole("heading", { name: "Forja" })).toBeInTheDocument();
  });

  it("falla con un mensaje claro si falta #root", async () => {
    await expect(import("../src/main")).rejects.toThrow("#root");
  });
});

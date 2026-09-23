import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/App";

describe("App", () => {
  it("muestra el nombre del producto como encabezado principal", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Forja" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });
});

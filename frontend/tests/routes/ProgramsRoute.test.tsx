import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { ProgramsRoute } from "../../src/routes/ProgramsRoute";
import { server } from "../../src/mocks/server";
import { renderWithQuery } from "./renderWithQuery";
import { screen } from "@testing-library/react";

describe("ProgramsRoute", () => {
  it("muestra los programas guardados con su estado activo y días por semana", async () => {
    renderWithQuery(<ProgramsRoute />);

    expect(await screen.findByText("Hipertrofia 4 días · glúteo")).toBeInTheDocument();
    expect(screen.getByText("(Activa)")).toBeInTheDocument();
    expect(screen.getByText("4 días por semana")).toBeInTheDocument();
  });

  it("muestra un estado vacío cuando la persona no tiene rutinas guardadas", async () => {
    server.use(
      http.get("/api/v1/programs", () => HttpResponse.json({ items: [], next_cursor: null }, { status: 200 })),
    );

    renderWithQuery(<ProgramsRoute />);

    expect(await screen.findByText("Todavía no tienes ninguna rutina guardada.")).toBeInTheDocument();
  });
});

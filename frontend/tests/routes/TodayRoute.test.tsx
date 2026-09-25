import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { TodayRoute } from "../../src/routes/TodayRoute";
import { server } from "../../src/mocks/server";
import { renderWithQuery } from "./renderWithQuery";

describe("TodayRoute", () => {
  it("muestra el resumen semanal desde /stats/overview", async () => {
    renderWithQuery(<TodayRoute />);

    expect(await screen.findByText("0 kg")).toBeInTheDocument();
    expect(screen.getByText("Sesiones completadas")).toBeInTheDocument();
    expect(screen.getByText("Sesiones planificadas")).toBeInTheDocument();
    expect(screen.getByText("Semanas seguidas cumplidas")).toBeInTheDocument();
    expect(screen.getAllByText("0")).toHaveLength(3);
  });

  it("muestra un mensaje de error si la petición falla", async () => {
    server.use(
      http.get("/api/v1/stats/overview", () =>
        HttpResponse.json(
          { type: "/problems/unauthenticated", title: "No autenticado", status: 401, code: "unauthenticated" },
          { status: 401 },
        ),
      ),
    );

    renderWithQuery(<TodayRoute />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se ha podido cargar el resumen. Inténtalo de nuevo.",
    );
  });
});

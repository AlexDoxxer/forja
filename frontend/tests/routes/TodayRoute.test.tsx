import "fake-indexeddb/auto";

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { closeDb, loadActiveState } from "../../src/features/session/storage";
import { server } from "../../src/mocks/server";
import { TodayRoute } from "../../src/routes/TodayRoute";
import { makeNextSession } from "../features/session/fixtures";
import { renderRoute } from "../features/renderRoute";

beforeEach(async () => {
  await closeDb();
  indexedDB.deleteDatabase("forja");
});

const overview = {
  week_start: "2026-09-21",
  sessions_completed: 2,
  sessions_planned: 4,
  sets_completed: 30,
  volume_kg: 5400,
  streak_weeks: 3,
  last_record: null,
  body_weight: { latest: null, moving_average_7d_kg: null },
  activity: [],
};

describe("TodayRoute", () => {
  it("muestra el resumen semanal desde /stats/overview y el día programado", async () => {
    server.use(
      http.get("/api/v1/stats/overview", () => HttpResponse.json(overview)),
      http.get("/api/v1/sessions/next", () => HttpResponse.json(makeNextSession())),
    );
    renderRoute(<TodayRoute />);

    expect(await screen.findByText("Toca hoy: Día A")).toBeInTheDocument();
    expect(await screen.findByText("Sesiones completadas")).toBeInTheDocument();
    expect(screen.getByText(/5[.,]?400 kg/)).toBeInTheDocument();
    expect(screen.getByText("Todavía sin récords.")).toBeInTheDocument();
  });

  it("«Empezar» crea la sesión en IndexedDB y navega al reproductor", async () => {
    server.use(
      http.get("/api/v1/stats/overview", () => HttpResponse.json(overview)),
      http.get("/api/v1/sessions/next", () => HttpResponse.json(makeNextSession())),
      http.post("/api/v1/sync", () => HttpResponse.error()),
    );
    const { router } = renderRoute(<TodayRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Empezar" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/sesion");
    });
    const state = await loadActiveState();
    expect(state?.slots).toHaveLength(2);
  });

  it.each([
    ["rest_day", "Hoy es día de descanso. Recuperar también es entrenar."],
    ["no_active_program", "Aún no tienes un programa activo."],
    ["program_completed", "Has completado tu programa. ¡Buen trabajo!"],
  ])("estado %s", async (status, text) => {
    server.use(
      http.get("/api/v1/stats/overview", () => HttpResponse.json(overview)),
      http.get("/api/v1/sessions/next", () =>
        HttpResponse.json({ ...makeNextSession(), status, day: null, suggestions: [], exercises: [] }),
      ),
    );
    renderRoute(<TodayRoute />);
    expect(await screen.findByText(text)).toBeInTheDocument();
  });

  it("guarda el peso corporal rápido", async () => {
    let body: unknown = null;
    server.use(
      http.get("/api/v1/stats/overview", () => HttpResponse.json(overview)),
      http.get("/api/v1/sessions/next", () =>
        HttpResponse.json({ ...makeNextSession(), status: "rest_day", day: null }),
      ),
      http.post("/api/v1/body-metrics", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          {
            id: "m",
            date: "2026-09-26",
            weight_kg: 80.5,
            body_fat_pct: null,
            waist_cm: null,
            created_at: "2026-09-26T08:00:00Z",
            updated_at: "2026-09-26T08:00:00Z",
          },
          { status: 201 },
        );
      }),
    );
    renderRoute(<TodayRoute />);
    await userEvent.type(await screen.findByLabelText("Peso de hoy (kg)"), "80,5");
    await userEvent.click(screen.getByRole("button", { name: "Guardar peso" }));
    expect(await screen.findByText("Peso guardado.")).toBeInTheDocument();
    expect(body).toMatchObject({ weight_kg: 80.5 });
  });

  it("muestra un mensaje de error si el resumen falla", async () => {
    server.use(
      http.get("/api/v1/stats/overview", () =>
        HttpResponse.json({ type: "/p", title: "No autenticado", status: 401 }, { status: 401 }),
      ),
    );
    renderRoute(<TodayRoute />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => a.textContent?.includes("No se ha podido cargar el resumen"))).toBe(true);
  });
});

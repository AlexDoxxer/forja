import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { buildHeatmap, withMovingAverage } from "../../src/features/progress/math";
import { server } from "../../src/mocks/server";
import { ProgressRoute } from "../../src/routes/ProgressRoute";
import { renderWithQuery } from "./renderWithQuery";
import "../../src/i18n";

const record = {
  id: "r1",
  exercise_id: "0001",
  exercise_name_es: "Press banca",
  kind: "e1rm",
  value: 82.5,
  weight_kg: 70,
  reps: 5,
  achieved_at: "2026-09-20T10:00:00Z",
  session_id: "s1",
  set_id: null,
};

function useData(): void {
  const today = new Date().toISOString().slice(0, 10);
  server.use(
    http.get("/api/v1/stats/overview", () =>
      HttpResponse.json({
        week_start: today,
        sessions_completed: 1,
        sessions_planned: 3,
        sets_completed: 10,
        volume_kg: 1000,
        streak_weeks: 1,
        last_record: null,
        body_weight: { latest: null, moving_average_7d_kg: null },
        activity: [
          { date: today, session_count: 1, volume_kg: 1000 },
        ],
      }),
    ),
    http.get("/api/v1/stats/volume", () =>
      HttpResponse.json({
        weeks: [
          { week_start: "2026-09-07", groups: [{ group: "chest", effective_sets: 8, volume_kg: 3000 }] },
          { week_start: "2026-09-14", groups: [{ group: "chest", effective_sets: 12, volume_kg: 4200 }, { group: "back", effective_sets: 10, volume_kg: 3900 }] },
        ],
      }),
    ),
    http.get("/api/v1/records", () => HttpResponse.json({ items: [record], next_cursor: null })),
    http.get("/api/v1/stats/exercise/:id", () =>
      HttpResponse.json({
        exercise_id: "0001",
        best_e1rm_kg: 82.5,
        best_set: { weight_kg: 70, reps: 5, rir: 2, date: "2026-09-20" },
        points: [
          { date: "2026-09-13", session_id: "s0", e1rm_kg: 80, best_weight_kg: 68, best_reps: 5, volume_kg: 1000 },
          { date: "2026-09-20", session_id: "s1", e1rm_kg: 82.5, best_weight_kg: 70, best_reps: 5, volume_kg: 1100 },
        ],
      }),
    ),
    http.get("/api/v1/body-metrics", () =>
      HttpResponse.json({
        items: [
          { id: "m1", date: "2026-09-25", weight_kg: 81, body_fat_pct: null, waist_cm: null, created_at: "", updated_at: "" },
          { id: "m2", date: "2026-09-24", weight_kg: 80, body_fat_pct: null, waist_cm: null, created_at: "", updated_at: "" },
        ],
        next_cursor: null,
      }),
    ),
  );
}

describe("math", () => {
  it("media móvil de 7 días naturales", () => {
    const out = withMovingAverage([
      { date: "2026-09-01", weightKg: 80 },
      { date: "2026-09-03", weightKg: 82 },
      { date: "2026-09-10", weightKg: 90 },
    ]);
    expect(out.map((p) => p.average7d)).toEqual([80, 81, 90]);
  });

  it("mapa de calor: semanas en columnas y niveles por cuartiles", () => {
    const grid = buildHeatmap(
      [
        { date: "2026-09-21", session_count: 1, volume_kg: 100 },
        { date: "2026-09-22", session_count: 1, volume_kg: 900 },
      ],
      2,
      new Date(2026, 8, 24),
    );
    expect(grid).toHaveLength(2);
    expect(grid[0]).toHaveLength(7);
    const cells = grid.flat();
    expect(cells.find((c) => c.date === "2026-09-21")?.level).toBeGreaterThan(0);
    expect(cells.find((c) => c.date === "2026-09-22")?.level).toBe(4);
    expect(cells.find((c) => c.date === "2026-09-23")?.level).toBe(0);
    expect(grid[0]?.[0]?.date).toBe("2026-09-14");
  });
});

describe("ProgressRoute", () => {
  it("muestra calendario, récords, volumen, e1RM y peso con media de 7 días", { timeout: 20_000 }, async () => {
    useData();
    const { container } = renderWithQuery(<ProgressRoute />);

    expect(await screen.findByRole("heading", { name: "Progreso" })).toBeInTheDocument();
    // Récords
    expect(await screen.findByText("82,5 kg")).toBeInTheDocument();
    // Calendario: 26 semanas × 7 días
    const heat = await screen.findByRole("list", { name: "Actividad" });
    expect(within(heat).getAllByRole("listitem")).toHaveLength(26 * 7);
    expect(within(heat).getAllByLabelText(/1 sesiones, 1.000 kg|1 sesiones, 1000 kg/)).toHaveLength(1);
    // Volumen de la última semana: tabla de datos (Recharts se carga en un chunk diferido)
    expect(await screen.findByText("Pecho")).toBeInTheDocument();
    expect(screen.getByText("Espalda")).toBeInTheDocument();
    // e1RM del primer ejercicio con récord
    expect(await screen.findByLabelText("Ejercicio")).toHaveValue("0001");
    // Peso corporal: media de 7 días
    expect(await screen.findByText("80,5")).toBeInTheDocument();
    await waitFor(() => {
      expect(container.querySelector(".recharts-responsive-container")).not.toBeNull();
    }, { timeout: 8000 });
  });

  it("estados vacíos", async () => {
    server.use(
      http.get("/api/v1/stats/overview", () =>
        HttpResponse.json({
          week_start: "2026-09-21", sessions_completed: 0, sessions_planned: 0, sets_completed: 0, volume_kg: 0,
          streak_weeks: 0, last_record: null, body_weight: { latest: null, moving_average_7d_kg: null }, activity: [],
        }),
      ),
      http.get("/api/v1/stats/volume", () => HttpResponse.json({ weeks: [] })),
      http.get("/api/v1/records", () => HttpResponse.json({ items: [], next_cursor: null })),
      http.get("/api/v1/body-metrics", () => HttpResponse.json({ items: [], next_cursor: null })),
    );
    renderWithQuery(<ProgressRoute />);
    expect(await screen.findByText("Aún no hay volumen registrado.")).toBeInTheDocument();
    expect(await screen.findByText("Todavía no hay récords.")).toBeInTheDocument();
    expect(await screen.findByText("Registra tu peso en «Hoy» para ver la tendencia.")).toBeInTheDocument();
    expect(await screen.findByText("Registra sesiones para ver la evolución de un ejercicio.")).toBeInTheDocument();
  });

  it("errores de carga", async () => {
    server.use(
      http.get("/api/v1/stats/volume", () => HttpResponse.json({ type: "/p", title: "x", status: 500 }, { status: 500 })),
    );
    renderWithQuery(<ProgressRoute />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThan(0);
  });
});

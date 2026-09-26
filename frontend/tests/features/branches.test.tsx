import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import "../../src/i18n";
import type { components } from "../../src/lib/api/schema";
import { AdminScreen } from "../../src/features/admin/AdminScreen";
import { TargetRings } from "../../src/features/nutrition/TargetRings";
import { mondayOf } from "../../src/features/nutrition/queries";
import { buildHeatmap, withMovingAverage } from "../../src/features/progress/math";
import { createInitialState, playerReducer } from "../../src/features/session/playerMachine";
import { SessionPlayer } from "../../src/features/session/SessionPlayer";
import { closeDb, savePlayerState, loadActiveState } from "../../src/features/session/storage";
import { scheduler } from "../../src/features/session/scheduler";
import { uuidv7 } from "../../src/features/shared/uuid";
import { server } from "../../src/mocks/server";
import { makeNextSession } from "./session/fixtures";
import { renderRoute } from "./renderRoute";

afterEach(async () => {
  scheduler.stop();
  await closeDb();
  indexedDB.deleteDatabase("forja");
});

const target: components["schemas"]["NutritionTarget"] = {
  method: "mifflin_male", age_years: 30, bmr_kcal: 1, activity_factor: 1, tdee_kcal: 1,
  requested_goal: "lose", effective_goal: "lose", pace: "gentle", target_kcal: 2000,
  protein_g: null, fat_g: null, carbs_g: null, fiber_g: null, blocked: false, block: null, notices: [],
};

describe("ramas de pantallas", () => {
  it("TargetRings: sin kcal no dibuja nada; macros nulos se muestran como guion", () => {
    const { container, rerender } = render(<TargetRings target={{ ...target, target_kcal: null }} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<TargetRings target={target} />);
    expect(screen.getAllByText("–")).toHaveLength(3);
  });

  it("mondayOf devuelve el lunes de la semana", () => {
    expect(mondayOf(new Date(2026, 8, 27))).toBe("2026-09-21");
    expect(mondayOf(new Date(2026, 8, 21))).toBe("2026-09-21");
  });

  it("math: sin actividad y peso vacío", () => {
    expect(withMovingAverage([])).toEqual([]);
    const grid = buildHeatmap([{ date: "2026-09-21", session_count: 1, volume_kg: 0 }], 1, new Date(2026, 8, 24));
    expect(grid.flat().find((c) => c.date === "2026-09-21")?.level).toBe(4);
  });

  it("player: recorrer toda la sesión lleva a la pantalla de esfuerzo y guarda sin esfuerzo", async () => {
    const user = userEvent.setup();
    const s = createInitialState({ sessionUuid: uuidv7(), now: Date.now(), next: makeNextSession() });
    await savePlayerState(s);
    server.use(http.post("/api/v1/sync", () => HttpResponse.error()));
    const onFinished = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SessionPlayer onFinished={onFinished} onExit={vi.fn()} />
      </QueryClientProvider>,
    );
    for (let i = 0; i < 3; i += 1) {
      await user.click(await screen.findByRole("button", { name: "Serie hecha" }));
      if (i < 2) await user.click(await screen.findByRole("button", { name: "Saltar descanso" }));
    }
    expect(await screen.findByRole("heading", { name: "¿Qué esfuerzo has sentido?" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar y ver resumen" }));
    expect(onFinished).toHaveBeenCalled();
    await waitFor(async () => {
      expect(await loadActiveState()).toBeUndefined();
    });
  });

  it("player: ejercicio sin sugerencia ni rango de repeticiones y sesión ya completada", async () => {
    const next = makeNextSession();
    next.suggestions = [];
    const block = next.day?.blocks[0];
    const first = block?.exercises[0];
    if (first !== undefined) Object.assign(first, { rep_min: null, rep_max: null, target_rir: null, notes_es: "Controla la bajada", rest_s: 0 });
    let s = createInitialState({ sessionUuid: uuidv7(), now: Date.now(), next });
    await savePlayerState(s);
    const view = render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SessionPlayer onFinished={vi.fn()} onExit={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText(/Controla la bajada/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Serie hecha" }));
    // rest_s 0: sin descanso, se queda en la siguiente serie
    expect(await screen.findByText("Serie 2 de 2")).toBeInTheDocument();
    view.unmount();
    s = playerReducer(s, { type: "FINISH", now: Date.now(), perceivedEffort: null });
    await savePlayerState(s);
    const onFinished = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <SessionPlayer sessionUuid={s.sessionUuid} onFinished={onFinished} onExit={vi.fn()} />
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Resumen de la sesión" }));
    expect(onFinished).toHaveBeenCalledWith(s.sessionUuid);
  });

  it("admin: ejecuciones con errores, último acceso, búsqueda y sin ejecuciones", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({ id: "u", email: "a@x", display_name: "A", role: "admin", locale: "es", units: "metric", created_at: "", last_login_at: null, onboarding_completed: true, diet_available: true }),
      ),
      http.get("/api/v1/admin/settings", () =>
        HttpResponse.json({ registration_open: false, diet_feature_enabled: true, media_require_auth: false, dataset_commit: "c" }),
      ),
      http.get("/api/v1/admin/users", ({ request }) =>
        HttpResponse.json({
          items: new URL(request.url).searchParams.get("q") === "zz" ? [] : [
            { id: "u2", email: "b@x", display_name: "B", role: "admin", is_active: false, created_at: "", last_login_at: "2026-09-20T10:00:00Z" },
          ],
          next_cursor: null,
        }),
      ),
      http.get("/api/v1/admin/ingest/runs", () =>
        HttpResponse.json({
          items: [{ id: "r", status: "failed", dry_run: false, commit: "abcdef123", started_at: null, finished_at: null, triggered_by: null, counts: null, diff: null, errors: ["Checksum inválido"], warnings: [] }],
          next_cursor: null,
        }),
      ),
    );
    renderRoute(<AdminScreen />);
    expect(await screen.findByText("Checksum inválido")).toBeInTheDocument();
    expect(await screen.findByText("b@x")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Buscar por email o nombre"), "zz");
    await waitFor(() => {
      expect(screen.queryByText("b@x")).not.toBeInTheDocument();
    });
  });
});

import "fake-indexeddb/auto";

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { mondayOf } from "../../src/features/nutrition/queries";
import { closeDb } from "../../src/features/session/storage";
import { server } from "../../src/mocks/server";
import { NutritionRoute } from "../../src/routes/NutritionRoute";
import { renderRoute } from "./renderRoute";

const totals = { kcal: 500, protein_g: 30, fat_g: 15, carbs_g: 60, fiber_g: 8 };

function settings(overrides: Record<string, unknown> = {}, targetOverrides: Record<string, unknown> = {}): object {
  return {
    diet_enabled: true,
    goal: "lose",
    pace: "gentle",
    diet_type: "omnivore",
    meals_per_day: 3,
    allergens: [],
    excluded_food_ids: [],
    disliked_food_ids: [],
    pregnant: false,
    breastfeeding: false,
    feature_available: true,
    current_target: {
      id: "t1",
      calculated_at: "2026-09-22T19:00:00Z",
      target: {
        method: "mifflin_male",
        age_years: 30,
        bmr_kcal: 1700,
        activity_factor: 1.5,
        tdee_kcal: 2500,
        requested_goal: "lose",
        effective_goal: "lose",
        pace: "gentle",
        target_kcal: 2000,
        protein_g: 150,
        fat_g: 60,
        carbs_g: 220,
        fiber_g: 28,
        blocked: false,
        block: null,
        notices: [{ code: "health_disclaimer", message_es: "Cifras orientativas." }],
        ...targetOverrides,
      },
    },
    ...overrides,
  };
}

const plan = {
  id: "plan1",
  created_at: "2026-09-21T08:00:00Z",
  updated_at: "2026-09-21T08:00:00Z",
  plan: {
    nutrition_version: "1",
    foods_hash: "0".repeat(64),
    seed: 1,
    week_start: "2026-09-21",
    diet_type: "omnivore",
    meals_per_day: 3,
    target: (settings() as { current_target: { target: object } }).current_target.target,
    days: [
      {
        day_index: 0,
        date: "2026-09-21",
        meals: [
          {
            slot: "breakfast",
            items: [{ food_id: "avena", name_es: "Avena", grams: 60, units: null, nutrients: totals }],
            totals,
          },
        ],
        totals,
        deviation: { kcal: 12, protein: 1, fat: 1, carbs: 1 },
      },
    ],
    notices: [
      { code: "health_disclaimer", message_es: "x" },
      { code: "tolerance_not_met", message_es: "Fuera de tolerancia" },
    ],
  },
};

beforeEach(async () => {
  await closeDb();
  indexedDB.deleteDatabase("forja");
});

function useHandlers(opts: { settings?: object } = {}): void {
  server.use(
    http.get("/api/v1/nutrition/settings", () => HttpResponse.json(opts.settings ?? settings())),
    http.get("/api/v1/nutrition/plans", () =>
      HttpResponse.json({
        items: [{ id: "plan1", week_start: "2026-09-21", diet_type: "omnivore", meals_per_day: 3, target_kcal: 2000, created_at: "" }],
        next_cursor: null,
      }),
    ),
    http.get("/api/v1/nutrition/plans/:id", () => HttpResponse.json(plan)),
    http.get("/api/v1/nutrition/plans/:id/shopping-list", () =>
      HttpResponse.json({
        plan_id: "plan1",
        week_start: "2026-09-21",
        categories: [
          { category: "grains", label_es: "Cereales", items: [{ food_id: "avena", name_es: "Avena", total_grams: 420, units: null }] },
        ],
      }),
    ),
  );
}

describe("NutritionRoute", () => {
  it("muestra el aviso de seguridad, anillos neutros, plan y tolerancia como información", async () => {
    useHandlers();
    const { container } = renderRoute(<NutritionRoute />);

    expect(await screen.findByRole("note", { name: "Aviso de seguridad" })).toBeInTheDocument();
    const rings = await screen.findByRole("list", { name: "Objetivo diario" });
    expect(within(rings).getByRole("img", { name: /kcal: 2\.?000/ })).toBeInTheDocument();
    expect(within(rings).getByRole("img", { name: /Proteína: 150 g/ })).toBeInTheDocument();
    expect(within(rings).getByText("30 % de las calorías")).toBeInTheDocument();
    // Plan
    expect(await screen.findByText(/Avena · 60 g · 500 kcal/)).toBeInTheDocument();
    // tolerance_not_met: nota informativa, nunca alerta de error
    expect(screen.getByText(/Es informativo: no hace falta corregir nada/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    // Sin colores punitivos en los anillos: solo tokens neutros
    expect(container.innerHTML).not.toMatch(/color-error|color-success|color-warning/);
    const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(results.violations.map((v) => v.id)).toEqual([]);
  });

  it("lista de la compra marcable y persistente en IndexedDB", async () => {
    useHandlers();
    const user = userEvent.setup();
    const first = renderRoute(<NutritionRoute />);
    const box = await screen.findByRole("checkbox", { name: "Marcar Avena como comprado" });
    await user.click(box);
    expect(box).toBeChecked();
    first.unmount();
    renderRoute(<NutritionRoute />);
    await waitFor(async () => {
      expect(await screen.findByRole("checkbox", { name: "Marcar Avena como comprado" })).toBeChecked();
    });
  });

  it("intercambia un alimento automáticamente", async () => {
    useHandlers();
    let body: unknown = null;
    server.use(
      http.post("/api/v1/nutrition/plans/:id/swap", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(plan);
      }),
    );
    const user = userEvent.setup();
    renderRoute(<NutritionRoute />);
    await user.click(await screen.findByRole("button", { name: "Cambiar Avena" }));
    await user.click(screen.getByRole("button", { name: "Elegir automáticamente" }));
    await waitFor(() => {
      expect(body).toEqual({ day_index: 0, meal: "breakfast", food_id: "avena", replacement_food_id: null });
    });
  });

  it("genera el plan de la semana actual", async () => {
    useHandlers();
    let weekStart = "";
    server.use(
      http.post("/api/v1/nutrition/plans", async ({ request }) => {
        weekStart = ((await request.json()) as { week_start: string }).week_start;
        return HttpResponse.json(plan, { status: 201 });
      }),
    );
    renderRoute(<NutritionRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Generar plan de esta semana" }));
    await waitFor(() => {
      expect(weekStart).toBe(mondayOf(new Date()));
    });
  });

  it("objetivo bloqueado: mensaje informativo, sin botón de generar plan", async () => {
    useHandlers({
      settings: settings({}, {
        blocked: true,
        target_kcal: null,
        block: { reason_code: "pregnant", message_es: "No generamos planes durante el embarazo." },
      }),
    });
    renderRoute(<NutritionRoute />);
    expect(await screen.findByText(/No generamos planes durante el embarazo/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generar plan de esta semana" })).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("dieta desactivada: ofrece activarla; función no disponible: lo indica", async () => {
    useHandlers({ settings: settings({ diet_enabled: false }) });
    let saved: unknown = null;
    server.use(
      http.put("/api/v1/nutrition/settings", async ({ request }) => {
        saved = await request.json();
        return HttpResponse.json(settings());
      }),
    );
    const first = renderRoute(<NutritionRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Activar nutrición" }));
    await waitFor(() => {
      expect(saved).toMatchObject({ diet_enabled: true });
    });
    first.unmount();

    useHandlers({ settings: settings({ feature_available: false }) });
    renderRoute(<NutritionRoute />);
    expect(await screen.findByText(/no está disponible en este servidor/)).toBeInTheDocument();
  });

  it("guarda ajustes y recalcula el objetivo", async () => {
    useHandlers();
    let saved: { allergens?: string[] } = {};
    let recalculated = false;
    server.use(
      http.put("/api/v1/nutrition/settings", async ({ request }) => {
        saved = (await request.json()) as { allergens?: string[] };
        return HttpResponse.json(settings());
      }),
      http.post("/api/v1/nutrition/targets/calculate", () => {
        recalculated = true;
        return HttpResponse.json((settings() as { current_target: object }).current_target);
      }),
    );
    const user = userEvent.setup();
    renderRoute(<NutritionRoute />);
    await user.click(await screen.findByRole("checkbox", { name: "Cacahuete" }));
    await user.click(screen.getByRole("button", { name: "Guardar ajustes" }));
    await waitFor(() => {
      expect(saved.allergens).toEqual(["peanuts"]);
    });
    await user.click(screen.getByRole("button", { name: "Recalcular objetivo" }));
    await waitFor(() => {
      expect(recalculated).toBe(true);
    });
  });

  it("error de carga", async () => {
    server.use(
      http.get("/api/v1/nutrition/settings", () => HttpResponse.json({ type: "/p", title: "x", status: 500 }, { status: 500 })),
    );
    renderRoute(<NutritionRoute />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No se ha podido cargar la nutrición.");
  });
});

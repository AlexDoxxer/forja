import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import "../../src/i18n";
import { first } from "../../src/features/shared/enums";
import { GeneratorScreen } from "../../src/features/generator/GeneratorScreen";
import { formatPrescription, randomSeed } from "../../src/features/shared/format";
import { server } from "../../src/mocks/server";
import { expectNoAxeViolations } from "../axe";
import { previewFixture, exerciseFixture } from "../fixtures/catalog";
import { installRadixPolyfills } from "../radixPolyfills";
import { renderWithRouter } from "../routes/renderWithRouter";

interface Calls {
  preview: unknown[];
  regenerateDay: unknown[];
  swap: unknown[];
  save: unknown[];
}

function mockApi(sex: "male" | "female" | "unspecified"): Calls {
  const calls: Calls = { preview: [], regenerateDay: [], swap: [], save: [] };
  server.use(
    http.get("/api/v1/profile", () =>
      HttpResponse.json({
        display_name: "Lucía",
        locale: "es",
        units: "metric",
        sex,
        birth_date: null,
        height_cm: null,
        experience: "beginner",
        activity_level: "moderate",
        equipment: { preset: "home_dumbbells", items: [] },
        limitations: { avoid_muscles: ["shoulders"], avoid_patterns: [], notes: null },
        diet_enabled: false,
        preferences: { theme: "dark", sounds: true, vibration: true, default_rest_s: null },
        parq_flagged: true,
        parq_completed_at: null,
        onboarding_completed: true,
        updated_at: "2026-09-26T10:00:00Z",
      }),
    ),
    http.post("/api/v1/generator/preview", async ({ request }) => {
      calls.preview.push(await request.json());
      return HttpResponse.json(previewFixture());
    }),
    http.post("/api/v1/generator/preview/regenerate-day", async ({ request }) => {
      calls.regenerateDay.push(await request.json());
      return HttpResponse.json(previewFixture());
    }),
    http.post("/api/v1/generator/preview/swap", async ({ request }) => {
      calls.swap.push(await request.json());
      const preview = previewFixture();
      preview.exercises.push(exerciseFixture("0050", "sentadilla goblet"));
      return HttpResponse.json(preview);
    }),
    http.post("/api/v1/programs", async ({ request }) => {
      calls.save.push(await request.json());
      return HttpResponse.json({}, { status: 201 });
    }),
  );
  return calls;
}

async function goToPreview(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(await screen.findByRole("button", { name: /Fuerza/ }));
  await user.click(screen.getByRole("button", { name: "Continuar" }));
  await user.click(screen.getByRole("button", { name: "Continuar" }));
  await user.click(screen.getByRole("button", { name: "Continuar" }));
  await user.click(screen.getByRole("button", { name: "Continuar" }));
  await user.click(screen.getByRole("button", { name: "Generar vista previa" }));
}

describe("GeneratorScreen", () => {
  beforeEach(installRadixPolyfills);

  it("recorre el wizard con el sexo preseleccionado y explicado, y envía la entrada al motor", async () => {
    const user = userEvent.setup();
    const calls = mockApi("female");
    renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });

    // Paso 1: objetivos con explicación.
    expect(await screen.findByText("Cargas altas, pocas repeticiones y descansos largos.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Fuerza/ }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    // Paso 2: días; los días preferidos deben coincidir con los días por semana.
    expect(screen.getByText(/Paso 2 de 6/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Lun" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Elige exactamente 3 días preferidos o ninguno.");
    await user.click(screen.getByRole("button", { name: "Lun" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    // Paso 3: sexo del perfil, con explicación de qué ajusta y qué nunca hace.
    expect(screen.getByText("Hemos preseleccionado el sexo de tu perfil.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mujer" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Preselecciona el énfasis «Piernas y glúteos»/)).toBeInTheDocument();
    expect(screen.getByText("El sexo nunca excluye ejercicios ni grupos musculares, ni limita cargas.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Hombre" }));
    expect(screen.getByText("Has cambiado el sexo respecto a tu perfil (solo para esta rutina).")).toBeInTheDocument();
    expect(screen.getByText(/Preselecciona el énfasis «Equilibrado» y no cambia descansos/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mujer" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    // Paso 4: nivel, duración (deslizador) y equipamiento del perfil.
    expect(screen.getByText(/Tu PAR-Q marcó una alerta/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Principiante" })).toHaveAttribute("aria-pressed", "true");
    const duration = screen.getByRole("slider", { name: /Duración por sesión/ });
    duration.focus();
    await user.keyboard("{ArrowRight}");
    expect(duration).toHaveAttribute("aria-valuenow", "65");
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    // Paso 5: énfasis preseleccionado por el sexo (editable) y limitaciones del perfil.
    expect(screen.getByRole("button", { name: "Piernas y glúteos" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Hombros" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Generar vista previa" }));

    expect(await screen.findByText("Hemos elegido cuerpo completo porque entrenas 3 días.")).toBeInTheDocument();
    expect(calls.preview).toHaveLength(1);
    expect(calls.preview[0]).toMatchObject({
      goal: "strength",
      days_per_week: 3,
      sex: "female",
      experience: "beginner",
      session_minutes: 65,
      equipment: { preset: "home_dumbbells", items: [] },
      emphasis: "lower_glutes",
      avoid_muscles: ["shoulders"],
      preferred_days: [],
      weeks: 5,
    });
  });

  it("la vista previa muestra GIFs con atribución, prescripción, volumen, motivos y avisos", async () => {
    const user = userEvent.setup();
    mockApi("male");
    const { container } = renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });
    await goToPreview(user);

    expect(await screen.findByRole("heading", { name: "Por qué esta rutina" })).toBeInTheDocument();
    expect(screen.getByText("El volumen de espalda queda por debajo del rango.")).toBeInTheDocument();
    expect(screen.getByText("sentadilla con barra")).toBeInTheDocument();
    expect(screen.getByText(/3×8-12 · descanso 90 s · RIR 2/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "© Gym visual" }).length).toBeGreaterThan(0);
    expect(screen.getByText("55 min", { exact: false })).toBeInTheDocument();

    const table = screen.getByRole("table", { name: /Series efectivas planificadas/ });
    expect(within(table).getByRole("row", { name: /Cuádriceps 9 8–14/ })).toBeInTheDocument();
    // El gráfico de Recharts se carga bajo demanda (chunk diferido).
    await waitFor(() => {
      expect(container.querySelector(".recharts-responsive-container")).not.toBeNull();
    });

    await user.click(screen.getByRole("tab", { name: "Cuerpo completo B" }));
    expect(await screen.findByText("peso muerto rumano")).toBeVisible();
    await expectNoAxeViolations(container);
  });

  it("regenera un día, cambia un ejercicio con alternativas y guarda y activa", async () => {
    const user = userEvent.setup();
    const calls = mockApi("unspecified");
    renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });
    await goToPreview(user);
    await screen.findByText("sentadilla con barra");

    await user.click(screen.getByRole("button", { name: "Regenerar este día" }));
    await waitFor(() => {
      expect(calls.regenerateDay).toHaveLength(1);
    });
    expect(calls.regenerateDay[0]).toMatchObject({ day_index: 0, seed: null });

    await user.click(first(screen.getAllByRole("button", { name: "Cambiar ejercicio" })));
    const sheet = await screen.findByRole("dialog", { name: "Cambiar ejercicio" });
    await user.click(within(sheet).getByRole("button", { name: "Usar peso muerto rumano" }));
    await waitFor(() => {
      expect(calls.swap).toHaveLength(1);
    });
    expect(calls.swap[0]).toMatchObject({
      address: { week_index: 0, day_index: 0, block_order: 0, exercise_order: 0 },
      replacement_id: "0044",
      exclude_ids: ["0043"],
      apply_to_all_weeks: true,
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Regenerar con otra semilla" }));
    await waitFor(() => {
      expect(calls.preview).toHaveLength(2);
    });
    expect(typeof (calls.preview[1] as { seed: unknown }).seed).toBe("number");

    await user.clear(screen.getByLabelText("Nombre de la rutina"));
    await user.type(screen.getByLabelText("Nombre de la rutina"), "Mi plan");
    await user.click(screen.getByRole("button", { name: "Guardar y activar" }));
    await waitFor(() => {
      expect(calls.save).toHaveLength(1);
    });
    expect(calls.save[0]).toMatchObject({ source: "generated", name: "Mi plan", activate: true });
    expect(await screen.findByText("ruta:/rutinas")).toBeInTheDocument();
  });

  it("guarda sin activar y muestra errores del motor", async () => {
    const user = userEvent.setup();
    const calls = mockApi("unspecified");
    renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });
    await goToPreview(user);
    await screen.findByText("sentadilla con barra");

    server.use(http.post("/api/v1/programs", () => HttpResponse.json({ title: "x", type: "x", status: 500, code: "service_unavailable" }, { status: 500 })));
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("No se ha podido guardar la rutina.")).toBeInTheDocument();
    expect(calls.save).toHaveLength(0);
  });

  it("informa si el motor rechaza la entrada", async () => {
    const user = userEvent.setup();
    mockApi("unspecified");
    server.use(http.post("/api/v1/generator/preview", () => HttpResponse.json({ title: "Datos no válidos", type: "x", status: 422, code: "validation_error" }, { status: 422 })));
    renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });
    await goToPreview(user);
    expect(await screen.findByText(/No se ha podido generar la rutina/)).toBeInTheDocument();
  });

  it("exige elegir equipamiento con el preset personalizado", async () => {
    const user = userEvent.setup();
    mockApi("unspecified");
    renderWithRouter(GeneratorScreen, { path: "/rutinas/nueva" });
    await user.click(await screen.findByRole("button", { name: /Fuerza/ }));
    for (let i = 0; i < 3; i += 1) await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Personalizado" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Marca al menos un tipo de equipamiento.");
    await user.click(screen.getByRole("button", { name: "Kettlebell" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByText(/Paso 5 de 6/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Atrás" }));
    expect(screen.getByText(/Paso 4 de 6/)).toBeInTheDocument();
  });
});

describe("format helpers", () => {
  it("formatea repeticiones, duración y por lado", () => {
    expect(formatPrescription({ sets: 3, rep_min: 8, rep_max: 8, duration_s: null, per_side: false }, "por lado")).toBe("3×8");
    expect(formatPrescription({ sets: 2, rep_min: null, rep_max: null, duration_s: 45, per_side: true }, "por lado")).toBe("2×45 s por lado");
    expect(formatPrescription({ sets: 4, rep_min: 10, rep_max: null, duration_s: null, per_side: false }, "por lado")).toBe("4×10");
  });

  it("genera semillas enteras seguras en JavaScript", () => {
    for (let i = 0; i < 50; i += 1) {
      const seed = randomSeed();
      expect(Number.isSafeInteger(seed)).toBe(true);
      expect(seed).toBeGreaterThanOrEqual(0);
    }
  });
});

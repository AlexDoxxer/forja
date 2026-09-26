import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { OnboardingScreen } from "../../src/features/onboarding/OnboardingScreen";
import { server } from "../../src/mocks/server";
import { renderWithRouter } from "../routes/renderWithRouter";

interface Captured {
  register: unknown;
  profile: unknown;
  parq: unknown;
  metric: unknown;
}

function captureRequests(parqResult: { flagged: boolean }): Captured {
  const captured: Captured = { register: null, profile: null, parq: null, metric: null };
  const profile = {
    display_name: "Lucía",
    locale: "es",
    units: "metric",
    sex: "unspecified",
    birth_date: null,
    height_cm: null,
    experience: "beginner",
    activity_level: "moderate",
    equipment: { preset: "full_gym", items: [] },
    limitations: { avoid_muscles: [], avoid_patterns: [], notes: null },
    diet_enabled: false,
    preferences: { theme: "dark", sounds: true, vibration: true, default_rest_s: null },
    parq_flagged: false,
    parq_completed_at: null,
    onboarding_completed: false,
    updated_at: "2026-09-26T10:00:00Z",
  };
  server.use(
    http.post("/api/v1/auth/register", async ({ request }) => {
      captured.register = await request.json();
      return HttpResponse.json(
        {
          id: "0192f08a-3b4c-7d5e-8f60-112233445566",
          email: "lucia@example.org",
          display_name: "Lucía",
          role: "user",
          locale: "es",
          units: "metric",
          created_at: "2026-09-26T10:00:00Z",
          last_login_at: null,
          onboarding_completed: false,
          diet_available: false,
        },
        { status: 201 },
      );
    }),
    http.get("/api/v1/profile", () => HttpResponse.json(profile)),
    http.put("/api/v1/profile", async ({ request }) => {
      captured.profile = await request.json();
      return HttpResponse.json(profile);
    }),
    http.put("/api/v1/profile/parq", async ({ request }) => {
      captured.parq = await request.json();
      return HttpResponse.json({
        parq_flagged: parqResult.flagged,
        experience_forced: parqResult.flagged,
        recommendation_es: parqResult.flagged ? "Consulta con un profesional sanitario antes de empezar." : null,
        profile,
      });
    }),
    http.post("/api/v1/body-metrics", async ({ request }) => {
      captured.metric = await request.json();
      return HttpResponse.json({}, { status: 201 });
    }),
  );
  return captured;
}

async function completeAccount(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText("Correo electrónico"), "lucia@example.org");
  await user.type(screen.getByLabelText("Contraseña"), "brasa-y-yunque-2026");
  await user.type(screen.getByLabelText("Nombre para mostrar"), "Lucía");
  await user.click(screen.getByRole("button", { name: "Continuar" }));
}

describe("OnboardingScreen", () => {
  it("valida la cuenta antes de avanzar", async () => {
    const user = userEvent.setup();
    renderWithRouter(OnboardingScreen, { path: "/onboarding" });
    await user.click(await screen.findByRole("button", { name: "Continuar" }));
    expect(screen.getByText("Introduce un correo válido.")).toBeInTheDocument();
    expect(screen.getByText("La contraseña debe tener al menos 10 caracteres.")).toBeInTheDocument();
    expect(screen.getByText("Indica un nombre.")).toBeInTheDocument();
    expect(screen.getByText(/Paso 1 de 4/)).toBeInTheDocument();
  });

  it("muestra el error de correo repetido (409)", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/register", () =>
        HttpResponse.json({ type: "/problems/conflict", title: "Conflicto", status: 409, code: "email_taken" }, { status: 409 }),
      ),
    );
    renderWithRouter(OnboardingScreen, { path: "/onboarding" });
    await screen.findByLabelText("Correo electrónico");
    await completeAccount(user);
    expect(await screen.findByText("Ya existe una cuenta con ese correo.")).toBeInTheDocument();
  });

  it("completa los 4 pasos con PAR-Q sin marcar y guarda perfil y PAR-Q en orden", async () => {
    const user = userEvent.setup();
    const captured = captureRequests({ flagged: false });
    renderWithRouter(OnboardingScreen, { path: "/onboarding" });
    await screen.findByLabelText("Correo electrónico");

    await completeAccount(user);
    expect(await screen.findByText(/Paso 2 de 4/)).toBeInTheDocument();
    expect(captured.register).toMatchObject({ email: "lucia@example.org", display_name: "Lucía" });

    await user.click(screen.getByRole("button", { name: "Mujer" }));
    await user.type(screen.getByLabelText("Altura (cm)"), "166");
    await user.type(screen.getByLabelText("Peso (kg)"), "60");
    await user.click(screen.getByRole("button", { name: "Intermedio" }));
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    expect(await screen.findByText(/Paso 3 de 4/)).toBeInTheDocument();
    const next = screen.getByRole("button", { name: "Continuar" });
    expect(next).toBeDisabled();
    for (const group of screen.getAllByRole("radiogroup")) {
      await user.click(within(group).getByLabelText("No"));
    }
    expect(screen.queryByText(/Has marcado al menos un/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    expect(await screen.findByText(/Paso 4 de 4/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Personalizado" }));
    await user.click(screen.getByRole("button", { name: "Terminar" }));
    expect(await screen.findByText("Marca al menos un tipo de equipamiento.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mancuernas" }));
    await user.click(screen.getByRole("button", { name: "Glúteos" }));
    await user.click(screen.getByRole("button", { name: "Terminar" }));

    expect(await screen.findByRole("heading", { name: "Todo listo" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear mi rutina" })).toHaveAttribute("href", "/rutinas/nueva");
    expect(captured.profile).toMatchObject({
      sex: "female",
      height_cm: 166,
      experience: "intermediate",
      equipment: { preset: "custom", items: ["dumbbell"] },
      limitations: { avoid_muscles: ["glutes"] },
    });
    expect(captured.parq).toMatchObject({ answers: { heart_condition: false, other_reason: false } });
    await waitFor(() => {
      expect(captured.metric).toMatchObject({ weight_kg: 60 });
    });
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("con PAR-Q marcado avisa, no bloquea y muestra la recomendación", async () => {
    const user = userEvent.setup();
    const captured = captureRequests({ flagged: true });
    renderWithRouter(OnboardingScreen, { path: "/onboarding" });
    await screen.findByLabelText("Correo electrónico");
    await completeAccount(user);
    await user.click(await screen.findByRole("button", { name: "Continuar" }));

    const groups = screen.getAllByRole("radiogroup");
    for (const [index, group] of groups.entries()) {
      await user.click(within(group).getByLabelText(index === 1 ? "Sí" : "No"));
    }
    expect(screen.getByRole("status")).toHaveTextContent("ajustaremos tu nivel a principiante");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Terminar" }));

    expect(await screen.findByText("Consulta con un profesional sanitario antes de empezar.")).toBeInTheDocument();
    expect(captured.parq).toMatchObject({ answers: { chest_pain_activity: true } });
  });

  it("permite volver atrás y muestra un error si falla el guardado del perfil", async () => {
    const user = userEvent.setup();
    captureRequests({ flagged: false });
    server.use(http.put("/api/v1/profile", () => HttpResponse.json({ title: "x", status: 500, type: "x", code: "service_unavailable" }, { status: 500 })));
    renderWithRouter(OnboardingScreen, { path: "/onboarding" });
    await screen.findByLabelText("Correo electrónico");
    await completeAccount(user);
    await user.click(await screen.findByRole("button", { name: "Atrás" }));
    expect(screen.getByLabelText("Correo electrónico")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(await screen.findByRole("button", { name: "Continuar" }));
    for (const group of screen.getAllByRole("radiogroup")) {
      await user.click(within(group).getByLabelText("No"));
    }
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Terminar" }));
    expect(await screen.findByText("No se ha podido guardar tu perfil. Inténtalo de nuevo.")).toBeInTheDocument();
  });
});

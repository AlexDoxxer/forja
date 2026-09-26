import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { reloadToHome } from "../../src/features/profile/navigation";
import { i18next } from "../../src/i18n";
import { collectActiveProgramMedia, offlineSupported, requestPrecache } from "../../src/sw/library";
import { ProfileRoute } from "../../src/routes/ProfileRoute";
import { server } from "../../src/mocks/server";
import { renderRoute } from "../features/renderRoute";

vi.mock("../../src/features/profile/navigation", () => ({ reloadToHome: vi.fn() }));
vi.mock("../../src/sw/library", () => ({
  offlineSupported: vi.fn(() => false),
  collectActiveProgramMedia: vi.fn(),
  requestPrecache: vi.fn(),
}));

const profile = {
  display_name: "Ana",
  locale: "es",
  units: "metric",
  sex: "female",
  birth_date: "1990-01-01",
  height_cm: 165,
  experience: "beginner",
  activity_level: "light",
  equipment: { preset: "full_gym", items: [] },
  limitations: { avoid_muscles: [], avoid_patterns: [], notes: null },
  diet_enabled: false,
  preferences: { theme: "dark", sounds: true, vibration: true, default_rest_s: 90 },
  parq_flagged: false,
  parq_completed_at: null,
  onboarding_completed: true,
  updated_at: "2026-09-20T10:00:00Z",
};

const me = (role: string, diet: boolean): object => ({
  id: "u1", email: "ana@example.com", display_name: "Ana", role, locale: "es", units: "metric",
  created_at: "", last_login_at: null, onboarding_completed: true, diet_available: diet,
});

afterEach(async () => {
  await i18next.changeLanguage("es");
  vi.restoreAllMocks();
  document.documentElement.dataset["theme"] = "dark";
});

function useBase(role = "user", diet = false): void {
  server.use(
    http.get("/api/v1/profile", () => HttpResponse.json(profile)),
    http.get("/api/v1/auth/me", () => HttpResponse.json(me(role, diet))),
    http.get("/api/v1/auth/sessions", () =>
      HttpResponse.json({
        items: [
          { id: "s1", created_at: "", last_seen_at: "2026-09-25T10:00:00Z", expires_at: "", user_agent: "Firefox", current: true },
          { id: "s2", created_at: "", last_seen_at: "2026-09-24T10:00:00Z", expires_at: "", user_agent: "Safari iPhone", current: false },
        ],
      }),
    ),
  );
}

describe("ProfileRoute", () => {
  it("muestra los créditos: commit del dataset, nº de ejercicios y atribución de medios", async () => {
    useBase();
    renderRoute(<ProfileRoute />);

    expect(await screen.findByText("7455efae41b330c265e7cd4b78dfa848e7ce5ebd")).toBeInTheDocument();
    expect(screen.getByText("1324")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "© Gym visual" })).toHaveAttribute("href", "https://gymvisual.com/");
    expect(
      screen.getByText("Forja no sustituye el consejo de profesionales sanitarios ni de entrenamiento."),
    ).toBeInTheDocument();
    expect(screen.getByText("MIT — hasaneyldrm/exercises-dataset")).toBeInTheDocument();
  });

  it("guarda ajustes: idioma y tema se aplican al instante", async () => {
    useBase();
    let body: { locale?: string; preferences?: { theme?: string; default_rest_s?: number } } = {};
    server.use(
      http.put("/api/v1/profile", async ({ request }) => {
        body = (await request.json()) as typeof body;
        return HttpResponse.json({ ...profile, ...body });
      }),
    );
    const user = userEvent.setup();
    renderRoute(<ProfileRoute />);
    await user.selectOptions(await screen.findByLabelText("Idioma"), "en");
    await user.selectOptions(screen.getByLabelText("Tema"), "light");
    const rest = screen.getByLabelText("Descanso por defecto (segundos)");
    await user.clear(rest);
    await user.type(rest, "120");
    await user.click(screen.getByRole("button", { name: "Guardar ajustes" }));
    await waitFor(() => {
      expect(body.locale).toBe("en");
    });
    expect(body.preferences).toMatchObject({ theme: "light", default_rest_s: 120 });
    await waitFor(() => {
      expect(document.documentElement.dataset["theme"]).toBe("light");
      expect(i18next.language).toBe("en");
    });
  });

  it("enlaces a Nutrición y Admin según el rol y la dieta", async () => {
    useBase("admin", true);
    renderRoute(<ProfileRoute />);
    expect(await screen.findByRole("link", { name: "Nutrición" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Administración" })).toBeInTheDocument();
  });

  it("sin permisos no aparecen los enlaces", async () => {
    useBase("user", false);
    renderRoute(<ProfileRoute />);
    await screen.findByText("Créditos y licencias");
    expect(screen.queryByRole("link", { name: "Administración" })).not.toBeInTheDocument();
  });

  it("sesiones activas: cerrar otra sesión", async () => {
    useBase();
    let revoked = "";
    server.use(
      http.delete("/api/v1/auth/sessions/:id", ({ params }) => {
        revoked = String(params["id"]);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderRoute(<ProfileRoute />);
    expect(await screen.findByText("Este dispositivo")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión de Safari iPhone" }));
    await waitFor(() => {
      expect(revoked).toBe("s2");
    });
  });

  it("exporta los datos como archivo JSON", async () => {
    useBase();
    server.use(http.get("/api/v1/me/export", () => HttpResponse.json({ format: "forja-export" })));
    const createUrl = vi.fn().mockReturnValue("blob:x");
    Object.defineProperty(URL, "createObjectURL", { value: createUrl, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderRoute(<ProfileRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Exportar mis datos" }));
    await waitFor(() => {
      expect(click).toHaveBeenCalled();
    });
    expect(createUrl).toHaveBeenCalled();
  });

  it("importa un archivo válido y rechaza uno inválido", async () => {
    useBase();
    server.use(
      http.post("/api/v1/me/import", () =>
        HttpResponse.json({
          created: { programs: 1, sessions: 2, sets: 30, body_metrics: 0, favorites: 0, meal_plans: 0 },
          skipped: { programs: 0, sessions: 0, sets: 0, body_metrics: 0, favorites: 0, meal_plans: 0 },
          warnings: [],
        }),
      ),
    );
    const user = userEvent.setup({ applyAccept: false });
    renderRoute(<ProfileRoute />);
    const input = await screen.findByLabelText("Archivo de exportación de Forja");
    await user.upload(input, new File(["no es json"], "x.json", { type: "application/json" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no es una exportación válida");
    await user.upload(input, new File([JSON.stringify({ format: "forja-export" })], "ok.json", { type: "application/json" }));
    expect(await screen.findByText("Importado: 2 sesiones, 1 programas, 30 series.")).toBeInTheDocument();
  });

  it("eliminar cuenta exige contraseña y confirma", async () => {
    useBase();
    let sent: unknown = null;
    server.use(
      http.delete("/api/v1/me", async ({ request }) => {
        sent = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderRoute(<ProfileRoute />);
    await user.click(await screen.findByRole("button", { name: "Eliminar mi cuenta" }));
    const confirm = screen.getByRole("button", { name: "Eliminar definitivamente" });
    expect(confirm).toBeDisabled();
    await user.type(screen.getByLabelText("Contraseña para confirmar"), "secreto123");
    await user.click(confirm);
    await waitFor(() => {
      expect(sent).toEqual({ password: "secreto123" });
    });
    await waitFor(() => {
      expect(reloadToHome).toHaveBeenCalled();
    });
  });

  it("descargar biblioteca: pide al service worker precachear los medios del programa activo", async () => {
    useBase();
    vi.mocked(offlineSupported).mockReturnValue(true);
    vi.mocked(collectActiveProgramMedia).mockResolvedValue(["/media/a.jpg", "/media/a.gif"]);
    const precache = vi.mocked(requestPrecache).mockResolvedValue(2);
    renderRoute(<ProfileRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Descargar biblioteca para uso offline" }));
    expect(await screen.findByText("Listo: 2 medios guardados para uso sin conexión.")).toBeInTheDocument();
    expect(precache).toHaveBeenCalledWith(["/media/a.jpg", "/media/a.gif"]);
  });
});

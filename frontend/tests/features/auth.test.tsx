import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { redirectTarget, UnauthenticatedError } from "../../src/features/auth/session";
import { server } from "../../src/mocks/server";

const user = (completed: boolean): object => ({
  id: "u1", email: "a@x.com", display_name: "A", role: "user", locale: "es", units: "metric",
  created_at: "", last_login_at: null, onboarding_completed: completed, diet_available: false,
});
const unauth = (): Response =>
  HttpResponse.json({ type: "/p", title: "No autenticado", status: 401, code: "unauthenticated" }, { status: 401 });

/** Módulos de la app nuevos en cada caso: el router y la caché no comparten estado entre pruebas. */
async function loadApp(path: string): Promise<{
  App: typeof import("../../src/App").App;
  router: typeof import("../../src/routes/router").router;
}> {
  vi.resetModules();
  const { App } = await import("../../src/App");
  const { router } = await import("../../src/routes/router");
  router.history.replace(path);
  return { App, router };
}

describe("redirectTarget", () => {
  const ok = { isLoading: false, error: null, data: user(true) as never };
  it("decide el destino según sesión y onboarding", () => {
    expect(redirectTarget("/", { isLoading: true, error: null, data: undefined })).toBeNull();
    expect(redirectTarget("/", { isLoading: false, error: new UnauthenticatedError(), data: undefined })).toBe("/login");
    expect(redirectTarget("/login", { isLoading: false, error: new UnauthenticatedError(), data: undefined })).toBeNull();
    expect(redirectTarget("/onboarding", { isLoading: false, error: new UnauthenticatedError(), data: undefined })).toBeNull();
    expect(redirectTarget("/", { ...ok, data: user(false) as never })).toBe("/onboarding");
    expect(redirectTarget("/onboarding", { ...ok, data: user(false) as never })).toBeNull();
    expect(redirectTarget("/login", ok)).toBe("/");
    expect(redirectTarget("/progreso", ok)).toBeNull();
  });
});

describe("guarda de sesión", () => {

  it("sin sesión redirige a /login y permite iniciar sesión", async () => {
    server.use(http.get("/api/v1/auth/me", () => unauth()));
    const { App, router } = await loadApp("/progreso");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(screen.queryByRole("navigation", { name: "Forja" })).not.toBeInTheDocument();

    server.use(
      http.post("/api/v1/auth/login", () => HttpResponse.json({}, { status: 401 })),
      http.get("/api/v1/auth/me", () => unauth()),
    );
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Correo electrónico"), "a@x.com");
    await u.type(screen.getByLabelText("Contraseña"), "mala");
    await u.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Correo o contraseña incorrectos.")).toBeInTheDocument();

    server.use(
      http.post("/api/v1/auth/login", () => HttpResponse.json(user(true))),
      http.get("/api/v1/auth/me", () => HttpResponse.json(user(true))),
    );
    await u.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    expect(await screen.findByRole("navigation", { name: "Forja" })).toBeInTheDocument();
  });

  it("con sesión pero sin onboarding completado redirige a /onboarding", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(user(false))));
    const { App, router } = await loadApp("/");
    render(<App />);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/onboarding");
    });
  });

  it("un error de servidor no expulsa: ofrece reintentar", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json({ type: "/p", title: "x", status: 500 }, { status: 500 })));
    const { App, router } = await loadApp("/");
    render(<App />);
    expect(await screen.findByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });

  it("cerrar sesión desde Perfil lleva a /login", async () => {
    server.use(
      http.get("/api/v1/auth/me", () => HttpResponse.json(user(true))),
      http.post("/api/v1/auth/logout", () => {
        server.use(http.get("/api/v1/auth/me", () => unauth()));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { App, router } = await loadApp("/perfil");
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Cerrar sesión" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
    });
  });
});

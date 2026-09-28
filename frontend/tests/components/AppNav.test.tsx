import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { AppNav } from "../../src/components/AppNav";
import { server } from "../../src/mocks/server";
import { renderRoute } from "../features/renderRoute";

const me = (role: string, diet: boolean): object => ({
  id: "u1",
  email: "a@x.com",
  display_name: "A",
  role,
  locale: "es",
  units: "metric",
  created_at: "",
  last_login_at: null,
  onboarding_completed: true,
  diet_available: diet,
});

describe("AppNav", () => {
  it("muestra los enlaces base sin Nutrición ni Admin para una persona sin esos permisos", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(me("user", false))));
    renderRoute(<AppNav />, "/", ["/biblioteca", "/progreso"]);

    expect(await screen.findByRole("link", { name: "Hoy" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rutinas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Biblioteca" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Progreso" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Perfil" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Nutrición" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
  });

  it("añade Nutrición y Admin cuando la sesión los tiene disponibles", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(me("admin", true))));
    renderRoute(<AppNav />, "/", ["/biblioteca", "/progreso"]);

    await waitFor(async () => {
      expect(await screen.findByRole("link", { name: "Nutrición" })).toHaveAttribute("href", "/nutricion");
    });
    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
  });
});

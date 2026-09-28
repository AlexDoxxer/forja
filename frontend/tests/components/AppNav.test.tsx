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

  it("agrupa los enlaces en «Entrenar» y «Cuenta» (subtítulos del rail de escritorio)", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(me("user", false))));
    renderRoute(<AppNav />, "/", ["/biblioteca", "/progreso"]);

    expect(await screen.findByText("Entrenar")).toBeInTheDocument();
    expect(screen.getByText("Cuenta")).toBeInTheDocument();
  });

  it("marca el enlace activo con `aria-current` y una píldora; con movimiento reducido, sin animación", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(me("user", false))));
    const original = window.matchMedia.bind(window);
    window.matchMedia = ((query: string) => ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
    })) as unknown as typeof window.matchMedia;

    renderRoute(<AppNav />, "/", ["/biblioteca", "/progreso"]);
    const active = await screen.findByRole("link", { name: "Hoy" });
    expect(active).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Rutinas" })).not.toHaveAttribute("aria-current");

    window.matchMedia = original;
  });
});

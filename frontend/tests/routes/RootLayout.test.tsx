import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { RootLayout } from "../../src/routes/RootLayout";
import styles from "../../src/routes/RootLayout.module.css";

function buildRouter(path: string): ReturnType<typeof createRouter> {
  const root = createRootRoute({ component: RootLayout });
  const home = createRoute({ getParentRoute: () => root, path: "/", component: () => <p>Pantalla Hoy</p> });
  const programs = createRoute({ getParentRoute: () => root, path: "/rutinas", component: () => <p>Pantalla Rutinas</p> });
  const login = createRoute({ getParentRoute: () => root, path: "/login", component: () => <p>Pantalla Login</p> });
  return createRouter({
    routeTree: root.addChildren([home, programs, login]),
    history: createMemoryHistory({ initialEntries: [path] }),
  });
}

function mockReducedMotion(reduced: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion") ? reduced : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
}

/**
 * El crossfade entre rutas (`AnimatePresence` + `motion.div` en `RootLayout.tsx`, MASTER_PROMPT
 * §10.1) debe existir con movimiento normal y **omitirse** con `prefers-reduced-motion`.
 */
describe("RootLayout", () => {
  it("muestra la ruta activa dentro del nav y el shell con movimiento normal", async () => {
    mockReducedMotion(false);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = buildRouter("/");
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Pantalla Hoy")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    // Grano global (F5): una sola capa decorativa, siempre presente y fuera del árbol de a11y.
    expect(document.querySelector(".grain-overlay")).toHaveAttribute("aria-hidden", "true");
    // Ruta autenticada normal: el contenedor con el padding/ancho máximo del shell.
    expect(document.getElementById("main-content")).toHaveClass(styles["main"] ?? "");
  });

  it("las rutas públicas a pantalla completa (login) no llevan el padding/ancho del shell (F5-FE-02)", async () => {
    mockReducedMotion(false);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = buildRouter("/login");
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Pantalla Login")).toBeInTheDocument();
    // `/login` es pública: sin AppNav (ya cubierto por otros tests de isPublicPath en auth.test.tsx).
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    const main = document.getElementById("main-content");
    expect(main).toHaveClass(styles["fullBleed"] ?? "");
    expect(main).not.toHaveClass(styles["main"] ?? "");
  });

  it("con movimiento reducido, sigue mostrando la ruta activa (sin animar la transición)", async () => {
    mockReducedMotion(true);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = buildRouter("/rutinas");
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Pantalla Rutinas")).toBeInTheDocument();
  });
});

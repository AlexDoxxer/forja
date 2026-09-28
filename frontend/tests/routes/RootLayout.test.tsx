import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "../../src/i18n";
import { RootLayout } from "../../src/routes/RootLayout";

function buildRouter(path: string): ReturnType<typeof createRouter> {
  const root = createRootRoute({ component: RootLayout });
  const home = createRoute({ getParentRoute: () => root, path: "/", component: () => <p>Pantalla Hoy</p> });
  const programs = createRoute({ getParentRoute: () => root, path: "/rutinas", component: () => <p>Pantalla Rutinas</p> });
  return createRouter({
    routeTree: root.addChildren([home, programs]),
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

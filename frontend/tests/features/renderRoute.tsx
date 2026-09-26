import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router";
import type { ReactElement } from "react";

import "../../src/i18n";

/**
 * Renderiza un elemento en la ruta `path` de un router en memoria (con rutas «marcador» para
 * los destinos de navegación de las pantallas) y un `QueryClient` limpio.
 */
export function renderRoute(
  ui: ReactElement,
  path = "/",
  extraPaths: string[] = [],
): RenderResult & { router: { state: { location: { pathname: string } } } } {
  const root = createRootRoute();
  const main = createRoute({ getParentRoute: () => root, path, component: () => ui });
  const others = ["/sesion", "/rutinas", "/nutricion", "/perfil", "/admin", "/", ...extraPaths]
    .filter((p) => p !== path)
    .map((p) =>
      createRoute({ getParentRoute: () => root, path: p, component: () => <p>destino {p}</p> }),
    );
  const router = createRouter({
    routeTree: root.addChildren([main, ...others]),
    history: createMemoryHistory({ initialEntries: [path] }),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return Object.assign(result, { router });
}

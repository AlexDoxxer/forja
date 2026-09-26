import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import type { ComponentType } from "react";

import { ToastProvider } from "../../src/components/ui";

/** Rutas a las que apuntan los enlaces de las pantallas; se sustituyen por un marcador en tests. */
const STUB_PATHS = [
  "/",
  "/onboarding",
  "/biblioteca",
  "/biblioteca/$exerciseId",
  "/rutinas",
  "/rutinas/nueva",
  "/rutinas/$programId/editar",
];

export interface RenderWithRouterOptions {
  /** Patrón de ruta de la pantalla bajo prueba, p. ej. `/biblioteca/$exerciseId`. */
  path: string;
  /** URL inicial (por defecto, el propio patrón). */
  url?: string;
}

/**
 * Renderiza una pantalla dentro de un router en memoria con `QueryClient` y avisos, para que los
 * `Link` y `useParams` funcionen igual que en la aplicación. El resto de rutas son marcadores.
 */
export function renderWithRouter(Screen: ComponentType, { path, url }: RenderWithRouterOptions): RenderResult {
  const root = createRootRoute({ component: Outlet });
  const routes = STUB_PATHS.filter((stub) => stub !== path).map((stub) =>
    createRoute({ getParentRoute: () => root, path: stub, component: () => <p>{`ruta:${stub}`}</p> }),
  );
  routes.push(createRoute({ getParentRoute: () => root, path, component: Screen }));
  const router = createRouter({
    routeTree: root.addChildren(routes),
    history: createMemoryHistory({ initialEntries: [url ?? path] }),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

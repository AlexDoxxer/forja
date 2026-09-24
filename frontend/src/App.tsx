import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";

import "./i18n";
import { queryClient } from "./lib/queryClient";
import { router } from "./routes/router";

/** Raíz de la aplicación: proveedores de datos (TanStack Query) y de rutas (TanStack Router). */
export function App(): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

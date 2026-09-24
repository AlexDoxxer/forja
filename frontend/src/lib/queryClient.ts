import { QueryClient } from "@tanstack/react-query";

/** Cliente de TanStack Query compartido por toda la app (MASTER_PROMPT §4.1). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

/** Usuario actual (`GET /auth/me`): rol, dieta disponible y preferencias de unidades/idioma. */
export function useProfileSummary(): UseQueryResult<components["schemas"]["CurrentUser"]> {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => unwrapApi(await api.GET("/auth/me")),
  });
}

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type StatsOverview = components["schemas"]["StatsOverview"];

/** Resumen de la pantalla «Hoy» (MASTER_PROMPT §10.2.2, `GET /stats/overview`). */
export function useTodayOverview(): UseQueryResult<StatsOverview> {
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: async () => unwrapApi(await api.GET("/stats/overview")),
  });
}

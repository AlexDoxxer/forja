import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type VolumeStats = components["schemas"]["VolumeStats"];

/** Volumen semanal por grupo muscular (MASTER_PROMPT §10.2.8, `GET /stats/volume`). */
export function useVolumeStats(): UseQueryResult<VolumeStats> {
  return useQuery({
    queryKey: ["stats", "volume"],
    queryFn: async () => unwrapApi(await api.GET("/stats/volume")),
  });
}

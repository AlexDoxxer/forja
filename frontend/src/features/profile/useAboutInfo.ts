import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type AboutInfo = components["schemas"]["AboutInfo"];

/** Créditos y licencias (MASTER_PROMPT §10.2.10, §2.1, `GET /about`). */
export function useAboutInfo(): UseQueryResult<AboutInfo> {
  return useQuery({
    queryKey: ["about"],
    queryFn: async () => unwrapApi(await api.GET("/about")),
  });
}

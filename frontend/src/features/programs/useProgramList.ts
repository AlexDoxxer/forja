import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type ProgramPage = components["schemas"]["ProgramPage"];

/** Programas guardados de la persona (MASTER_PROMPT §10.2.7, `GET /programs`). */
export function useProgramList(): UseQueryResult<ProgramPage> {
  return useQuery({
    queryKey: ["programs", "list"],
    queryFn: async () => unwrapApi(await api.GET("/programs")),
  });
}

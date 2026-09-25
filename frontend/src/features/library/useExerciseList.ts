import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type ExercisePage = components["schemas"]["ExercisePage"];

/** Primera página de la biblioteca (MASTER_PROMPT §10.2.7, `GET /exercises`). */
export function useExerciseList(): UseQueryResult<ExercisePage> {
  return useQuery({
    queryKey: ["exercises", "list"],
    queryFn: async () => unwrapApi(await api.GET("/exercises")),
  });
}

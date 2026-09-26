import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];

export function useNextSession(): UseQueryResult<Schemas["NextSession"]> {
  return useQuery({
    queryKey: ["sessions", "next"],
    queryFn: async () => unwrapApi(await api.GET("/sessions/next")),
  });
}

export function useProfilePrefs(): UseQueryResult<Schemas["Profile"]> {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => unwrapApi(await api.GET("/profile")),
  });
}

export function useExerciseDetail(exerciseId: string | null): UseQueryResult<Schemas["ExerciseDetail"]> {
  return useQuery({
    queryKey: ["exercise", exerciseId],
    enabled: exerciseId !== null,
    queryFn: async () =>
      unwrapApi(
        await api.GET("/exercises/{exercise_id}", {
          params: { path: { exercise_id: exerciseId ?? "" } },
        }),
      ),
  });
}

export function useAlternatives(
  exerciseId: string | null,
  enabled: boolean,
): UseQueryResult<Schemas["ExerciseAlternativeList"]> {
  return useQuery({
    queryKey: ["exercise", exerciseId, "alternatives"],
    enabled: enabled && exerciseId !== null,
    queryFn: async () =>
      unwrapApi(
        await api.GET("/exercises/{exercise_id}/alternatives", {
          params: { path: { exercise_id: exerciseId ?? "" } },
        }),
      ),
  });
}

/** Resumen del servidor: `finish` es idempotente si la sesión ya estaba terminada. */
export async function fetchSessionSummary(
  serverId: string,
  finishedAt: string,
  perceivedEffort: number | null,
): Promise<Schemas["SessionSummary"]> {
  return unwrapApi(
    await api.POST("/sessions/{session_id}/finish", {
      params: { path: { session_id: serverId } },
      body: { finished_at: finishedAt, perceived_effort: perceivedEffort },
    }),
  );
}

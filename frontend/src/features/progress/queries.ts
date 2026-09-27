import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];

export function useOverview(): UseQueryResult<Schemas["StatsOverview"]> {
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: async () => unwrapApi(await api.GET("/stats/overview")),
  });
}

export function useVolume(weeks = 12): UseQueryResult<Schemas["VolumeStats"]> {
  return useQuery({
    queryKey: ["stats", "volume", weeks],
    queryFn: async () => unwrapApi(await api.GET("/stats/volume", { params: { query: { weeks } } })),
  });
}

export function useRecords(): UseQueryResult<Schemas["PersonalRecordPage"]> {
  return useQuery({
    queryKey: ["records"],
    queryFn: async () => unwrapApi(await api.GET("/records", { params: { query: { limit: 100 } } })),
  });
}

export function useExerciseStats(exerciseId: string | null): UseQueryResult<Schemas["ExerciseStats"]> {
  return useQuery({
    queryKey: ["stats", "exercise", exerciseId],
    enabled: exerciseId !== null,
    queryFn: async () =>
      unwrapApi(
        await api.GET("/stats/exercise/{exercise_id}", {
          params: { path: { exercise_id: exerciseId ?? "" } },
        }),
      ),
  });
}

export function useBodyMetrics(): UseQueryResult<Schemas["BodyMetricPage"]> {
  return useQuery({
    queryKey: ["body-metrics"],
    queryFn: async () => unwrapApi(await api.GET("/body-metrics", { params: { query: { limit: 100 } } })),
  });
}

import { useMutation, useQuery, useQueryClient, type UseMutationResult, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import type { DayEdit } from "./editorState";

export type ProgramDetail = components["schemas"]["ProgramDetail"];
export type PlanWarning = components["schemas"]["PlanWarning"];

export function useProgram(programId: string): UseQueryResult<ProgramDetail> {
  return useQuery({
    queryKey: ["programs", "detail", programId],
    queryFn: async () => unwrapApi(await api.GET("/programs/{program_id}", { params: { path: { program_id: programId } } })),
    // El editor mantiene su propio borrador: no se refresca solo bajo los pies de la persona.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}

export function useSaveDay(programId: string): UseMutationResult<ProgramDetail, Error, { dayId: string; edit: DayEdit }> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ dayId, edit }) =>
      unwrapApi(
        await api.PUT("/programs/{program_id}/days/{day_id}", {
          params: { path: { program_id: programId, day_id: dayId } },
          body: edit,
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["programs", "list"] });
    },
  });
}

/** Reglas duras del motor incumplidas (`plan_invalid`, `violations`) de un error de la API. */
export function violationsOf(error: unknown): PlanWarning[] {
  if (!(error instanceof ApiError)) return [];
  const problem: unknown = error.problem;
  if (typeof problem !== "object" || problem === null || !("violations" in problem)) return [];
  const violations: unknown = problem.violations;
  return Array.isArray(violations) ? (violations as PlanWarning[]) : [];
}

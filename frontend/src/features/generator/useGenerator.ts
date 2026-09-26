import { useMutation, useQuery, useQueryClient, type UseMutationResult, type UseQueryResult } from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];
export type GeneratorInput = Schemas["GeneratorInput"];
export type GeneratorPreview = Schemas["GeneratorPreview"];
export type ProgramPlan = Schemas["ProgramPlan"];
export type SlotAddress = Schemas["SlotAddress"];
export type PlanExercise = Schemas["PlanExercise"];
export type Profile = Schemas["Profile"];
export type ProgramDetail = Schemas["ProgramDetail"];

export function useProfile(): UseQueryResult<Profile> {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => unwrapApi(await api.GET("/profile")),
  });
}

export function usePreviewProgram(): UseMutationResult<GeneratorPreview, Error, { input: GeneratorInput }> {
  return useMutation({
    mutationFn: async ({ input }) => unwrapApi(await api.POST("/generator/preview", { body: input })),
  });
}

export function useRegenerateDay(): UseMutationResult<
  GeneratorPreview,
  Error,
  { plan: ProgramPlan; dayIndex: number }
> {
  return useMutation({
    mutationFn: async ({ plan, dayIndex }) =>
      unwrapApi(await api.POST("/generator/preview/regenerate-day", { body: { plan, day_index: dayIndex, seed: null } })),
  });
}

export function useSwapPreviewExercise(): UseMutationResult<
  GeneratorPreview,
  Error,
  { plan: ProgramPlan; address: SlotAddress; excludeIds: string[]; replacementId: string | null }
> {
  return useMutation({
    mutationFn: async ({ plan, address, excludeIds, replacementId }) =>
      unwrapApi(
        await api.POST("/generator/preview/swap", {
          body: {
            plan,
            address,
            exclude_ids: excludeIds,
            replacement_id: replacementId,
            apply_to_all_weeks: true,
          },
        }),
      ),
  });
}

export function useSaveProgram(): UseMutationResult<ProgramDetail, Error, { name: string; plan: ProgramPlan; activate: boolean }> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, plan, activate }) =>
      unwrapApi(await api.POST("/programs", { body: { source: "generated", name, plan, activate } })),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["programs"] });
    },
  });
}

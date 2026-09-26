import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];

export function useNutritionSettings(): UseQueryResult<Schemas["NutritionSettings"]> {
  return useQuery({
    queryKey: ["nutrition", "settings"],
    queryFn: async () => unwrapApi(await api.GET("/nutrition/settings")),
  });
}

export function useSaveSettings(): UseMutationResult<
  Schemas["NutritionSettings"],
  Error,
  Schemas["NutritionSettingsUpdate"]
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => unwrapApi(await api.PUT("/nutrition/settings", { body })),
    onSuccess: async (data) => {
      queryClient.setQueryData(["nutrition", "settings"], data);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useRecalculateTarget(): UseMutationResult<Schemas["NutritionTargetRecord"], Error, void> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => unwrapApi(await api.POST("/nutrition/targets/calculate", { body: {} })),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["nutrition", "settings"] });
    },
  });
}

export function usePlanList(enabled: boolean): UseQueryResult<Schemas["MealPlanPage"]> {
  return useQuery({
    queryKey: ["nutrition", "plans"],
    enabled,
    queryFn: async () => unwrapApi(await api.GET("/nutrition/plans", { params: { query: { limit: 10 } } })),
  });
}

export function usePlan(planId: string | null): UseQueryResult<Schemas["MealPlanResource"]> {
  return useQuery({
    queryKey: ["nutrition", "plan", planId],
    enabled: planId !== null,
    queryFn: async () =>
      unwrapApi(await api.GET("/nutrition/plans/{plan_id}", { params: { path: { plan_id: planId ?? "" } } })),
  });
}

export function useGeneratePlan(): UseMutationResult<Schemas["MealPlanResource"], Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (weekStart) =>
      unwrapApi(await api.POST("/nutrition/plans", { body: { week_start: weekStart } })),
    onSuccess: async (data) => {
      queryClient.setQueryData(["nutrition", "plan", data.id], data);
      await queryClient.invalidateQueries({ queryKey: ["nutrition", "plans"] });
    },
  });
}

export function useSwapFood(planId: string): UseMutationResult<
  Schemas["MealPlanResource"],
  Error,
  Schemas["MealSwapRequest"]
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) =>
      unwrapApi(
        await api.POST("/nutrition/plans/{plan_id}/swap", { params: { path: { plan_id: planId } }, body }),
      ),
    onSuccess: async (data) => {
      queryClient.setQueryData(["nutrition", "plan", planId], data);
      await queryClient.invalidateQueries({ queryKey: ["nutrition", "shopping", planId] });
    },
  });
}

export function useShoppingList(planId: string | null): UseQueryResult<Schemas["ShoppingList"]> {
  return useQuery({
    queryKey: ["nutrition", "shopping", planId],
    enabled: planId !== null,
    queryFn: async () =>
      unwrapApi(
        await api.GET("/nutrition/plans/{plan_id}/shopping-list", { params: { path: { plan_id: planId ?? "" } } }),
      ),
  });
}

export function useFoodSearch(q: string, enabled: boolean): UseQueryResult<Schemas["FoodPage"]> {
  return useQuery({
    queryKey: ["foods", q],
    enabled,
    queryFn: async () => unwrapApi(await api.GET("/foods", { params: { query: { q, limit: 8 } } })),
  });
}

/** Lunes de la semana de `date` en formato ISO (fecha local). */
export function mondayOf(date: Date): string {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${String(d.getFullYear())}-${month}-${day}`;
}

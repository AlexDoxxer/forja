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

export function useAdminSettings(): UseQueryResult<Schemas["AdminSettings"]> {
  return useQuery({
    queryKey: ["admin", "settings"],
    queryFn: async () => unwrapApi(await api.GET("/admin/settings")),
  });
}

export function useUpdateAdminSettings(): UseMutationResult<
  Schemas["AdminSettings"],
  Error,
  Schemas["AdminSettingsFields"]
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => unwrapApi(await api.PUT("/admin/settings", { body })),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin", "settings"], data);
    },
  });
}

export function useAdminUsers(q: string): UseQueryResult<Schemas["AdminUserPage"]> {
  return useQuery({
    queryKey: ["admin", "users", q],
    queryFn: async () =>
      unwrapApi(
        await api.GET("/admin/users", { params: { query: { limit: 50, ...(q === "" ? {} : { q }) } } }),
      ),
  });
}

export function useUpdateUser(): UseMutationResult<
  Schemas["AdminUser"],
  Error,
  { id: string; patch: Schemas["AdminUserUpdate"] }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, patch }) =>
      unwrapApi(await api.PATCH("/admin/users/{user_id}", { params: { path: { user_id: id } }, body: patch })),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export function useIngestRuns(): UseQueryResult<Schemas["IngestRunPage"]> {
  return useQuery({
    queryKey: ["admin", "ingest"],
    queryFn: async () => unwrapApi(await api.GET("/admin/ingest/runs", { params: { query: { limit: 10 } } })),
    // Mientras haya una ejecución en marcha se consulta cada pocos segundos.
    refetchInterval: (query) =>
      query.state.data?.items.some((r) => r.status === "queued" || r.status === "running") === true ? 4000 : false,
  });
}

export function useStartIngest(): UseMutationResult<Schemas["IngestRun"], Error, boolean> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (dryRun) => unwrapApi(await api.POST("/admin/ingest", { body: { dry_run: dryRun } })),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin", "ingest"] });
    },
  });
}

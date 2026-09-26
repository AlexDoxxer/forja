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
export type ProfileFields = Schemas["ProfileFields"];

export function useProfile(): UseQueryResult<Schemas["Profile"]> {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => unwrapApi(await api.GET("/profile")),
  });
}

/** Campos editables de un `Profile` (el resto son de solo lectura). */
export function toProfileFields(p: Schemas["Profile"]): ProfileFields {
  return {
    display_name: p.display_name,
    locale: p.locale,
    units: p.units,
    sex: p.sex,
    birth_date: p.birth_date,
    height_cm: p.height_cm,
    experience: p.experience,
    activity_level: p.activity_level,
    equipment: p.equipment,
    limitations: p.limitations,
    diet_enabled: p.diet_enabled,
    preferences: p.preferences,
  };
}

export function useSaveProfile(): UseMutationResult<Schemas["Profile"], Error, ProfileFields> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => unwrapApi(await api.PUT("/profile", { body })),
    onSuccess: async (data) => {
      queryClient.setQueryData(["profile"], data);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useAuthSessions(): UseQueryResult<Schemas["AuthSessionList"]> {
  return useQuery({
    queryKey: ["auth", "sessions"],
    queryFn: async () => unwrapApi(await api.GET("/auth/sessions")),
  });
}

export function useRevokeSession(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id) => {
      const result = await api.DELETE("/auth/sessions/{auth_session_id}", {
        params: { path: { auth_session_id: id } },
      });
      if (result.error !== undefined) unwrapApi(result as { data?: never; error: unknown });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["auth", "sessions"] });
    },
  });
}

/** Descarga la copia completa de datos (JSON) como `Blob`. */
export async function fetchExport(): Promise<Blob> {
  const result = await api.GET("/me/export", { parseAs: "blob" });
  return unwrapApi(result as { data?: Blob; error?: unknown });
}

export async function importExport(payload: Schemas["UserExport"]): Promise<Schemas["ImportResult"]> {
  return unwrapApi(await api.POST("/me/import", { body: payload }));
}

export async function deleteAccount(password: string): Promise<void> {
  const result = await api.DELETE("/me", { body: { password } });
  if (result.error !== undefined) unwrapApi(result as { data?: never; error: unknown });
}

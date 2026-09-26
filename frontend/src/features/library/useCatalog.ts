import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type UseInfiniteQueryResult,
  type UseMutationResult,
  type UseQueryResult,
  type InfiniteData,
} from "@tanstack/react-query";

import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import type { BodyPart, EquipmentCode, InstructionLang, MovementPattern, MuscleCode } from "../shared/enums";

export type ExerciseSummary = components["schemas"]["ExerciseSummary"];
export type ExercisePage = components["schemas"]["ExercisePage"];
export type ExerciseDetail = components["schemas"]["ExerciseDetail"];
export type ExerciseAlternativeList = components["schemas"]["ExerciseAlternativeList"];
export type CatalogFacets = components["schemas"]["CatalogFacets"];
export type ExerciseStats = components["schemas"]["ExerciseStats"];

export interface LibraryFilters {
  q: string;
  body_part: readonly BodyPart[];
  muscle: readonly MuscleCode[];
  equipment: readonly EquipmentCode[];
  pattern: readonly MovementPattern[];
  difficulty: readonly (1 | 2 | 3)[];
  favorites: boolean;
}

export const EMPTY_FILTERS: LibraryFilters = {
  q: "",
  body_part: [],
  muscle: [],
  equipment: [],
  pattern: [],
  difficulty: [],
  favorites: false,
};

export const PAGE_SIZE = 60;

function filterQuery(filters: LibraryFilters): {
  q?: string;
  body_part?: BodyPart[];
  muscle?: MuscleCode[];
  equipment?: EquipmentCode[];
  pattern?: MovementPattern[];
  difficulty?: (1 | 2 | 3)[];
  favorites?: boolean;
} {
  return {
    ...(filters.q === "" ? {} : { q: filters.q }),
    ...(filters.body_part.length > 0 ? { body_part: [...filters.body_part] } : {}),
    ...(filters.muscle.length > 0 ? { muscle: [...filters.muscle] } : {}),
    ...(filters.equipment.length > 0 ? { equipment: [...filters.equipment] } : {}),
    ...(filters.pattern.length > 0 ? { pattern: [...filters.pattern] } : {}),
    ...(filters.difficulty.length > 0 ? { difficulty: [...filters.difficulty] } : {}),
    ...(filters.favorites ? { favorites: true } : {}),
  };
}

/** Búsqueda paginada por cursor (`GET /exercises`); conserva la lista anterior mientras carga la nueva. */
export function useExerciseSearch(
  filters: LibraryFilters,
): UseInfiniteQueryResult<InfiniteData<ExercisePage, string | null>> {
  return useInfiniteQuery({
    queryKey: ["exercises", "search", filters],
    initialPageParam: null as string | null,
    placeholderData: keepPreviousData,
    queryFn: async ({ pageParam }) =>
      unwrapApi(
        await api.GET("/exercises", {
          params: {
            query: {
              ...filterQuery(filters),
              limit: PAGE_SIZE,
              ...(pageParam === null ? {} : { cursor: pageParam }),
            },
          },
        }),
      ),
    getNextPageParam: (last) => last.next_cursor,
  });
}

/** Recuentos por valor de cada filtro (`GET /catalog/facets`). */
export function useCatalogFacets(filters: LibraryFilters): UseQueryResult<CatalogFacets> {
  return useQuery({
    queryKey: ["catalog", "facets", filters],
    placeholderData: keepPreviousData,
    queryFn: async () =>
      unwrapApi(
        await api.GET("/catalog/facets", {
          params: {
            query: {
              ...(filters.q === "" ? {} : { q: filters.q }),
              ...(filters.body_part.length > 0 ? { body_part: [...filters.body_part] } : {}),
              ...(filters.muscle.length > 0 ? { muscle: [...filters.muscle] } : {}),
              ...(filters.equipment.length > 0 ? { equipment: [...filters.equipment] } : {}),
              ...(filters.pattern.length > 0 ? { pattern: [...filters.pattern] } : {}),
              ...(filters.favorites ? { favorites: true } : {}),
            },
          },
        }),
      ),
  });
}

export function useExerciseDetail(id: string, lang: InstructionLang): UseQueryResult<ExerciseDetail> {
  return useQuery({
    queryKey: ["exercises", "detail", id, lang],
    placeholderData: keepPreviousData,
    queryFn: async () =>
      unwrapApi(await api.GET("/exercises/{exercise_id}", { params: { path: { exercise_id: id }, query: { lang } } })),
  });
}

export function useExerciseAlternatives(id: string): UseQueryResult<ExerciseAlternativeList> {
  return useQuery({
    queryKey: ["exercises", "alternatives", id],
    queryFn: async () =>
      unwrapApi(await api.GET("/exercises/{exercise_id}/alternatives", { params: { path: { exercise_id: id } } })),
  });
}

export function useExerciseStats(id: string): UseQueryResult<ExerciseStats> {
  return useQuery({
    queryKey: ["stats", "exercise", id],
    queryFn: async () =>
      unwrapApi(await api.GET("/stats/exercise/{exercise_id}", { params: { path: { exercise_id: id } } })),
  });
}

/** Marca o desmarca favorito (idempotente) y refresca el catálogo. */
export function useToggleFavorite(id: string): UseMutationResult<void, Error, boolean> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (makeFavorite: boolean) => {
      const result = makeFavorite
        ? await api.PUT("/exercises/{exercise_id}/favorite", { params: { path: { exercise_id: id } } })
        : await api.DELETE("/exercises/{exercise_id}/favorite", { params: { path: { exercise_id: id } } });
      if (result.error !== undefined) throw new Error("favorite");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["exercises"] });
    },
  });
}

/** Ejercicios cargados de todas las páginas, sin duplicados. */
export function flattenPages(data: InfiniteData<ExercisePage, string | null> | undefined): ExerciseSummary[] {
  if (data === undefined) return [];
  const seen = new Set<string>();
  const out: ExerciseSummary[] = [];
  for (const page of data.pages) {
    for (const item of page.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        out.push(item);
      }
    }
  }
  return out;
}

import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];
export type ExerciseSummary = Schemas["ExerciseSummary"];
export type LoadSuggestion = Schemas["LoadSuggestion"];
export type NextSession = Schemas["NextSession"];
export type SetLogCreate = Schemas["SetLogCreate"];

/** Ejercicio del día ya «congelado» en el cliente para poder entrenar sin red. */
export interface PlayerSlot {
  key: string;
  programExerciseId: string | null;
  exercise: ExerciseSummary;
  sets: number;
  repMin: number | null;
  repMax: number | null;
  durationS: number | null;
  targetRir: number | null;
  restS: number;
  notesEs: string | null;
  suggestion: LoadSuggestion | null;
  alternatives: string[];
}

export interface LoggedSet {
  clientUuid: string;
  slotKey: string;
  exerciseId: string;
  programExerciseId: string | null;
  setIndex: number;
  weightKg: number | null;
  reps: number | null;
  rir: number | null;
  isWarmup: boolean;
  completedAt: string;
}

export interface RestState {
  startedAt: number;
  endsAt: number;
}

/**
 * Estados explícitos del reproductor (MASTER_PROMPT §10.2.5):
 * `exercising` → registrar la serie actual; `resting` → cuenta atrás; `finished` → todas las
 * series hechas, a la espera de esfuerzo percibido; `completed` → sesión cerrada.
 */
export type Phase = "exercising" | "resting" | "finished" | "completed";

export interface PlayerState {
  version: 1;
  sessionUuid: string;
  programDayId: string | null;
  name: string;
  startedAt: string;
  slots: PlayerSlot[];
  slotIndex: number;
  /** Serie de trabajo siguiente (0-based) dentro del ejercicio actual. */
  setIndex: number;
  sets: LoggedSet[];
  phase: Phase;
  rest: RestState | null;
  perceivedEffort: number | null;
  finishedAt: string | null;
  serverId: string | null;
}

export type PlayerAction =
  | {
      type: "LOG_SET";
      now: number;
      uuid: string;
      weightKg: number | null;
      reps: number | null;
      rir: number | null;
      isWarmup?: boolean;
    }
  | { type: "REST_ADJUST"; deltaMs: number; now: number }
  | { type: "REST_DONE" }
  | { type: "GO_TO_SLOT"; index: number }
  | { type: "SWAP_EXERCISE"; exercise: ExerciseSummary }
  | { type: "UNDO_LAST" }
  | { type: "FINISH"; now: number; perceivedEffort: number | null }
  | { type: "SET_SERVER_ID"; serverId: string };

export interface StartInput {
  sessionUuid: string;
  now: number;
  next: NextSession;
}

/** Crea el estado inicial a partir de `GET /sessions/next` (bloques aplanados en orden). */
export function createInitialState({ sessionUuid, now, next }: StartInput): PlayerState {
  const byId = new Map(next.exercises.map((e) => [e.id, e]));
  const suggestions = new Map(next.suggestions.map((s) => [s.program_exercise_id, s]));
  const slots: PlayerSlot[] = [];
  const blocks = [...(next.day?.blocks ?? [])].sort((a, b) => a.order - b.order);
  for (const block of blocks) {
    for (const item of [...block.exercises].sort((a, b) => a.order - b.order)) {
      const exercise = byId.get(item.exercise_id);
      if (exercise === undefined) continue;
      slots.push({
        key: item.id,
        programExerciseId: item.id,
        exercise,
        sets: Math.max(1, item.sets),
        repMin: item.rep_min,
        repMax: item.rep_max,
        durationS: item.duration_s,
        targetRir: item.target_rir,
        restS: item.rest_s,
        notesEs: item.notes_es,
        suggestion: suggestions.get(item.id) ?? null,
        alternatives: item.alternatives,
      });
    }
  }
  return {
    version: 1,
    sessionUuid,
    programDayId: next.day?.id ?? null,
    name: next.day?.name ?? "Sesión libre",
    startedAt: new Date(now).toISOString(),
    slots,
    slotIndex: 0,
    setIndex: 0,
    sets: [],
    phase: slots.length === 0 ? "finished" : "exercising",
    rest: null,
    perceivedEffort: null,
    finishedAt: null,
    serverId: null,
  };
}

export function currentSlot(state: PlayerState): PlayerSlot | null {
  return state.slots[state.slotIndex] ?? null;
}

export function setsOfSlot(state: PlayerState, slotKey: string): LoggedSet[] {
  return state.sets.filter((s) => s.slotKey === slotKey);
}

export function workSetsDone(state: PlayerState, slotKey: string): number {
  return setsOfSlot(state, slotKey).filter((s) => !s.isWarmup).length;
}

/** Milisegundos que faltan (>= 0) calculados siempre desde marcas de tiempo, nunca acumulados. */
export function restRemainingMs(rest: RestState | null, now: number): number {
  return rest === null ? 0 : Math.max(0, rest.endsAt - now);
}

/** Volumen local (kg × reps) de series de trabajo; solo para mostrar mientras se entrena. */
export function localVolumeKg(state: PlayerState): number {
  return state.sets
    .filter((s) => !s.isWarmup)
    .reduce((acc, s) => acc + (s.weightKg ?? 0) * (s.reps ?? 0), 0);
}

function advance(state: PlayerState): Pick<PlayerState, "slotIndex" | "setIndex" | "phase"> {
  const slot = currentSlot(state);
  const nextSet = state.setIndex + 1;
  if (slot !== null && nextSet < slot.sets) {
    return { slotIndex: state.slotIndex, setIndex: nextSet, phase: "resting" };
  }
  if (state.slotIndex + 1 < state.slots.length) {
    return { slotIndex: state.slotIndex + 1, setIndex: 0, phase: "resting" };
  }
  return { slotIndex: state.slotIndex, setIndex: nextSet, phase: "finished" };
}

/** Reductor puro de la máquina de estados del reproductor. */
export function playerReducer(state: PlayerState, action: PlayerAction): PlayerState {
  switch (action.type) {
    case "LOG_SET": {
      const slot = currentSlot(state);
      if (slot === null || state.phase === "finished" || state.phase === "completed") return state;
      const logged: LoggedSet = {
        clientUuid: action.uuid,
        slotKey: slot.key,
        exerciseId: slot.exercise.id,
        programExerciseId: slot.programExerciseId,
        setIndex: setsOfSlot(state, slot.key).length,
        weightKg: action.weightKg,
        reps: action.reps,
        rir: action.rir,
        isWarmup: action.isWarmup ?? false,
        completedAt: new Date(action.now).toISOString(),
      };
      const withSet = { ...state, sets: [...state.sets, logged] };
      if (logged.isWarmup) {
        return withSet;
      }
      const moved = advance(state);
      const restMs = slot.restS * 1000;
      return {
        ...withSet,
        ...moved,
        rest:
          moved.phase === "resting" && restMs > 0
            ? { startedAt: action.now, endsAt: action.now + restMs }
            : null,
        phase: moved.phase === "resting" && restMs === 0 ? "exercising" : moved.phase,
      };
    }
    case "REST_ADJUST": {
      if (state.phase !== "resting" || state.rest === null) return state;
      const endsAt = Math.max(action.now, state.rest.endsAt + action.deltaMs);
      return { ...state, rest: { ...state.rest, endsAt } };
    }
    case "REST_DONE":
      return state.phase === "resting" ? { ...state, phase: "exercising", rest: null } : state;
    case "GO_TO_SLOT": {
      if (state.phase === "completed" || action.index < 0 || action.index >= state.slots.length) {
        return state;
      }
      const target = state.slots[action.index];
      if (target === undefined) return state;
      return {
        ...state,
        slotIndex: action.index,
        setIndex: Math.min(workSetsDone(state, target.key), target.sets - 1),
        phase: "exercising",
        rest: null,
      };
    }
    case "SWAP_EXERCISE": {
      const slot = currentSlot(state);
      if (slot === null) return state;
      const slots = state.slots.map((s, i) =>
        i === state.slotIndex
          ? { ...s, exercise: action.exercise, suggestion: null, alternatives: [] }
          : s,
      );
      return { ...state, slots };
    }
    case "UNDO_LAST": {
      const last = state.sets[state.sets.length - 1];
      if (last === undefined || state.phase === "completed") return state;
      const slotIndex = state.slots.findIndex((s) => s.key === last.slotKey);
      const sets = state.sets.slice(0, -1);
      const target = state.slots[slotIndex];
      return {
        ...state,
        sets,
        slotIndex: Math.max(0, slotIndex),
        setIndex:
          target === undefined
            ? state.setIndex
            : Math.min(sets.filter((s) => s.slotKey === target.key && !s.isWarmup).length, target.sets - 1),
        phase: "exercising",
        rest: null,
      };
    }
    case "FINISH":
      return {
        ...state,
        phase: "completed",
        rest: null,
        perceivedEffort: action.perceivedEffort,
        finishedAt: new Date(action.now).toISOString(),
      };
    case "SET_SERVER_ID":
      return { ...state, serverId: action.serverId };
  }
}

/** Instrucción a la cola offline derivable de un cambio (ADR 0006). */
export function toSetCreate(set: LoggedSet): SetLogCreate {
  return {
    client_uuid: set.clientUuid,
    exercise_id: set.exerciseId,
    program_exercise_id: set.programExerciseId,
    // Interno 0-based; el contrato (SetLogCreate) exige >= 1.
    set_index: set.setIndex + 1,
    weight_kg: set.weightKg,
    reps: set.reps,
    rir: set.rir,
    duration_s: null,
    is_warmup: set.isWarmup,
    completed_at: set.completedAt,
  };
}

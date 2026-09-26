import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];
export type Prescription = Schemas["ExercisePrescription"];
export type BlockKind = Schemas["BlockKind"];
export type ProgramDay = Schemas["ProgramDay"];
export type DayEdit = Schemas["DayEdit"];

export interface ExerciseDraft extends Prescription {
  /** Identidad estable en la UI (dnd-kit); no viaja al servidor. */
  key: string;
}

export interface BlockDraft {
  key: string;
  kind: BlockKind;
  rounds: number;
  rest_between_rounds_s: number | null;
  exercises: ExerciseDraft[];
}

export interface DayDraft {
  key: string;
  /** Id del día en la semana 0 del programa (destino del PUT). */
  dayId: string;
  /** Índice del día en la semana (para casar avisos del motor). */
  index: number;
  name: string;
  focus: string | null;
  weekday: ProgramDay["weekday"];
  blocks: BlockDraft[];
}

export interface EditorState {
  days: DayDraft[];
  past: DayDraft[][];
  future: DayDraft[][];
  /** Contador de ediciones (0 = sin cambios desde la carga o el último guardado). */
  revision: number;
}

let keyCounter = 0;
export function newKey(prefix: string): string {
  keyCounter += 1;
  return `${prefix}-${String(keyCounter)}`;
}

/** Prescripción por defecto de un ejercicio añadido a mano; el motor la valida y reequilibra al guardar. */
export function defaultPrescription(exerciseId: string): Prescription {
  return {
    exercise_id: exerciseId,
    sets: 3,
    rep_min: 8,
    rep_max: 12,
    duration_s: null,
    per_side: false,
    target_rir: 2,
    tempo: null,
    rest_s: 90,
    load_hint: null,
    notes_es: null,
    alternatives: [],
  };
}

export function daysFromProgram(days: readonly ProgramDay[]): DayDraft[] {
  return days.map((day) => ({
    key: newKey("day"),
    dayId: day.id,
    index: day.index,
    name: day.name,
    focus: day.focus,
    weekday: day.weekday,
    blocks: day.blocks.map((block) => ({
      key: newKey("block"),
      kind: block.kind,
      rounds: block.rounds,
      rest_between_rounds_s: block.rest_between_rounds_s,
      exercises: block.exercises.map((exercise) => ({
        key: newKey("ex"),
        exercise_id: exercise.exercise_id,
        sets: exercise.sets,
        rep_min: exercise.rep_min,
        rep_max: exercise.rep_max,
        duration_s: exercise.duration_s,
        per_side: exercise.per_side,
        target_rir: exercise.target_rir,
        tempo: exercise.tempo,
        rest_s: exercise.rest_s,
        load_hint: exercise.load_hint,
        notes_es: exercise.notes_es,
        alternatives: exercise.alternatives,
      })),
    })),
  }));
}

export function initialEditorState(days: readonly ProgramDay[]): EditorState {
  return { days: daysFromProgram(days), past: [], future: [], revision: 0 };
}

function stripKey(exercise: ExerciseDraft): Prescription {
  return {
    exercise_id: exercise.exercise_id,
    sets: exercise.sets,
    rep_min: exercise.rep_min,
    rep_max: exercise.rep_max,
    duration_s: exercise.duration_s,
    per_side: exercise.per_side,
    target_rir: exercise.target_rir,
    tempo: exercise.tempo,
    rest_s: exercise.rest_s,
    load_hint: exercise.load_hint,
    notes_es: exercise.notes_es,
    alternatives: exercise.alternatives,
  };
}

/** Cuerpo de `PUT /programs/{id}/days/{day_id}` a partir del borrador (sin claves de UI). */
export function toDayEdit(day: DayDraft, applyToAllWeeks: boolean): DayEdit {
  return {
    name: day.name,
    focus: day.focus,
    weekday: day.weekday,
    apply_to_all_weeks: applyToAllWeeks,
    blocks: day.blocks.map((block) => ({
      kind: block.kind,
      rounds: block.rounds,
      rest_between_rounds_s: block.rest_between_rounds_s,
      exercises: block.exercises.map(stripKey),
    })),
  };
}

export type EditorAction =
  | { type: "move"; dayKey: string; activeKey: string; overKey: string }
  | { type: "moveStep"; dayKey: string; exerciseKey: string; delta: -1 | 1 }
  | { type: "update"; dayKey: string; exerciseKey: string; patch: Partial<Prescription> }
  | { type: "remove"; dayKey: string; exerciseKey: string }
  | { type: "add"; dayKey: string; exerciseId: string }
  | { type: "mergeNext"; dayKey: string; blockKey: string }
  | { type: "split"; dayKey: string; blockKey: string }
  | { type: "block"; dayKey: string; blockKey: string; patch: Partial<Pick<BlockDraft, "rounds" | "rest_between_rounds_s">> }
  | { type: "day"; dayKey: string; patch: Partial<Pick<DayDraft, "name" | "focus" | "weekday">> }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "reset"; days: readonly ProgramDay[] };

function commit(state: EditorState, days: DayDraft[]): EditorState {
  return { days, past: [...state.past, state.days], future: [], revision: state.revision + 1 };
}

function mapDay(days: DayDraft[], dayKey: string, fn: (day: DayDraft) => DayDraft): DayDraft[] {
  return days.map((day) => (day.key === dayKey ? fn(day) : day));
}

function locate(day: DayDraft, exerciseKey: string): { block: number; index: number } | null {
  for (let block = 0; block < day.blocks.length; block += 1) {
    const index = day.blocks[block]?.exercises.findIndex((exercise) => exercise.key === exerciseKey) ?? -1;
    if (index >= 0) return { block, index };
  }
  return null;
}

/** Tipo de bloque según el número de ejercicios: 1 ⇒ principal, 2 ⇒ superserie, 3+ ⇒ circuito. */
function kindForSize(size: number, current: BlockKind): BlockKind {
  if (size >= 3) return "circuit";
  if (size === 2) return "superset";
  return current === "superset" || current === "circuit" ? "main" : current;
}

function normalizeBlocks(blocks: BlockDraft[]): BlockDraft[] {
  return blocks
    .filter((block) => block.exercises.length > 0)
    .map((block) => ({ ...block, kind: kindForSize(block.exercises.length, block.kind) }));
}

function moveExercise(day: DayDraft, activeKey: string, overKey: string): DayDraft {
  const from = locate(day, activeKey);
  if (from === null) return day;
  const over = locate(day, overKey);
  const blocks = day.blocks.map((block) => ({ ...block, exercises: [...block.exercises] }));
  const source = blocks[from.block];
  const moved = source?.exercises[from.index];
  if (source === undefined || moved === undefined) return day;

  if (over === null) {
    // El destino es el contenedor de un bloque: se añade al final de ese bloque.
    const toBlock = blocks.findIndex((block) => block.key === overKey);
    const target = blocks[toBlock];
    if (target === undefined || toBlock === from.block) return day;
    source.exercises.splice(from.index, 1);
    target.exercises.push(moved);
    return { ...day, blocks: normalizeBlocks(blocks) };
  }

  if (over.block === from.block) {
    // Mismo bloque: `arrayMove` (el elemento acaba en la posición del destino).
    source.exercises.splice(from.index, 1);
    source.exercises.splice(over.index, 0, moved);
    return { ...day, blocks: normalizeBlocks(blocks) };
  }

  const target = blocks[over.block];
  if (target === undefined) return day;
  if (source.exercises.length === 1 && target.exercises.length === 1) {
    // Dos bloques de un solo ejercicio: arrastrar reordena los bloques (no crea una superserie;
    // eso se hace de forma explícita con «Unir con el siguiente»).
    const [block] = blocks.splice(from.block, 1);
    if (block === undefined) return day;
    blocks.splice(over.block, 0, block);
    return { ...day, blocks };
  }
  // Se suelta sobre un ejercicio de otro bloque agrupado: se une a ese bloque.
  source.exercises.splice(from.index, 1);
  target.exercises.splice(from.block < over.block ? over.index + 1 : over.index, 0, moved);
  return { ...day, blocks: normalizeBlocks(blocks) };
}

/** Paso de teclado: sube/baja una posición; en el borde de un bloque agrupado sale a su propio bloque. */
function stepExercise(day: DayDraft, exerciseKey: string, delta: -1 | 1): DayDraft {
  const from = locate(day, exerciseKey);
  if (from === null) return day;
  const block = day.blocks[from.block];
  if (block === undefined) return day;
  const neighbour = block.exercises[from.index + delta];
  if (neighbour !== undefined) return moveExercise(day, exerciseKey, neighbour.key);

  const blocks = day.blocks.map((item) => ({ ...item, exercises: [...item.exercises] }));
  if (block.exercises.length === 1) {
    const sibling = from.block + delta;
    if (blocks[sibling] === undefined) return day;
    const [moved] = blocks.splice(from.block, 1);
    if (moved === undefined) return day;
    blocks.splice(sibling, 0, moved);
    return { ...day, blocks };
  }
  const moving = block.exercises[from.index];
  const source = blocks[from.block];
  if (moving === undefined || source === undefined) return day;
  source.exercises.splice(from.index, 1);
  const alone: BlockDraft = { key: newKey("block"), kind: "main", rounds: 1, rest_between_rounds_s: null, exercises: [moving] };
  blocks.splice(delta === 1 ? from.block + 1 : from.block, 0, alone);
  return { ...day, blocks: normalizeBlocks(blocks) };
}

export function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "undo": {
      const previous = state.past[state.past.length - 1];
      if (previous === undefined) return state;
      return { days: previous, past: state.past.slice(0, -1), future: [state.days, ...state.future], revision: state.revision + 1 };
    }
    case "redo": {
      const next = state.future[0];
      if (next === undefined) return state;
      return { days: next, past: [...state.past, state.days], future: state.future.slice(1), revision: state.revision + 1 };
    }
    case "reset":
      return initialEditorState(action.days);
    case "move":
      if (action.activeKey === action.overKey) return state;
      return commit(state, mapDay(state.days, action.dayKey, (day) => moveExercise(day, action.activeKey, action.overKey)));
    case "moveStep":
      return commit(state, mapDay(state.days, action.dayKey, (day) => stepExercise(day, action.exerciseKey, action.delta)));
    case "update":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => ({
          ...day,
          blocks: day.blocks.map((block) => ({
            ...block,
            exercises: block.exercises.map((exercise) =>
              exercise.key === action.exerciseKey ? { ...exercise, ...action.patch } : exercise,
            ),
          })),
        })),
      );
    case "remove":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => ({
          ...day,
          blocks: normalizeBlocks(
            day.blocks.map((block) => ({
              ...block,
              exercises: block.exercises.filter((exercise) => exercise.key !== action.exerciseKey),
            })),
          ),
        })),
      );
    case "add":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => ({
          ...day,
          blocks: [
            ...day.blocks,
            {
              key: newKey("block"),
              kind: "main",
              rounds: 1,
              rest_between_rounds_s: null,
              exercises: [{ key: newKey("ex"), ...defaultPrescription(action.exerciseId) }],
            },
          ],
        })),
      );
    case "mergeNext":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => {
          const index = day.blocks.findIndex((block) => block.key === action.blockKey);
          const current = day.blocks[index];
          const following = day.blocks[index + 1];
          if (current === undefined || following === undefined) return day;
          const merged: BlockDraft = {
            ...current,
            exercises: [...current.exercises, ...following.exercises],
            rounds: Math.max(current.rounds, following.rounds),
          };
          merged.kind = kindForSize(merged.exercises.length, "superset");
          const blocks = [...day.blocks];
          blocks.splice(index, 2, merged);
          return { ...day, blocks };
        }),
      );
    case "split":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => {
          const index = day.blocks.findIndex((block) => block.key === action.blockKey);
          const current = day.blocks[index];
          if (current === undefined || current.exercises.length < 2) return day;
          const singles: BlockDraft[] = current.exercises.map((exercise) => ({
            key: newKey("block"),
            kind: "main",
            rounds: 1,
            rest_between_rounds_s: null,
            exercises: [exercise],
          }));
          const blocks = [...day.blocks];
          blocks.splice(index, 1, ...singles);
          return { ...day, blocks };
        }),
      );
    case "block":
      return commit(
        state,
        mapDay(state.days, action.dayKey, (day) => ({
          ...day,
          blocks: day.blocks.map((block) => (block.key === action.blockKey ? { ...block, ...action.patch } : block)),
        })),
      );
    case "day":
      return commit(state, mapDay(state.days, action.dayKey, (day) => ({ ...day, ...action.patch })));
  }
}

const TEMPO_PATTERN = /^[0-9X]-[0-9X]-[0-9X]-[0-9X]$/;

export type FieldErrors = Partial<Record<"sets" | "reps" | "duration" | "rir" | "tempo" | "rest", string>>;

/**
 * Comprobaciones de forma del contrato (rangos del esquema OpenAPI), no reglas del motor: las
 * reglas duras y los avisos de volumen los devuelve `PUT /programs/{id}/days/{day_id}`.
 * Devuelve claves de i18n de error por campo.
 */
export function validateExercise(exercise: Prescription): FieldErrors {
  const errors: FieldErrors = {};
  if (!Number.isInteger(exercise.sets) || exercise.sets < 1 || exercise.sets > 10) errors.sets = "editor.errors.sets";
  if (exercise.duration_s === null) {
    const { rep_min: min, rep_max: max } = exercise;
    if (min === null || max === null || min < 1 || max > 100 || min > max) errors.reps = "editor.errors.reps";
  } else if (exercise.duration_s < 5 || exercise.duration_s > 3600) {
    errors.duration = "editor.errors.duration";
  }
  if (exercise.target_rir !== null && (exercise.target_rir < 0 || exercise.target_rir > 5)) errors.rir = "editor.errors.rir";
  if (exercise.tempo !== null && !TEMPO_PATTERN.test(exercise.tempo)) errors.tempo = "editor.errors.tempo";
  if (exercise.rest_s < 0 || exercise.rest_s > 600) errors.rest = "editor.errors.rest";
  return errors;
}

export function dayHasErrors(day: DayDraft): boolean {
  return day.blocks.length === 0 || day.blocks.some((block) => block.exercises.some((exercise) => Object.keys(validateExercise(exercise)).length > 0));
}

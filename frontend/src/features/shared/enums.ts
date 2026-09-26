import type { components } from "../../lib/api/schema";

type Schemas = components["schemas"];

export type Goal = Schemas["Goal"];
export type Sex = Schemas["Sex"];
export type Experience = Schemas["Experience"];
export type Emphasis = Schemas["Emphasis"];
export type EquipmentPreset = Schemas["EquipmentPreset"];
export type EquipmentCode = Schemas["EquipmentCode"];
export type MuscleCode = Schemas["MuscleCode"];
export type MovementPattern = Schemas["MovementPattern"];
export type Weekday = Schemas["Weekday"];
export type InstructionLang = Schemas["InstructionLang"];
export type BodyPart = Schemas["BodyPart"];
export type VolumeGroup = Schemas["VolumeGroup"];
export type BlockKind = Schemas["BlockKind"];

export const GOALS: readonly Goal[] = ["strength", "hypertrophy", "fat_loss", "endurance", "general_fitness", "toning"];
export const SEXES: readonly Sex[] = ["male", "female", "unspecified"];
export const EXPERIENCES: readonly Experience[] = ["beginner", "intermediate", "advanced"];
export const EMPHASES: readonly Emphasis[] = ["balanced", "lower_glutes", "upper_body", "arms", "back_posture", "core"];
export const PRESETS: readonly EquipmentPreset[] = ["full_gym", "home_dumbbells", "home_bands", "bodyweight", "custom"];
export const WEEKDAYS: readonly Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
export const LANGS: readonly InstructionLang[] = ["es", "en", "fr", "it", "pl", "ru", "tr", "zh", "hi", "ko"];

export const EQUIPMENT_CODES: readonly EquipmentCode[] = [
  "bodyweight", "dumbbell", "cable", "barbell", "ez_bar", "trap_bar", "machine", "smith", "sled", "assisted", "band",
  "kettlebell", "weighted", "stability_ball", "medicine_ball", "bosu", "rope", "roller", "ab_wheel", "hammer", "tire",
  "arm_ergometer", "skierg", "bike", "elliptical", "stepmill",
];

export const MUSCLE_CODES: readonly MuscleCode[] = [
  "chest", "lats", "upper_back", "traps", "lower_back", "shoulders", "rear_delts", "rotator_cuff", "serratus",
  "biceps", "triceps", "forearms", "abs", "obliques", "hip_flexors", "glutes", "quads", "hamstrings", "adductors",
  "abductors", "calves", "lower_leg", "neck", "cardio",
];

export const PATTERN_CODES: readonly MovementPattern[] = [
  "squat", "lunge", "hinge", "horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull", "elbow_flexion",
  "elbow_extension", "shoulder_raise", "chest_fly", "rear_delt", "knee_extension", "knee_flexion", "hip_abduction",
  "hip_adduction", "glute_isolation", "calf", "core_flexion", "core_anti_extension", "core_rotation", "core_lateral",
  "shrug", "forearm", "neck", "carry", "plyometric", "cardio", "mobility", "other",
];

export const BLOCK_KINDS: readonly BlockKind[] = ["warmup", "main", "superset", "circuit", "finisher", "cooldown"];

export const BODY_PARTS: readonly BodyPart[] = [
  "upper_arms", "upper_legs", "back", "waist", "chest", "shoulders", "lower_legs", "lower_arms", "cardio", "neck",
];

export const DIFFICULTIES: readonly (1 | 2 | 3)[] = [1, 2, 3];

/** Minúsculas y sin diacríticos: base de la búsqueda tolerante a acentos (§10.2.7). */
export function foldText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

/** Devuelve el primer elemento no indefinido de un array no vacío conocido en tiempo de compilación. */
export function first<T>(items: readonly T[]): T {
  const item = items[0];
  if (item === undefined) throw new Error("Lista vacía inesperada.");
  return item;
}

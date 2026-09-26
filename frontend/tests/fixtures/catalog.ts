import type { components } from "../../src/lib/api/schema";

type Schemas = components["schemas"];

export function exerciseFixture(id: string, nameEs: string, overrides: Partial<Schemas["ExerciseSummary"]> = {}): Schemas["ExerciseSummary"] {
  return {
    id,
    slug: `ejercicio-${id}`,
    name_es: nameEs,
    name_en: `exercise ${id}`,
    variant_label_es: null,
    body_part: "upper_legs",
    equipment_code: "barbell",
    target_muscle: "quads",
    movement_pattern: "squat",
    mechanic: "compound",
    role: "main",
    difficulty: 2,
    is_staple: true,
    laterality: "bilateral",
    load_type: "external",
    demo_sex: null,
    variant_group: `grupo-${id}`,
    media: {
      thumb_url: `/media/thumbs/${id}.jpg`,
      gif_url: `/media/gifs/${id}.gif`,
      width: 180,
      height: 180,
      attribution: { text: "© Gym visual", url: "https://gymvisual.com/" },
    },
    is_favorite: false,
    deprecated: false,
    ...overrides,
  };
}

export function prescriptionFixture(exerciseId: string, overrides: Partial<Schemas["ExercisePrescription"]> = {}): Schemas["ExercisePrescription"] {
  return {
    exercise_id: exerciseId,
    sets: 3,
    rep_min: 8,
    rep_max: 12,
    duration_s: null,
    per_side: false,
    target_rir: 2,
    tempo: "3-0-1-0",
    rest_s: 90,
    load_hint: null,
    notes_es: null,
    alternatives: [],
    ...overrides,
  };
}

export function planFixture(): Schemas["ProgramPlan"] {
  return {
    engine_version: "1.0.0",
    tables_hash: "0".repeat(64),
    seed: 7,
    input: {
      goal: "hypertrophy",
      days_per_week: 3,
      sex: "female",
      experience: "beginner",
      session_minutes: 60,
      equipment: { preset: "full_gym", items: [] },
      emphasis: "lower_glutes",
      avoid_muscles: [],
      avoid_patterns: [],
      preferred_days: [],
      weeks: 5,
      include_warmup: null,
      include_cooldown: null,
      include_cardio_finisher: null,
      favorite_exercise_ids: [],
      excluded_exercise_ids: [],
      seed: null,
    },
    split: ["full_a", "full_b", "full_a"],
    weeks: [
      {
        index: 0,
        phase: "accumulation",
        target_rir: 2,
        volume_ratio: 1,
        days: [
          {
            index: 0,
            template: "full_a",
            name_es: "Cuerpo completo A",
            focus_es: "Piernas y empuje",
            weekday: null,
            is_recovery: false,
            estimated_minutes: 55,
            blocks: [
              {
                order: 0,
                kind: "main",
                rounds: 1,
                rest_between_rounds_s: null,
                exercises: [
                  { ...prescriptionFixture("0043", { alternatives: ["0044"] }), order: 0, slot: null },
                ],
              },
            ],
            volume: [{ group: "quads", sets: 3 }],
          },
          {
            index: 1,
            template: "full_b",
            name_es: "Cuerpo completo B",
            focus_es: "Espalda y bisagra",
            weekday: null,
            is_recovery: false,
            estimated_minutes: 50,
            blocks: [
              {
                order: 0,
                kind: "main",
                rounds: 1,
                rest_between_rounds_s: null,
                exercises: [{ ...prescriptionFixture("0044"), order: 0, slot: null }],
              },
            ],
            volume: [{ group: "back", sets: 3 }],
          },
        ],
      },
    ],
    weekly_volume: [
      { group: "quads", target_min: 8, target_max: 14, planned_sets: 9 },
      { group: "back", target_min: 8, target_max: 14, planned_sets: 6 },
    ],
    warnings: [
      { code: "volume_out_of_range", message_es: "El volumen de espalda queda por debajo del rango.", week_index: 0, day_index: 1, exercise_id: null },
    ],
    rationale_es: ["Hemos elegido cuerpo completo porque entrenas 3 días."],
  };
}

export function previewFixture(): Schemas["GeneratorPreview"] {
  return {
    plan: planFixture(),
    exercises: [
      exerciseFixture("0043", "sentadilla con barra"),
      exerciseFixture("0044", "peso muerto rumano", { movement_pattern: "hinge", target_muscle: "hamstrings" }),
    ],
  };
}

export function programFixture(): Schemas["ProgramDetail"] {
  const plan = planFixture();
  return {
    id: "0192f09e-0000-7c2d-8e4f-5a6b7c8d9e00",
    name: "Cuerpo completo",
    source: "generated",
    goal: "hypertrophy",
    days_per_week: 2,
    weeks_count: 5,
    is_active: true,
    archived_at: null,
    generator_version: "1.0.0",
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-20T10:00:00Z",
    seed: 7,
    tables_hash: plan.tables_hash,
    generator_input: plan.input,
    weeks: [
      {
        id: "0192f09e-0000-7c2d-8e4f-000000000001",
        index: 0,
        phase: "accumulation",
        days: [
          {
            id: "0192f09e-0000-7c2d-8e4f-0000000000d1",
            index: 0,
            name: "Cuerpo completo A",
            focus: "Piernas",
            weekday: null,
            is_recovery: false,
            estimated_minutes: 55,
            blocks: [
              {
                id: "0192f09e-0000-7c2d-8e4f-0000000000b1",
                order: 0,
                kind: "main",
                rounds: 1,
                rest_between_rounds_s: null,
                exercises: [
                  { ...prescriptionFixture("0043"), id: "0192f09e-0000-7c2d-8e4f-0000000000e1", order: 0 },
                ],
              },
              {
                id: "0192f09e-0000-7c2d-8e4f-0000000000b2",
                order: 1,
                kind: "main",
                rounds: 1,
                rest_between_rounds_s: null,
                exercises: [
                  { ...prescriptionFixture("0044"), id: "0192f09e-0000-7c2d-8e4f-0000000000e2", order: 0 },
                ],
              },
            ],
          },
          {
            id: "0192f09e-0000-7c2d-8e4f-0000000000d2",
            index: 1,
            name: "Cuerpo completo B",
            focus: "Espalda",
            weekday: null,
            is_recovery: false,
            estimated_minutes: 50,
            blocks: [
              {
                id: "0192f09e-0000-7c2d-8e4f-0000000000b3",
                order: 0,
                kind: "main",
                rounds: 1,
                rest_between_rounds_s: null,
                exercises: [
                  { ...prescriptionFixture("0044"), id: "0192f09e-0000-7c2d-8e4f-0000000000e3", order: 0 },
                ],
              },
            ],
          },
        ],
      },
    ],
    weekly_volume: plan.weekly_volume,
    warnings: [],
    rationale_es: plan.rationale_es,
    exercises: [exerciseFixture("0043", "sentadilla con barra"), exerciseFixture("0044", "peso muerto rumano")],
  };
}

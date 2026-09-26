import type { components } from "../../../src/lib/api/schema";

type Schemas = components["schemas"];

export function makeExercise(id: string, name = `Ejercicio ${id}`): Schemas["ExerciseSummary"] {
  return {
    id,
    slug: `ej-${id}`,
    name_es: name,
    name_en: name,
    variant_label_es: null,
    body_part: "chest",
    equipment_code: "barbell",
    target_muscle: "chest",
    movement_pattern: "horizontal_push",
    mechanic: "compound",
    role: "main",
    difficulty: 1,
    is_staple: true,
    laterality: "bilateral",
    load_type: "external",
    demo_sex: null,
    variant_group: `g-${id}`,
    media: {
      thumb_url: `/media/thumbs/${id}.jpg`,
      gif_url: `/media/gifs/${id}.gif`,
      width: 180,
      height: 180,
      attribution: { text: "© Gym visual", url: "https://gymvisual.com/" },
    },
    is_favorite: false,
    deprecated: false,
  };
}

/** Día con dos ejercicios: 2 series de press (descanso 90 s) y 1 de remo (60 s). */
export function makeNextSession(): Schemas["NextSession"] {
  return {
    status: "scheduled",
    program_id: "p1",
    program_name: "Empuje/Tirón",
    week_index: 0,
    scheduled_date: "2026-09-26",
    day: {
      id: "d1",
      index: 0,
      name: "Día A",
      focus: null,
      weekday: null,
      is_recovery: false,
      estimated_minutes: 45,
      blocks: [
        {
          id: "b1",
          order: 0,
          kind: "main",
          rounds: 1,
          rest_between_rounds_s: null,
          exercises: [
            {
              id: "pe1",
              order: 0,
              exercise_id: "0001",
              sets: 2,
              rep_min: 8,
              rep_max: 10,
              duration_s: null,
              per_side: false,
              target_rir: 2,
              tempo: null,
              rest_s: 90,
              load_hint: null,
              notes_es: null,
              alternatives: ["0003"],
            },
            {
              id: "pe2",
              order: 1,
              exercise_id: "0002",
              sets: 1,
              rep_min: 10,
              rep_max: 12,
              duration_s: null,
              per_side: false,
              target_rir: 2,
              tempo: null,
              rest_s: 60,
              load_hint: null,
              notes_es: null,
              alternatives: [],
            },
          ],
        },
      ],
    },
    suggestions: [
      {
        program_exercise_id: "pe1",
        exercise_id: "0001",
        kind: "increase_load",
        suggested_weight_kg: 60,
        suggested_rep_min: 8,
        suggested_rep_max: 10,
        suggested_exercise_id: null,
        plates_per_side_kg: [20, 5],
        reason_es: "Sube 2,5 kg respecto a la última vez.",
        last_performance: {
          session_id: "s0",
          date: "2026-09-19",
          sets: [{ weight_kg: 57.5, reps: 10, rir: 2, duration_s: null }],
        },
        warmup_sets: [{ percent: 50, reps: 8, weight_kg: 30, plates_per_side_kg: [5] }],
      },
    ],
    exercises: [makeExercise("0001", "Press banca"), makeExercise("0002", "Remo con barra")],
  };
}

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import "../../src/i18n";
import { first } from "../../src/features/shared/enums";
import { EditorScreen } from "../../src/features/editor/EditorScreen";
import {
  dayHasErrors,
  editorReducer,
  initialEditorState,
  toDayEdit,
  validateExercise,
  type EditorState,
} from "../../src/features/editor/editorState";
import { server } from "../../src/mocks/server";
import { expectNoAxeViolations } from "../axe";
import { exerciseFixture, prescriptionFixture, programFixture } from "../fixtures/catalog";
import { installRadixPolyfills } from "../radixPolyfills";
import { renderWithRouter } from "../routes/renderWithRouter";

const PROGRAM_ID = "0192f09e-0000-7c2d-8e4f-5a6b7c8d9e00";

function stateFromFixture(): EditorState {
  const program = programFixture();
  return initialEditorState(program.weeks[0]?.days ?? []);
}

function keysOf(state: EditorState, dayIndex = 0): string[] {
  return (state.days[dayIndex]?.blocks ?? []).flatMap((block) => block.exercises.map((exercise) => exercise.exercise_id));
}

describe("editorReducer", () => {
  it("reordena dentro del día, entre bloques y con pasos de teclado; normaliza bloques", () => {
    let state = stateFromFixture();
    const day = state.days[0];
    if (day === undefined) throw new Error("sin día");
    const first = day.blocks[0]?.exercises[0]?.key ?? "";
    const second = day.blocks[1]?.exercises[0]?.key ?? "";

    state = editorReducer(state, { type: "move", dayKey: day.key, activeKey: first, overKey: second });
    // Dos bloques de un ejercicio: arrastrar reordena los bloques, no crea una superserie.
    expect(keysOf(state)).toEqual(["0044", "0043"]);
    expect(state.days[0]?.blocks.map((block) => block.kind)).toEqual(["main", "main"]);

    state = editorReducer(state, { type: "moveStep", dayKey: day.key, exerciseKey: first, delta: -1 });
    expect(keysOf(state)).toEqual(["0043", "0044"]);
    // Sin vecino no cambia el orden.
    const same = editorReducer(state, { type: "moveStep", dayKey: day.key, exerciseKey: first, delta: -1 });
    expect(keysOf(same)).toEqual(["0043", "0044"]);

    // En una superserie: mover dentro del bloque, soltar sobre un bloque agrupado y salir por el borde.
    state = editorReducer(state, { type: "mergeNext", dayKey: day.key, blockKey: state.days[0]?.blocks[0]?.key ?? "" });
    state = editorReducer(state, { type: "add", dayKey: day.key, exerciseId: "0050" });
    const added = state.days[0]?.blocks[1]?.exercises[0]?.key ?? "";
    const groupedFirst = state.days[0]?.blocks[0]?.exercises[0]?.key ?? "";
    state = editorReducer(state, { type: "move", dayKey: day.key, activeKey: added, overKey: groupedFirst });
    expect(keysOf(state)).toEqual(["0050", "0043", "0044"]);
    expect(state.days[0]?.blocks).toHaveLength(1);
    state = editorReducer(state, { type: "moveStep", dayKey: day.key, exerciseKey: added, delta: -1 });
    expect(state.days[0]?.blocks.map((block) => block.exercises.length)).toEqual([1, 2]);
    expect(keysOf(state)).toEqual(["0050", "0043", "0044"]);
    state = editorReducer(state, { type: "moveStep", dayKey: day.key, exerciseKey: added, delta: 1 });
    expect(keysOf(state)).toEqual(["0043", "0044", "0050"]);
    // Soltar sobre el contenedor de un bloque lo añade al final de ese bloque.
    const blockKey = state.days[0]?.blocks[0]?.key ?? "";
    const before = editorReducer(state, { type: "move", dayKey: day.key, activeKey: groupedFirst, overKey: "no-existe" });
    expect(before.days).toEqual(state.days);
    expect(editorReducer(state, { type: "move", dayKey: day.key, activeKey: "no-existe", overKey: blockKey }).days).toEqual(state.days);
    state = stateFromFixture();
    // Mover sobre sí mismo es no-op.
    const noop = editorReducer(state, { type: "move", dayKey: day.key, activeKey: first, overKey: first });
    expect(noop).toBe(state);
  });

  it("crea y separa superseries y circuitos", () => {
    let state = stateFromFixture();
    const day = state.days[0];
    if (day === undefined) throw new Error("sin día");
    const blockKey = day.blocks[0]?.key ?? "";
    state = editorReducer(state, { type: "mergeNext", dayKey: day.key, blockKey });
    expect(state.days[0]?.blocks).toHaveLength(1);
    expect(state.days[0]?.blocks[0]?.kind).toBe("superset");

    state = editorReducer(state, { type: "add", dayKey: day.key, exerciseId: "0050" });
    const merged = state.days[0]?.blocks[0]?.key ?? "";
    state = editorReducer(state, { type: "mergeNext", dayKey: day.key, blockKey: merged });
    expect(state.days[0]?.blocks[0]?.kind).toBe("circuit");
    expect(state.days[0]?.blocks[0]?.exercises).toHaveLength(3);

    state = editorReducer(state, { type: "block", dayKey: day.key, blockKey: state.days[0]?.blocks[0]?.key ?? "", patch: { rounds: 3 } });
    expect(state.days[0]?.blocks[0]?.rounds).toBe(3);

    state = editorReducer(state, { type: "split", dayKey: day.key, blockKey: state.days[0]?.blocks[0]?.key ?? "" });
    expect(state.days[0]?.blocks).toHaveLength(3);
    expect(state.days[0]?.blocks.every((block) => block.kind === "main")).toBe(true);
    // Separar un bloque de un solo ejercicio no hace nada.
    const single = state.days[0]?.blocks[0]?.key ?? "";
    expect(editorReducer(state, { type: "split", dayKey: day.key, blockKey: single }).days).toEqual(state.days);
  });

  it("deshacer y rehacer recorren el historial completo", () => {
    let state = stateFromFixture();
    const day = state.days[0];
    if (day === undefined) throw new Error("sin día");
    const exerciseKey = day.blocks[0]?.exercises[0]?.key ?? "";
    state = editorReducer(state, { type: "update", dayKey: day.key, exerciseKey, patch: { sets: 5 } });
    state = editorReducer(state, { type: "day", dayKey: day.key, patch: { name: "Nuevo" } });
    state = editorReducer(state, { type: "remove", dayKey: day.key, exerciseKey });
    expect(keysOf(state)).toEqual(["0044"]);

    state = editorReducer(state, { type: "undo" });
    expect(keysOf(state)).toEqual(["0043", "0044"]);
    state = editorReducer(state, { type: "undo" });
    expect(state.days[0]?.name).toBe("Cuerpo completo A");
    expect(state.days[0]?.blocks[0]?.exercises[0]?.sets).toBe(5);
    state = editorReducer(state, { type: "undo" });
    expect(state.days[0]?.blocks[0]?.exercises[0]?.sets).toBe(3);
    // Sin más historial, deshacer no cambia nada.
    expect(editorReducer(state, { type: "undo" })).toBe(state);

    state = editorReducer(state, { type: "redo" });
    expect(state.days[0]?.blocks[0]?.exercises[0]?.sets).toBe(5);
    state = editorReducer(state, { type: "redo" });
    state = editorReducer(state, { type: "redo" });
    expect(keysOf(state)).toEqual(["0044"]);
    expect(editorReducer(state, { type: "redo" })).toBe(state);

    // Una edición nueva descarta el futuro.
    state = editorReducer(state, { type: "undo" });
    state = editorReducer(state, { type: "day", dayKey: day.key, patch: { name: "Otro" } });
    expect(state.future).toHaveLength(0);
  });

  it("reset recarga los días y toDayEdit no envía claves de interfaz", () => {
    const program = programFixture();
    let state = stateFromFixture();
    state = editorReducer(state, { type: "reset", days: program.weeks[0]?.days ?? [] });
    expect(state.revision).toBe(0);
    const edit = toDayEdit(state.days[0] ?? (undefined as never), false);
    expect(edit.apply_to_all_weeks).toBe(false);
    expect(JSON.stringify(edit)).not.toContain('"key"');
    expect(edit.blocks[0]?.exercises[0]).toEqual(prescriptionFixture("0043"));
  });

  it("valida rangos de forma del contrato", () => {
    expect(validateExercise(prescriptionFixture("1"))).toEqual({});
    expect(validateExercise(prescriptionFixture("1", { sets: 0 }))).toHaveProperty("sets");
    expect(validateExercise(prescriptionFixture("1", { rep_min: 12, rep_max: 8 }))).toHaveProperty("reps");
    expect(validateExercise(prescriptionFixture("1", { rep_min: null }))).toHaveProperty("reps");
    expect(validateExercise(prescriptionFixture("1", { rep_min: null, rep_max: null, duration_s: 2 }))).toHaveProperty("duration");
    expect(validateExercise(prescriptionFixture("1", { rep_min: null, rep_max: null, duration_s: 30 }))).toEqual({});
    expect(validateExercise(prescriptionFixture("1", { target_rir: 9 }))).toHaveProperty("rir");
    expect(validateExercise(prescriptionFixture("1", { tempo: "3-1" }))).toHaveProperty("tempo");
    expect(validateExercise(prescriptionFixture("1", { rest_s: 601 }))).toHaveProperty("rest");

    const state = stateFromFixture();
    expect(dayHasErrors(state.days[0] ?? (undefined as never))).toBe(false);
    expect(dayHasErrors({ ...(state.days[0] ?? (undefined as never)), blocks: [] })).toBe(true);
  });
});

interface Puts {
  bodies: { dayId: string; body: unknown }[];
}

function mockProgram(options: { putResponse?: () => Response } = {}): Puts {
  const puts: Puts = { bodies: [] };
  server.use(
    http.get("/api/v1/programs/:id", () => HttpResponse.json(programFixture())),
    http.put("/api/v1/programs/:id/days/:dayId", async ({ request, params }) => {
      puts.bodies.push({ dayId: String(params["dayId"]), body: await request.json() });
      return options.putResponse?.() ?? HttpResponse.json({ ...programFixture(), warnings: [{ code: "volume_out_of_range", message_es: "Volumen de cuádriceps alto.", week_index: 0, day_index: 0, exercise_id: null }] });
    }),
    http.get("/api/v1/exercises", () => HttpResponse.json({ items: [exerciseFixture("0050", "sentadilla goblet")], next_cursor: null })),
  );
  return puts;
}

function names(): string[] {
  return screen
    .getAllByRole("button", { name: /^Arrastrar / })
    .map((button) => (button.getAttribute("aria-label") ?? "").replace("Arrastrar ", ""));
}

describe("EditorScreen", () => {
  beforeEach(installRadixPolyfills);

  it("muestra los días en pestañas con asas de arrastre accesibles y sin violaciones de a11y", async () => {
    mockProgram();
    const { container } = renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    expect(await screen.findByRole("heading", { name: "Editar «Cuerpo completo»" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(names()).toEqual(["sentadilla con barra", "peso muerto rumano"]);
    const handle = screen.getByRole("button", { name: "Arrastrar sentadilla con barra" });
    expect(handle).toHaveAttribute("aria-roledescription", "sortable");
    expect(handle).toHaveAttribute("tabindex", "0");
    expect(document.body.textContent).toContain("Para reordenar, pulsa espacio o Intro sobre el asa");
    await expectNoAxeViolations(container);
  });

  it("reordena con botones de teclado, valida en vivo con el motor y muestra sus avisos", async () => {
    const user = userEvent.setup();
    const puts = mockProgram();
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    await screen.findByRole("heading", { name: /Editar/ });

    await user.click(screen.getByRole("button", { name: "Bajar sentadilla con barra" }));
    expect(names()).toEqual(["peso muerto rumano", "sentadilla con barra"]);

    // Guardado diferido: sin pulsar nada, el motor valida tras la pausa.
    expect(await screen.findByText("Guardado y validado", {}, { timeout: 3000 })).toBeInTheDocument();
    expect(puts.bodies).toHaveLength(1);
    expect(puts.bodies[0]?.dayId).toBe("0192f09e-0000-7c2d-8e4f-0000000000d1");
    const body = puts.bodies[0]?.body as { apply_to_all_weeks: boolean; blocks: { kind: string; exercises: { exercise_id: string }[] }[] };
    expect(body.apply_to_all_weeks).toBe(true);
    expect(body.blocks.flatMap((block) => block.exercises.map((exercise) => exercise.exercise_id))).toEqual(["0044", "0043"]);
    expect(screen.getByText("Volumen de cuádriceps alto.")).toBeInTheDocument();
  });

  it("edita campos, bloquea el guardado con valores fuera de rango y permite deshacer y rehacer", async () => {
    const user = userEvent.setup();
    const puts = mockProgram();
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    await screen.findByRole("heading", { name: /Editar/ });

    const undo = screen.getByRole("button", { name: "Deshacer" });
    const redo = screen.getByRole("button", { name: "Rehacer" });
    expect(undo).toBeDisabled();

    const repMin = first(screen.getAllByLabelText("Reps mín."));
    await user.clear(repMin);
    await user.type(repMin, "20");
    expect(await screen.findByText("Repeticiones de 1 a 100, con el mínimo menor o igual que el máximo.")).toBeInTheDocument();
    expect(screen.getByText(/Hay campos con valores fuera de rango/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar ahora" }));
    expect(puts.bodies).toHaveLength(0);

    // Deshacer hasta el estado original, rehacer un paso y volver a deshacerlo.
    while (!(undo as HTMLButtonElement).disabled) await user.click(undo);
    expect(screen.queryByText(/Hay campos con valores fuera de rango/)).not.toBeInTheDocument();
    expect(redo).toBeEnabled();
    await user.click(redo);
    expect(undo).toBeEnabled();
    await user.click(undo);
    expect(undo).toBeDisabled();

    const rest = first(screen.getAllByLabelText("Descanso (s)"));
    await user.clear(rest);
    await user.type(rest, "120");
    const tempo = first(screen.getAllByLabelText("Tempo"));
    await user.clear(tempo);
    await user.type(tempo, "2");
    expect(screen.getByText("Formato 3-0-1-0 (dígitos o X).")).toBeInTheDocument();
    await user.clear(tempo);
    await user.type(tempo, "2-0-1-0");
    await user.click(screen.getByRole("checkbox", { name: /Aplicar los cambios del día a todas las semanas/ }));
    await user.click(screen.getByRole("button", { name: "Guardar ahora" }));
    await waitFor(() => {
      expect(puts.bodies.length).toBeGreaterThan(0);
    });
    const last = puts.bodies[puts.bodies.length - 1]?.body as { apply_to_all_weeks: boolean; blocks: { exercises: { rest_s: number; tempo: string }[] }[] };
    expect(last.apply_to_all_weeks).toBe(false);
    expect(last.blocks[0]?.exercises[0]).toMatchObject({ rest_s: 120, tempo: "2-0-1-0" });
  });

  it("crea y separa superseries y elimina ejercicios", async () => {
    const user = userEvent.setup();
    mockProgram();
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    await screen.findByRole("heading", { name: /Editar/ });

    await user.click(screen.getByRole("button", { name: "Unir con el siguiente (superserie)" }));
    expect(screen.getByRole("group", { name: "Superserie" })).toBeInTheDocument();
    expect(screen.getByLabelText("Rondas")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Separar ejercicios" }));
    expect(screen.queryByRole("group", { name: "Superserie" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Quitar peso muerto rumano" }));
    expect(names()).toEqual(["sentadilla con barra"]);
  });

  it("añade ejercicios desde el buscador lateral y muestra las reglas duras del motor (422)", async () => {
    const user = userEvent.setup();
    const puts = mockProgram({
      putResponse: () =>
        HttpResponse.json(
          {
            type: "/problems/plan-invalid",
            title: "Plan no válido",
            status: 422,
            code: "plan_invalid",
            violations: [{ code: "session_group_cap", message_es: "Máximo 10 series efectivas por grupo y sesión.", week_index: 0, day_index: 0, exercise_id: null }],
          },
          { status: 422 },
        ),
    });
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    await screen.findByRole("heading", { name: /Editar/ });

    await user.type(screen.getByLabelText("Buscar ejercicio"), "goblet");
    await user.click(await screen.findByRole("button", { name: "Añadir sentadilla goblet al día" }));
    expect(names()).toContain("sentadilla goblet");

    await user.click(screen.getByRole("button", { name: "Guardar ahora" }));
    const alert = await screen.findByText("El motor no admite estos cambios");
    expect(alert).toBeInTheDocument();
    expect(screen.getByText("Máximo 10 series efectivas por grupo y sesión.")).toBeInTheDocument();
    expect(screen.getByText("El motor ha rechazado los cambios")).toBeInTheDocument();
    expect(puts.bodies).toHaveLength(1);
  });

  it("cambia de día y muestra error si no se puede cargar el programa", async () => {
    const user = userEvent.setup();
    mockProgram();
    const { unmount } = renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    await screen.findByRole("heading", { name: /Editar/ });
    await user.click(screen.getByRole("tab", { name: "Cuerpo completo B" }));
    expect(within(screen.getByRole("tabpanel")).getByText("peso muerto rumano")).toBeVisible();
    unmount();

    server.use(http.get("/api/v1/programs/:id", () => HttpResponse.json({ title: "x", type: "x", status: 404, code: "not_found" }, { status: 404 })));
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: `/rutinas/${PROGRAM_ID}/editar` });
    expect(await screen.findByText("No se ha podido cargar la rutina.")).toBeInTheDocument();
  });
});

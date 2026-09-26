import "fake-indexeddb/auto";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../../../src/i18n";
import { applyKey } from "../../../src/features/session/keypad";
import {
  createInitialState,
  playerReducer,
  type PlayerState,
} from "../../../src/features/session/playerMachine";
import { SessionPlayer } from "../../../src/features/session/SessionPlayer";
import { SessionSummary } from "../../../src/features/session/SessionSummary";
import {
  closeDb,
  loadActiveState,
  readQueue,
  savePlayerState,
} from "../../../src/features/session/storage";
import { scheduler } from "../../../src/features/session/scheduler";
import { uuidv7 } from "../../../src/features/shared/uuid";
import { server } from "../../../src/mocks/server";
import { makeExercise, makeNextSession } from "./fixtures";

const T0 = Date.UTC(2026, 8, 26, 10, 0, 0);

function renderPlayer(onFinished = vi.fn(), onExit = vi.fn()): ReturnType<typeof render> {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SessionPlayer onFinished={onFinished} onExit={onExit} />
    </QueryClientProvider>,
  );
}

async function seed(mutate?: (s: PlayerState) => PlayerState): Promise<PlayerState> {
  const base = createInitialState({ sessionUuid: uuidv7(T0), now: T0, next: makeNextSession() });
  const state = mutate ? mutate(base) : base;
  await savePlayerState(state);
  return state;
}

beforeEach(async () => {
  await closeDb();
  indexedDB.deleteDatabase("forja");
  // Sin red por defecto en /sync: la cola debe conservar lo escrito.
  server.use(http.post("/api/v1/sync", () => HttpResponse.error()));
});
afterEach(() => {
  scheduler.stop();
  vi.useRealTimers();
});

describe("SessionNumberPad", () => {
  it("applyKey respeta coma decimal, ceros y longitud", () => {
    expect(applyKey("", ",", true)).toBe("0,");
    expect(applyKey("7,", ",", true)).toBe("7,");
    expect(applyKey("7", ",", false)).toBe("7");
    expect(applyKey("0", "5", true)).toBe("5");
    expect(applyKey("123456", "7", true)).toBe("123456");
    expect(applyKey("12", "back", true)).toBe("1");
  });
});

describe("SessionPlayer", () => {
  it("muestra el ejercicio con la atribución, objetivo y peso sugerido", async () => {
    await seed();
    renderPlayer();
    expect(await screen.findByRole("heading", { name: "Press banca" })).toBeInTheDocument();
    expect(screen.getByText("© Gym visual")).toBeInTheDocument();
    expect(screen.getByText("Serie 1 de 2")).toBeInTheDocument();
    expect(screen.getByTestId("weight-value")).toHaveTextContent("60");
    expect(screen.getByTestId("reps-value")).toHaveTextContent("10");
    expect(screen.getByText(/Discos por lado: 20 \+ 5 kg/)).toBeInTheDocument();
  });

  it("teclado: escribe peso y repeticiones, registra la serie y pasa a descanso", async () => {
    const user = userEvent.setup();
    await seed();
    renderPlayer();
    await screen.findByRole("heading", { name: "Press banca" });
    // Borra el peso sugerido y escribe 62,5
    const pad = screen.getByRole("group", { name: /Teclado numérico para Peso/ });
    await user.click(within(pad).getByRole("button", { name: "Borrar" }));
    await user.click(within(pad).getByRole("button", { name: "Borrar" }));
    for (const k of ["Tecla 6", "Tecla 2", "Coma decimal", "Tecla 5"]) {
      await user.click(within(pad).getByRole("button", { name: k }));
    }
    expect(screen.getByTestId("weight-value")).toHaveTextContent("62,5");
    await user.click(screen.getByRole("button", { name: "Serie hecha" }));

    expect(await screen.findByRole("region", { name: "Descanso" })).toBeInTheDocument();
    expect(screen.getByText("1:30")).toBeInTheDocument();
    await waitFor(async () => {
      const saved = await loadActiveState();
      expect(saved?.sets[0]).toMatchObject({ weightKg: 62.5, reps: 10, rir: 2 });
    });
    const queue = await readQueue();
    expect(queue.some((q) => q.op.op === "set_upsert")).toBe(true);
  });

  it("±15 s y saltar el descanso", async () => {
    const user = userEvent.setup();
    await seed();
    renderPlayer();
    await user.click(await screen.findByRole("button", { name: "Serie hecha" }));
    await screen.findByRole("region", { name: "Descanso" });
    await user.click(screen.getByRole("button", { name: "Sumar 15 segundos" }));
    await waitFor(() => {
      expect(screen.getByText("1:45")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Saltar descanso" }));
    expect(await screen.findByRole("button", { name: "Serie hecha" })).toBeInTheDocument();
    expect(screen.getByText("Serie 2 de 2")).toBeInTheDocument();
  });

  it("reanuda tras recargar: el descanso sigue contando desde la marca de tiempo guardada", async () => {
    const started = Date.now() - 30_000;
    await seed((s) =>
      playerReducer(s, { type: "LOG_SET", now: started, uuid: uuidv7(started), weightKg: 60, reps: 8, rir: 2 }),
    );
    renderPlayer();
    const region = await screen.findByRole("region", { name: "Descanso" });
    // 90 s de descanso − 30 s transcurridos ≈ 1:00 (nunca 1:30)
    expect(within(region).getByText(/^(1:00|0:59)$/)).toBeInTheDocument();
  });

  it("cuando el descanso termina, avisa y vuelve a la serie", async () => {
    const vibrate = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "vibrate", { value: vibrate, configurable: true });
    const started = Date.now() - 89_500;
    await seed((s) =>
      playerReducer(s, { type: "LOG_SET", now: started, uuid: uuidv7(started), weightKg: 60, reps: 8, rir: 2 }),
    );
    renderPlayer();
    expect(await screen.findByRole("button", { name: "Serie hecha" }, { timeout: 3000 })).toBeInTheDocument();
    expect(vibrate).toHaveBeenCalled();
  });

  it("calentamiento: registra series is_warmup sin iniciar descanso", async () => {
    const user = userEvent.setup();
    await seed();
    renderPlayer();
    await user.click(await screen.findByText("Calentamiento de aproximación"));
    await user.click(screen.getByRole("button", { name: "Hecha" }));
    await waitFor(async () => {
      expect((await loadActiveState())?.sets[0]?.isWarmup).toBe(true);
    });
    expect(screen.queryByRole("region", { name: "Descanso" })).not.toBeInTheDocument();
  });

  it("instrucciones paso a paso desde el detalle del ejercicio", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/exercises/:id", () =>
        HttpResponse.json({
          ...makeExercise("0001", "Press banca"),
          secondary_muscles: [],
          primary_group_muscle: "chest",
          equipment_group: "free_weights",
          instructions: { lang: "es", text: "x", steps: ["Túmbate en el banco", "Baja la barra al pecho"] },
          available_langs: ["es"],
          variants: [],
          source_commit: "abc",
          enrichment_version: 1,
          deprecated_at: null,
        }),
      ),
    );
    await seed();
    renderPlayer();
    await user.click(await screen.findByRole("button", { name: "Instrucciones paso a paso" }));
    expect(await screen.findByText("Baja la barra al pecho")).toBeInTheDocument();
  });

  it("cambio en caliente: sustituye el ejercicio por una alternativa", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/exercises/:id/alternatives", () =>
        HttpResponse.json({ items: [{ exercise: makeExercise("0003", "Press mancuernas"), score: 0.9 }] }),
      ),
    );
    await seed();
    renderPlayer();
    await user.click(await screen.findByRole("button", { name: "Cambiar ejercicio" }));
    await user.click(await screen.findByRole("button", { name: "Usar Press mancuernas" }));
    expect(await screen.findByRole("heading", { name: "Press mancuernas" })).toBeInTheDocument();
  });

  it("deshacer encola un set_delete", async () => {
    const user = userEvent.setup();
    await seed();
    renderPlayer();
    await user.click(await screen.findByRole("button", { name: "Serie hecha" }));
    await user.click(await screen.findByRole("button", { name: "Deshacer última serie" }));
    await waitFor(async () => {
      expect((await readQueue()).some((q) => q.op.op === "set_delete")).toBe(true);
    });
    expect(await screen.findByText("Serie 1 de 2")).toBeInTheDocument();
  });

  it("terminar: pide esfuerzo, cierra la sesión y encola su cierre", async () => {
    const user = userEvent.setup();
    const onFinished = vi.fn();
    await seed();
    renderPlayer(onFinished);
    await user.click(await screen.findByRole("button", { name: "Terminar sesión" }));
    await user.click(screen.getByRole("button", { name: "Esfuerzo 8" }));
    await user.click(screen.getByRole("button", { name: "Guardar y ver resumen" }));
    expect(onFinished).toHaveBeenCalledTimes(1);
    await waitFor(async () => {
      const q = await readQueue();
      const last = q[q.length - 1]?.op;
      expect(last).toMatchObject({ op: "session_upsert", status: "completed", perceived_effort: 8 });
    });
  });

  it("sin sesión activa ofrece volver a Hoy", async () => {
    const onExit = vi.fn();
    renderPlayer(vi.fn(), onExit);
    await userEvent.click(await screen.findByRole("button", { name: "Volver a Hoy" }));
    expect(onExit).toHaveBeenCalled();
  });

  it("pide el Wake Lock mientras dura la sesión y lo libera al salir", async () => {
    const release = vi.fn().mockResolvedValue(undefined);
    const request = vi.fn().mockResolvedValue({ release });
    Object.defineProperty(navigator, "wakeLock", { value: { request }, configurable: true });
    await seed();
    const { unmount } = renderPlayer();
    await screen.findByRole("heading", { name: "Press banca" });
    await waitFor(() => {
      expect(request).toHaveBeenCalledWith("screen");
    });
    unmount();
    await waitFor(() => {
      expect(release).toHaveBeenCalled();
    });
    Reflect.deleteProperty(navigator, "wakeLock");
  });

  it("no tiene violaciones de accesibilidad (axe)", async () => {
    await seed();
    const { container } = renderPlayer();
    await screen.findByRole("heading", { name: "Press banca" });
    const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(results.violations.map((v) => v.id)).toEqual([]);
  });
});

describe("SessionSummary", () => {
  it("muestra totales locales offline y los récords del servidor cuando hay sincronización", async () => {
    let s = createInitialState({ sessionUuid: uuidv7(T0), now: T0, next: makeNextSession() });
    s = playerReducer(s, { type: "LOG_SET", now: T0 + 60_000, uuid: uuidv7(T0), weightKg: 60, reps: 10, rir: 2 });
    s = playerReducer(s, { type: "FINISH", now: T0 + 30 * 60_000, perceivedEffort: 7 });
    await savePlayerState(s);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const view = render(
      <QueryClientProvider client={client}>
        <SessionSummary sessionUuid={s.sessionUuid} onExit={vi.fn()} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("30 min")).toBeInTheDocument();
    expect(screen.getByText("600 kg")).toBeInTheDocument();
    expect(screen.getByText(/Resumen calculado en este dispositivo/)).toBeInTheDocument();
    expect(screen.getByText("7/10")).toBeInTheDocument();

    // Al sincronizar, el servidor devuelve récords.
    await savePlayerState({ ...s, serverId: "srv-1" });
    server.use(
      http.post("/api/v1/sessions/:id/finish", () =>
        HttpResponse.json({
          session: {},
          duration_s: 1800,
          total_sets: 1,
          total_reps: 10,
          volume_kg: 600,
          exercises_completed: 1,
          new_records: [
            {
              id: "r1", exercise_id: "0001", exercise_name_es: "Press banca", kind: "e1rm", value: 80,
              weight_kg: 60, reps: 10, achieved_at: "2026-09-26T10:30:00Z", session_id: "srv-1", set_id: null,
            },
          ],
        }),
      ),
    );
    view.rerender(
      <QueryClientProvider client={client}>
        <SessionSummary sessionUuid={s.sessionUuid} onExit={vi.fn()} />
      </QueryClientProvider>,
    );
    await client.invalidateQueries({ queryKey: ["session-summary"] });
    expect(await screen.findByText(/1RM estimado/, undefined, { timeout: 3000 })).toBeInTheDocument();
  });
});

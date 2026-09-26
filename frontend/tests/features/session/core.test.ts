import "fake-indexeddb/auto";

import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createInitialState,
  currentSlot,
  localVolumeKg,
  playerReducer,
  restRemainingMs,
  type PlayerState,
} from "../../../src/features/session/playerMachine";
import {
  closeDb,
  enqueueOperation,
  loadActiveState,
  queueLength,
  readQueue,
  savePlayerState,
  takeRejections,
} from "../../../src/features/session/storage";
import {
  backoffDelayMs,
  flushQueue,
  SYNC_BATCH_SIZE,
  SyncScheduler,
} from "../../../src/features/session/syncQueue";
import { uuidv7 } from "../../../src/features/shared/uuid";
import { server } from "../../../src/mocks/server";
import { makeExercise, makeNextSession } from "./fixtures";

const T0 = Date.UTC(2026, 8, 26, 10, 0, 0);

function start(): PlayerState {
  return createInitialState({ sessionUuid: uuidv7(T0), now: T0, next: makeNextSession() });
}

function log(state: PlayerState, now: number, weight = 60, reps = 8): PlayerState {
  return playerReducer(state, { type: "LOG_SET", now, uuid: uuidv7(now), weightKg: weight, reps, rir: 2 });
}

beforeEach(async () => {
  await closeDb();
  indexedDB.deleteDatabase("forja");
});
afterEach(() => vi.useRealTimers());

describe("playerReducer (máquina de estados)", () => {
  it("aplana el día en ejercicios y empieza en 'exercising'", () => {
    const s = start();
    expect(s.slots.map((x) => x.exercise.id)).toEqual(["0001", "0002"]);
    expect(s.phase).toBe("exercising");
    expect(currentSlot(s)?.suggestion?.suggested_weight_kg).toBe(60);
  });

  it("registrar una serie entra en descanso con marcas de tiempo y avanza", () => {
    const s = log(start(), T0 + 1000);
    expect(s.phase).toBe("resting");
    expect(s.setIndex).toBe(1);
    expect(s.rest).toEqual({ startedAt: T0 + 1000, endsAt: T0 + 1000 + 90_000 });
    expect(restRemainingMs(s.rest, T0 + 31_000)).toBe(60_000);
    expect(restRemainingMs(s.rest, T0 + 999_999)).toBe(0);
  });

  it("±15 s y saltar; nunca deja el fin en el pasado", () => {
    let s = log(start(), T0);
    s = playerReducer(s, { type: "REST_ADJUST", deltaMs: 15_000, now: T0 + 1000 });
    expect(s.rest?.endsAt).toBe(T0 + 105_000);
    s = playerReducer(s, { type: "REST_ADJUST", deltaMs: -500_000, now: T0 + 2000 });
    expect(s.rest?.endsAt).toBe(T0 + 2000);
    s = playerReducer(s, { type: "REST_DONE" });
    expect(s.phase).toBe("exercising");
    expect(s.rest).toBeNull();
  });

  it("pasa al siguiente ejercicio y termina tras la última serie", () => {
    let s = log(start(), T0);
    s = playerReducer(s, { type: "REST_DONE" });
    s = log(s, T0 + 1);
    expect(s.slotIndex).toBe(1);
    expect(s.setIndex).toBe(0);
    s = playerReducer(s, { type: "REST_DONE" });
    s = log(s, T0 + 2, 40, 10);
    expect(s.phase).toBe("finished");
    expect(localVolumeKg(s)).toBe(60 * 8 * 2 + 40 * 10);
    const done = playerReducer(s, { type: "FINISH", now: T0 + 3, perceivedEffort: 7 });
    expect(done.phase).toBe("completed");
    expect(done.perceivedEffort).toBe(7);
  });

  it("el calentamiento no avanza series de trabajo ni inicia descanso", () => {
    const s = playerReducer(start(), {
      type: "LOG_SET", now: T0, uuid: uuidv7(T0), weightKg: 30, reps: 8, rir: null, isWarmup: true,
    });
    expect(s.phase).toBe("exercising");
    expect(s.setIndex).toBe(0);
    expect(s.sets[0]?.isWarmup).toBe(true);
    expect(localVolumeKg(s)).toBe(0);
  });

  it("cambio en caliente sustituye el ejercicio actual y deshacer retrocede", () => {
    const swapped = playerReducer(start(), {
      type: "SWAP_EXERCISE",
      exercise: { ...makeExercise("0003"), name_es: "Press mancuernas" },
    });
    expect(currentSlot(swapped)?.exercise.id).toBe("0003");
    const logged = log(swapped, T0);
    const undone = playerReducer(logged, { type: "UNDO_LAST" });
    expect(undone.sets).toHaveLength(0);
    expect(undone.setIndex).toBe(0);
    expect(undone.phase).toBe("exercising");
  });

  it("ir a otro ejercicio y guardar el id de servidor", () => {
    let s = playerReducer(start(), { type: "GO_TO_SLOT", index: 1 });
    expect(s.slotIndex).toBe(1);
    s = playerReducer(s, { type: "GO_TO_SLOT", index: 9 });
    expect(s.slotIndex).toBe(1);
    s = playerReducer(s, { type: "SET_SERVER_ID", serverId: "srv" });
    expect(s.serverId).toBe("srv");
  });
});

describe("persistencia en IndexedDB", () => {
  it("la sesión activa se recupera tras 'recargar' (cerrar y reabrir la base)", async () => {
    const s = log(start(), T0);
    await savePlayerState(s);
    await closeDb();
    const restored = await loadActiveState();
    expect(restored?.sessionUuid).toBe(s.sessionUuid);
    expect(restored?.sets).toHaveLength(1);
    expect(restored?.rest?.endsAt).toBe(s.rest?.endsAt);
  });

  it("una sesión completada deja de ser la activa", async () => {
    const s = start();
    const done = playerReducer(s, { type: "FINISH", now: T0, perceivedEffort: null });
    await savePlayerState(s);
    await savePlayerState(done);
    expect(await loadActiveState()).toBeUndefined();
  });
});

describe("cola offline y /sync", () => {
  const sessionOp = (uuid: string): Parameters<typeof enqueueOperation>[0] => ({
    op: "session_upsert",
    client_uuid: uuid,
    program_day_id: null,
    name: "x",
    started_at: new Date(T0).toISOString(),
    finished_at: null,
    status: "in_progress",
    perceived_effort: null,
    notes: null,
    updated_at: new Date(T0).toISOString(),
  });

  it("offline → online: la cola se conserva al fallar y se vacía al volver la red", async () => {
    const uuid = uuidv7(T0);
    await enqueueOperation(sessionOp(uuid));
    await enqueueOperation({ op: "set_delete", client_uuid: uuidv7(T0 + 1), deleted_at: new Date(T0).toISOString() });
    server.use(http.post("/api/v1/sync", () => HttpResponse.error()));
    const offline = await flushQueue();
    expect(offline.failed).toBe(true);
    expect(await queueLength()).toBe(2);

    server.use(
      http.post("/api/v1/sync", async ({ request }) => {
        const body = (await request.json()) as { operations: { op: string; client_uuid: string }[] };
        return HttpResponse.json({
          server_time: new Date(T0).toISOString(),
          results: body.operations.map((o, index) => ({
            index,
            op: o.op,
            client_uuid: o.client_uuid,
            status: index === 0 ? "applied" : "duplicate",
            server_id: null,
            problem: null,
          })),
        });
      }),
    );
    const online = await flushQueue();
    expect(online).toMatchObject({ sent: 2, applied: 1, duplicate: 1, failed: false });
    expect(await queueLength()).toBe(0);
  });

  it("las operaciones rechazadas salen de la cola y se registran; un fallo no aborta el lote", async () => {
    await enqueueOperation(sessionOp(uuidv7(T0)));
    await enqueueOperation(sessionOp(uuidv7(T0 + 1)));
    server.use(
      http.post("/api/v1/sync", () =>
        HttpResponse.json({
          server_time: new Date(T0).toISOString(),
          results: [
            {
              index: 0, op: "session_upsert", client_uuid: "a", status: "rejected", server_id: null,
              problem: { type: "/x", title: "Ejercicio inexistente", status: 422 },
            },
            { index: 1, op: "session_upsert", client_uuid: "b", status: "superseded", server_id: null, problem: null },
          ],
        }),
      ),
    );
    const out = await flushQueue();
    expect(out).toMatchObject({ rejected: 1, superseded: 1 });
    expect(await queueLength()).toBe(0);
    const rejections = await takeRejections();
    expect(rejections[0]?.title).toBe("Ejercicio inexistente");
    expect(await takeRejections()).toEqual([]);
  });

  it("envía en lotes de 500 como máximo y guarda el id de servidor de la sesión", async () => {
    const s = start();
    await savePlayerState(s);
    await enqueueOperation(sessionOp(s.sessionUuid));
    for (let i = 0; i < SYNC_BATCH_SIZE; i += 1) {
      await enqueueOperation({ op: "set_delete", client_uuid: uuidv7(T0 + i), deleted_at: new Date(T0).toISOString() });
    }
    const sizes: number[] = [];
    server.use(
      http.post("/api/v1/sync", async ({ request }) => {
        const body = (await request.json()) as { operations: { op: string; client_uuid: string }[] };
        sizes.push(body.operations.length);
        return HttpResponse.json({
          server_time: new Date(T0).toISOString(),
          results: body.operations.map((o, index) => ({
            index, op: o.op, client_uuid: o.client_uuid, status: "applied",
            server_id: o.op === "session_upsert" ? "srv-1" : null, problem: null,
          })),
        });
      }),
    );
    await flushQueue();
    expect(sizes).toEqual([500, 1]);
    expect((await loadActiveState())?.serverId).toBe("srv-1");
    expect(await readQueue()).toEqual([]);
  });

  it("un 4xx del lote entero conserva la cola para reintentar", async () => {
    await enqueueOperation(sessionOp(uuidv7(T0)));
    server.use(http.post("/api/v1/sync", () => HttpResponse.json({ type: "/x", title: "no", status: 401 }, { status: 401 })));
    expect((await flushQueue()).failed).toBe(true);
    expect(await queueLength()).toBe(1);
  });
});

describe("reintento exponencial", () => {
  it("1 s, 2 s, 4 s… con tope de 5 min y jitter acotado", () => {
    expect(backoffDelayMs(0, 0.5)).toBe(1000);
    expect(backoffDelayMs(1, 0.5)).toBe(2000);
    expect(backoffDelayMs(2, 0.5)).toBe(4000);
    expect(backoffDelayMs(20, 0.99)).toBe(300_000);
    expect(backoffDelayMs(0, 0)).toBe(800);
  });

  it("el planificador reintenta con temporizadores simulados hasta que el envío funciona", async () => {
    vi.useFakeTimers();
    const flush = vi
      .fn<() => Promise<Awaited<ReturnType<typeof flushQueue>>>>()
      .mockResolvedValueOnce({ sent: 0, applied: 0, duplicate: 0, superseded: 0, rejected: 0, failed: true })
      .mockResolvedValueOnce({ sent: 0, applied: 0, duplicate: 0, superseded: 0, rejected: 0, failed: true })
      .mockResolvedValue({ sent: 1, applied: 1, duplicate: 0, superseded: 0, rejected: 0, failed: false });
    const scheduler = new SyncScheduler(flush, () => 0.5, () => true);
    scheduler.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(flush).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1000);
    expect(flush).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2000);
    expect(flush).toHaveBeenCalledTimes(3);
    await vi.advanceTimersByTimeAsync(600_000);
    expect(flush).toHaveBeenCalledTimes(3);
    scheduler.stop();
  });

  it("sin conexión no envía y reintenta después", async () => {
    vi.useFakeTimers();
    let online = false;
    const flush = vi.fn().mockResolvedValue({ sent: 0, applied: 0, duplicate: 0, superseded: 0, rejected: 0, failed: false });
    const scheduler = new SyncScheduler(flush, () => 0.5, () => online);
    scheduler.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(flush).not.toHaveBeenCalled();
    online = true;
    await vi.advanceTimersByTimeAsync(1000);
    expect(flush).toHaveBeenCalledTimes(1);
    scheduler.stop();
  });
});

describe("uuidv7", () => {
  it("tiene versión 7, variante RFC y es ordenable por tiempo", () => {
    const a = uuidv7(T0);
    const b = uuidv7(T0 + 5000);
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a < b).toBe(true);
  });
});

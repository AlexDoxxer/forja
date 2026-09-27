import { api } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import {
  addRejection,
  enqueueOperation,
  getMeta,
  loadPlayerState,
  readQueue,
  removeFromQueue,
  savePlayerState,
  setMeta,
  type QueueItem as StoredQueueItem,
  type SyncOperation,
} from "./storage";

export type SyncResponse = components["schemas"]["SyncResponse"];

/** Lote máximo por petición (ADR 0006). */
export const SYNC_BATCH_SIZE = 500;
export const BACKOFF_BASE_MS = 1000;
export const BACKOFF_MAX_MS = 5 * 60 * 1000;

/**
 * Reintento exponencial con *jitter* (1 s, 2 s, 4 s… máx. 5 min; ADR 0006). `random` en [0, 1).
 * El jitter reparte el ±20 % pero nunca supera el máximo.
 */
export function backoffDelayMs(attempt: number, random: number = Math.random()): number {
  const base = Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** Math.max(0, attempt));
  const jittered = base * (0.8 + 0.4 * random);
  return Math.min(BACKOFF_MAX_MS, Math.round(jittered));
}

const SKEW_KEY = "clockSkewMs";
let clockSkewMs = 0;

/** Ahora, corregido con el desfase con el servidor (`SyncResponse.server_time`). */
export function syncedNow(): number {
  return Date.now() + clockSkewMs;
}

export async function restoreClockSkew(): Promise<void> {
  clockSkewMs = (await getMeta<number>(SKEW_KEY)) ?? 0;
}

async function updateSkew(serverTime: string): Promise<void> {
  const server = Date.parse(serverTime);
  if (Number.isNaN(server)) return;
  clockSkewMs = server - Date.now();
  await setMeta(SKEW_KEY, clockSkewMs);
}

export interface FlushOutcome {
  sent: number;
  applied: number;
  duplicate: number;
  superseded: number;
  rejected: number;
  /** `true` si el lote no llegó al servidor (sin red o error 5xx) y hay que reintentar. */
  failed: boolean;
}

const EMPTY: FlushOutcome = { sent: 0, applied: 0, duplicate: 0, superseded: 0, rejected: 0, failed: false };

/** Guarda el `id` de servidor de una sesión en su estado local (para pedir el resumen). */
async function rememberServerId(clientUuid: string, serverId: string): Promise<void> {
  const state = await loadPlayerState(clientUuid);
  if (state !== undefined && state.serverId !== serverId) {
    await savePlayerState({ ...state, serverId });
  }
}

/**
 * Envía la cola a `POST /sync` por lotes. Cada operación se resuelve por separado: las
 * aplicadas, duplicadas o superadas salen de la cola; las rechazadas también, pero se
 * registran para mostrárselas a la persona. Un error de red o 5xx deja la cola intacta.
 */
export async function flushQueue(): Promise<FlushOutcome> {
  const outcome: FlushOutcome = { ...EMPTY };
  const items = await readQueue();
  for (let start = 0; start < items.length; start += SYNC_BATCH_SIZE) {
    const failed = await sendBatch(items.slice(start, start + SYNC_BATCH_SIZE), outcome);
    if (failed) return { ...outcome, failed: true };
  }
  return outcome;
}

/** Envía un lote; devuelve `true` si hay que reintentar más tarde (red, 5xx, 401, 413…). */
async function sendBatch(batch: readonly Required<StoredQueueItem>[], outcome: FlushOutcome): Promise<boolean> {
  let response: SyncResponse;
  try {
    const result = await api.POST("/sync", { body: { operations: batch.map((i) => i.op) } });
    if (result.data === undefined) {
      if (result.response.status === 422) {
        // Un lote con una operación inválida no debe bloquear la cola para siempre: se aísla
        // la culpable enviando de una en una; la que siga fallando se descarta con aviso.
        if (batch.length > 1) {
          for (const item of batch) {
            if (await sendBatch([item], outcome)) return true;
          }
          return false;
        }
        const [item] = batch;
        if (item !== undefined) {
          outcome.rejected += 1;
          await addRejection({
            op: item.op.op,
            clientUuid: "client_uuid" in item.op ? item.op.client_uuid : "",
            title: "Operación rechazada por datos no válidos",
            at: Date.now(),
          });
          await removeFromQueue([item.seq]);
        }
        return false;
      }
      // 4xx del lote entero (sesión caducada, 413…): se reintentará; no se pierde nada.
      return true;
    }
    response = result.data;
  } catch {
    return true;
  }
  outcome.sent += batch.length;
  await updateSkew(response.server_time);
  const done: number[] = [];
  for (const result of response.results) {
    const item = batch[result.index];
    if (item === undefined) continue;
    done.push(item.seq);
    outcome[result.status] += 1;
    if (result.status === "rejected") {
      await addRejection({
        op: result.op,
        clientUuid: result.client_uuid,
        title: result.problem?.title ?? "Operación rechazada",
        at: Date.now(),
      });
    } else if (result.op === "session_upsert" && result.server_id !== null) {
      await rememberServerId(result.client_uuid, result.server_id);
    }
  }
  // Operaciones sin resultado (respuesta incompleta) se conservan para el siguiente intento.
  await removeFromQueue(done);
  return false;
}

export { enqueueOperation };
export type { SyncOperation };

/** Planificador con reintento exponencial: `online`, sondeo y mensaje de Background Sync. */
export class SyncScheduler {
  private attempt = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private running = false;
  private stopped = true;
  private listeners = new Set<(o: FlushOutcome) => void>();

  constructor(
    private readonly flush: () => Promise<FlushOutcome> = flushQueue,
    private readonly random: () => number = Math.random,
    private readonly isOnline: () => boolean = () => navigator.onLine,
  ) {}

  subscribe(fn: (o: FlushOutcome) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  start(): void {
    this.stopped = false;
    void this.trigger();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  /** Pide un envío ahora (nueva escritura, vuelta de la red, Background Sync). */
  async trigger(): Promise<FlushOutcome> {
    if (this.stopped || this.running) return EMPTY;
    if (!this.isOnline()) return this.scheduleRetry(EMPTY);
    this.running = true;
    try {
      const outcome = await this.flush();
      for (const l of this.listeners) l(outcome);
      if (outcome.failed) return this.scheduleRetry(outcome);
      this.attempt = 0;
      return outcome;
    } finally {
      this.running = false;
    }
  }

  private scheduleRetry(outcome: FlushOutcome): FlushOutcome {
    if (this.timer !== null) clearTimeout(this.timer);
    const delay = backoffDelayMs(this.attempt, this.random());
    this.attempt += 1;
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.trigger();
    }, delay);
    return outcome;
  }
}

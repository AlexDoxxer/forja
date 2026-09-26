import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import type { components } from "../../lib/api/schema";
import type { PlayerState } from "./playerMachine";

export type SyncOperation = components["schemas"]["SyncOperation"];

export interface QueueItem {
  seq?: number;
  op: SyncOperation;
  enqueuedAt: number;
}

export interface Rejection {
  id?: number;
  op: SyncOperation["op"];
  clientUuid: string;
  title: string;
  at: number;
}

interface ForjaDb extends DBSchema {
  /** Estado del reproductor por sesión (ADR 0006: nunca `localStorage`). */
  player: { key: string; value: PlayerState };
  /** Cola de escrituras offline, en orden de inserción. */
  queue: { key: number; value: QueueItem };
  /** Operaciones rechazadas por el servidor, pendientes de mostrar a la persona. */
  rejections: { key: number; value: Rejection };
  /** Pares clave/valor (sesión activa, desfase de reloj, listas marcadas…). */
  meta: { key: string; value: unknown };
}

const DB_NAME = "forja";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<ForjaDb>> | null = null;

export function getDb(): Promise<IDBPDatabase<ForjaDb>> {
  dbPromise ??= openDB<ForjaDb>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      db.createObjectStore("player", { keyPath: "sessionUuid" });
      db.createObjectStore("queue", { keyPath: "seq", autoIncrement: true });
      db.createObjectStore("rejections", { keyPath: "id", autoIncrement: true });
      db.createObjectStore("meta");
    },
  });
  return dbPromise;
}

/** Cierra la conexión y olvida la promesa (los tests borran la base entre casos). */
export async function closeDb(): Promise<void> {
  if (dbPromise !== null) {
    const db = await dbPromise;
    db.close();
    dbPromise = null;
  }
}

const ACTIVE_KEY = "activeSession";

export async function savePlayerState(state: PlayerState): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(["player", "meta"], "readwrite");
  await tx.objectStore("player").put(state);
  if (state.phase === "completed") {
    // La sesión cerrada se conserva para el resumen, pero deja de ser la «activa».
    const active = await tx.objectStore("meta").get(ACTIVE_KEY);
    if (active === state.sessionUuid) await tx.objectStore("meta").delete(ACTIVE_KEY);
  } else {
    await tx.objectStore("meta").put(state.sessionUuid, ACTIVE_KEY);
  }
  await tx.done;
}

export async function loadPlayerState(sessionUuid: string): Promise<PlayerState | undefined> {
  const db = await getDb();
  return db.get("player", sessionUuid);
}

/** Sesión en curso que sobrevivió a una recarga o cierre, si la hay. */
export async function loadActiveState(): Promise<PlayerState | undefined> {
  const db = await getDb();
  const uuid = await db.get("meta", ACTIVE_KEY);
  return typeof uuid === "string" ? db.get("player", uuid) : undefined;
}

export async function discardPlayerState(sessionUuid: string): Promise<void> {
  const db = await getDb();
  await db.delete("player", sessionUuid);
  const active = await db.get("meta", ACTIVE_KEY);
  if (active === sessionUuid) await db.delete("meta", ACTIVE_KEY);
}

export async function enqueueOperation(op: SyncOperation, now: number = Date.now()): Promise<void> {
  const db = await getDb();
  await db.add("queue", { op, enqueuedAt: now });
}

export async function readQueue(): Promise<Required<QueueItem>[]> {
  const db = await getDb();
  const items = await db.getAll("queue");
  return items.filter((i): i is Required<QueueItem> => i.seq !== undefined);
}

export async function removeFromQueue(seqs: number[]): Promise<void> {
  const db = await getDb();
  const tx = db.transaction("queue", "readwrite");
  await Promise.all(seqs.map((s) => tx.store.delete(s)));
  await tx.done;
}

export async function queueLength(): Promise<number> {
  const db = await getDb();
  return db.count("queue");
}

export async function addRejection(rejection: Rejection): Promise<void> {
  const db = await getDb();
  await db.add("rejections", rejection);
}

export async function takeRejections(): Promise<Rejection[]> {
  const db = await getDb();
  const all = await db.getAll("rejections");
  await db.clear("rejections");
  return all;
}

export async function getMeta<T>(key: string): Promise<T | undefined> {
  const db = await getDb();
  return (await db.get("meta", key)) as T | undefined;
}

export async function setMeta(key: string, value: unknown): Promise<void> {
  const db = await getDb();
  await db.put("meta", value, key);
}

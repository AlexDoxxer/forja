import { SyncScheduler } from "./syncQueue";

/** Planificador único de la cola offline para toda la app. */
export const scheduler = new SyncScheduler();

let attached = false;

/**
 * Conecta el planificador al ciclo de vida del navegador: envío al arrancar, al recuperar la
 * red y cuando el service worker avisa de un Background Sync (Safari no lo soporta: ADR 0006).
 */
export function attachSyncTriggers(): () => void {
  if (attached) return () => undefined;
  attached = true;
  scheduler.start();
  const unsubscribe = scheduler.subscribe((outcome) => {
    if (outcome.failed) void requestBackgroundSync();
  });
  const onOnline = (): void => void scheduler.trigger();
  const onMessage = (event: MessageEvent): void => {
    const data: unknown = event.data;
    if (typeof data === "object" && data !== null && "type" in data && data.type === "FLUSH_QUEUE") {
      void scheduler.trigger();
    }
  };
  window.addEventListener("online", onOnline);
  if ("serviceWorker" in navigator) navigator.serviceWorker.addEventListener("message", onMessage);
  return () => {
    attached = false;
    unsubscribe();
    scheduler.stop();
    window.removeEventListener("online", onOnline);
    if ("serviceWorker" in navigator) navigator.serviceWorker.removeEventListener("message", onMessage);
  };
}

interface SyncRegistration {
  sync?: { register: (tag: string) => Promise<void> };
}

/** Pide un Background Sync donde exista (Chromium); en el resto lo cubre el evento `online`. */
export async function requestBackgroundSync(): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  try {
    const reg = (await navigator.serviceWorker.ready) as ServiceWorkerRegistration & SyncRegistration;
    await reg.sync?.register("forja-sync");
  } catch {
    // No disponible: el planificador con reintento exponencial sigue funcionando.
  }
}

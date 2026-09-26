import { api, unwrapApi } from "../lib/api/client";

/** Mensaje al service worker para precachear medios (miniaturas y GIFs) del programa activo. */
export interface PrecacheMessage {
  type: "PRECACHE_MEDIA";
  urls: string[];
}

/** URLs de miniatura y GIF de los ejercicios del programa activo, sin duplicados. */
export async function collectActiveProgramMedia(): Promise<string[]> {
  const programs = unwrapApi(await api.GET("/programs", { params: { query: { limit: 50 } } }));
  const active = programs.items.find((p) => p.is_active);
  if (active === undefined) return [];
  const detail = unwrapApi(
    await api.GET("/programs/{program_id}", { params: { path: { program_id: active.id } } }),
  );
  const urls = new Set<string>();
  for (const exercise of detail.exercises) {
    urls.add(exercise.media.thumb_url);
    urls.add(exercise.media.gif_url);
  }
  return [...urls];
}

/** `true` si hay un service worker que pueda cachear medios. */
export function offlineSupported(): boolean {
  return "serviceWorker" in navigator && "caches" in globalThis;
}

/**
 * Pide al service worker que guarde las URLs y espera su confirmación (número de medios en
 * caché). Los medios se guardan tal cual llegan del servidor, sin transformarlos (§2.1).
 */
export async function requestPrecache(urls: string[]): Promise<number> {
  const registration = await navigator.serviceWorker.ready;
  const worker = registration.active;
  if (worker === null) throw new Error("No hay un service worker activo.");
  return new Promise<number>((resolve, reject) => {
    const channel = new MessageChannel();
    channel.port1.onmessage = (event: MessageEvent<{ ok: boolean; cached: number }>) => {
      if (event.data.ok) resolve(event.data.cached);
      else reject(new Error("El service worker no pudo guardar los medios."));
    };
    const message: PrecacheMessage = { type: "PRECACHE_MEDIA", urls };
    worker.postMessage(message, [channel.port2]);
  });
}

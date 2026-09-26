import { attachSyncTriggers } from "../features/session/scheduler";

/** Registra el service worker (solo en producción; en desarrollo MSW usa su propio worker). */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch (error) {
    console.error("No se pudo registrar el service worker:", error);
    return null;
  }
}

/** Arranque de las piezas PWA: service worker y cola offline (`/sync`). */
export function bootPwa(): void {
  attachSyncTriggers();
  void registerServiceWorker();
}

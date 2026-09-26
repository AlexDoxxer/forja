/// <reference lib="webworker" />
import { clientsClaim, type WorkboxPlugin } from "workbox-core";
import { CacheableResponsePlugin } from "workbox-cacheable-response";
import { ExpirationPlugin } from "workbox-expiration";
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { CacheFirst, StaleWhileRevalidate } from "workbox-strategies";

import {
  CACHE_EXERCISES,
  CACHE_GIFS,
  CACHE_THUMBS,
  DEFAULT_GIF_LIMIT_MB,
  isExercisesApi,
  isGif,
  isThumb,
  precacheMedia,
  THUMB_MAX_ENTRIES,
  trimCacheToBytes,
} from "./cachePolicy";
import type { PrecacheMessage } from "./library";

/** Los plugins de Workbox declaran opcionales sin `undefined`; con `exactOptionalPropertyTypes` hace falta este ajuste de tipo. */
const asPlugin = (plugin: unknown): WorkboxPlugin => plugin as WorkboxPlugin;

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: (string | { url: string; revision: string | null })[];
};

/** Límite de la caché de GIFs configurable en compilación (`VITE_GIF_CACHE_MB`, por defecto 300). */
const gifLimitMb = Number(import.meta.env["VITE_GIF_CACHE_MB"] ?? DEFAULT_GIF_LIMIT_MB);
const GIF_LIMIT_BYTES = (Number.isFinite(gifLimitMb) ? gifLimitMb : DEFAULT_GIF_LIMIT_MB) * 1024 * 1024;

clientsClaim();
void self.skipWaiting();

// App shell precacheado; la navegación cae a index.html salvo API y medios.
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();
registerRoute(
  new NavigationRoute(createHandlerBoundToURL("/index.html"), {
    denylist: [/^\/api\//, /^\/media\//],
  }),
);

// Catálogo: stale-while-revalidate. El resto de /api/v1 (datos personales) no se cachea (ADR 0006).
registerRoute(
  ({ url, request }) => isExercisesApi(url, request.method),
  new StaleWhileRevalidate({
    cacheName: CACHE_EXERCISES,
    plugins: [asPlugin(new CacheableResponsePlugin({ statuses: [200] }))],
  }),
);

registerRoute(
  ({ url }) => isThumb(url),
  new CacheFirst({
    cacheName: CACHE_THUMBS,
    plugins: [
      asPlugin(new CacheableResponsePlugin({ statuses: [200] })),
      asPlugin(new ExpirationPlugin({ maxEntries: THUMB_MAX_ENTRIES })),
    ],
  }),
);

registerRoute(
  ({ url }) => isGif(url),
  new CacheFirst({
    cacheName: CACHE_GIFS,
    plugins: [
      asPlugin(new CacheableResponsePlugin({ statuses: [200] })),
      {
        cacheDidUpdate: async () => {
          await trimCacheToBytes(await caches.open(CACHE_GIFS), GIF_LIMIT_BYTES);
        },
      },
    ],
  }),
);

// «Descargar biblioteca»: la página pide precachear los medios del programa activo.
self.addEventListener("message", (event) => {
  const data = event.data as Partial<PrecacheMessage> | null;
  const port = event.ports[0];
  if (data?.type !== "PRECACHE_MEDIA" || !Array.isArray(data.urls) || port === undefined) return;
  event.waitUntil(
    precacheMedia(
      data.urls,
      (name) => caches.open(name),
      (url) => fetch(url, { credentials: "same-origin" }),
      self.location.origin,
    ).then(
      (cached) => {
        port.postMessage({ ok: true, cached });
      },
      () => {
        port.postMessage({ ok: false, cached: 0 });
      },
    ),
  );
});

// Background Sync (Chromium): la página tiene la cookie CSRF, así que le pedimos que vacíe la cola.
self.addEventListener("sync", (event) => {
  const syncEvent = event as Event & { tag: string; waitUntil: (p: Promise<unknown>) => void };
  if (syncEvent.tag !== "forja-sync") return;
  syncEvent.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      for (const client of clients) client.postMessage({ type: "FLUSH_QUEUE" });
    }),
  );
});

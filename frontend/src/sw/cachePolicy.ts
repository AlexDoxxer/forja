/** Lógica pura de las políticas de caché del service worker (MASTER_PROMPT §10.3, ADR 0006). */

export const CACHE_EXERCISES = "forja-exercises-v1";
export const CACHE_THUMBS = "forja-thumbs-v1";
export const CACHE_GIFS = "forja-gifs-v1";

export const THUMB_MAX_ENTRIES = 1400;
export const DEFAULT_GIF_LIMIT_MB = 300;

export function isExercisesApi(url: URL, method: string): boolean {
  return method === "GET" && url.pathname.startsWith("/api/v1/exercises");
}

export function isThumb(url: URL): boolean {
  return url.pathname.startsWith("/media/thumbs/");
}

export function isGif(url: URL): boolean {
  return url.pathname.startsWith("/media/gifs/");
}

/** Los medios se guardan tal cual llegan (byte a byte, §2.1); aquí solo se decide dónde. */
export function cacheNameForMedia(url: URL): string | null {
  if (isThumb(url)) return CACHE_THUMBS;
  if (isGif(url)) return CACHE_GIFS;
  return null;
}

interface CacheLike {
  keys: () => Promise<readonly Request[]>;
  match: (request: Request) => Promise<Response | undefined>;
  delete: (request: Request) => Promise<boolean>;
  put: (request: Request | string, response: Response) => Promise<void>;
}

/** Elimina las entradas más antiguas hasta que el total quepa en `maxBytes`. */
export async function trimCacheToBytes(cache: CacheLike, maxBytes: number): Promise<number> {
  const requests = await cache.keys();
  const sized: { request: Request; size: number }[] = [];
  let total = 0;
  for (const request of requests) {
    const response = await cache.match(request);
    const size = response === undefined ? 0 : (await response.clone().arrayBuffer()).byteLength;
    sized.push({ request, size });
    total += size;
  }
  let removed = 0;
  // `keys()` devuelve en orden de inserción: las primeras son las más antiguas.
  for (const entry of sized) {
    if (total <= maxBytes) break;
    await cache.delete(entry.request);
    total -= entry.size;
    removed += 1;
  }
  return removed;
}

/** Guarda las URLs de medios en su caché; devuelve cuántas quedaron guardadas. */
export async function precacheMedia(
  urls: string[],
  open: (name: string) => Promise<CacheLike>,
  fetcher: (url: string) => Promise<Response>,
  origin: string,
): Promise<number> {
  let cached = 0;
  for (const raw of urls) {
    const url = new URL(raw, origin);
    const name = cacheNameForMedia(url);
    if (name === null || url.origin !== origin) continue;
    const response = await fetcher(url.href);
    if (!response.ok) continue;
    await (await open(name)).put(url.href, response);
    cached += 1;
  }
  return cached;
}

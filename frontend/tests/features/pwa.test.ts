import { describe, expect, it, vi } from "vitest";

import { i18next } from "../../src/i18n";
import "../../src/features/admin/strings";
import "../../src/features/nutrition/strings";
import "../../src/features/profile/strings";
import "../../src/features/progress/strings";
import "../../src/features/session/strings";
import {
  cacheNameForMedia,
  CACHE_GIFS,
  CACHE_THUMBS,
  isExercisesApi,
  precacheMedia,
  trimCacheToBytes,
} from "../../src/sw/cachePolicy";
import { collectActiveProgramMedia, offlineSupported, requestPrecache } from "../../src/sw/library";
import { registerServiceWorker } from "../../src/sw/register";
import { server } from "../../src/mocks/server";
import { http, HttpResponse } from "msw";

function fakeCache(entries: Record<string, number>): {
  keys: () => Promise<Request[]>;
  match: (r: Request) => Promise<Response | undefined>;
  delete: (r: Request) => Promise<boolean>;
  put: (r: Request | string, res: Response) => Promise<void>;
  store: Map<string, Response>;
} {
  const store = new Map<string, Response>(
    Object.entries(entries).map(([url, size]) => [url, new Response(new Uint8Array(size))]),
  );
  return {
    store,
    keys: () => Promise.resolve([...store.keys()].map((u) => new Request(u))),
    match: (r) => Promise.resolve(store.get(r.url)),
    delete: (r) => Promise.resolve(store.delete(r.url)),
    put: (r, res) => {
      store.set(typeof r === "string" ? r : r.url, res);
      return Promise.resolve();
    },
  };
}

describe("políticas de caché del service worker", () => {
  it("clasifica rutas de API y medios", () => {
    expect(isExercisesApi(new URL("https://x/api/v1/exercises?q=a"), "GET")).toBe(true);
    expect(isExercisesApi(new URL("https://x/api/v1/exercises"), "POST")).toBe(false);
    expect(isExercisesApi(new URL("https://x/api/v1/sessions"), "GET")).toBe(false);
    expect(cacheNameForMedia(new URL("https://x/media/thumbs/1.jpg"))).toBe(CACHE_THUMBS);
    expect(cacheNameForMedia(new URL("https://x/media/gifs/1.gif"))).toBe(CACHE_GIFS);
    expect(cacheNameForMedia(new URL("https://x/other"))).toBeNull();
  });

  it("recorta la caché por tamaño eliminando lo más antiguo", async () => {
    const cache = fakeCache({ "https://x/a": 100, "https://x/b": 100, "https://x/c": 100 });
    expect(await trimCacheToBytes(cache, 150)).toBe(2);
    expect([...cache.store.keys()]).toEqual(["https://x/c"]);
    expect(await trimCacheToBytes(cache, 1000)).toBe(0);
  });

  it("precachea solo medios del mismo origen y salta respuestas fallidas", async () => {
    const stores = new Map<string, ReturnType<typeof fakeCache>>();
    const open = (name: string): Promise<ReturnType<typeof fakeCache>> => {
      if (!stores.has(name)) stores.set(name, fakeCache({}));
      return Promise.resolve(stores.get(name) ?? fakeCache({}));
    };
    const fetcher = vi.fn((url: string) =>
      Promise.resolve(url.includes("bad") ? new Response(null, { status: 404 }) : new Response("ok")),
    );
    const n = await precacheMedia(
      ["/media/thumbs/1.jpg", "/media/gifs/1.gif", "/media/gifs/bad.gif", "https://evil.example/media/gifs/2.gif", "/x"],
      open,
      fetcher,
      "https://x",
    );
    expect(n).toBe(2);
    expect(stores.get(CACHE_THUMBS)?.store.size).toBe(1);
    expect(stores.get(CACHE_GIFS)?.store.size).toBe(1);
  });
});

describe("biblioteca offline y registro", () => {
  it("reúne miniaturas y GIFs del programa activo sin duplicados", async () => {
    const ex = (id: string): object => ({
      id,
      media: { thumb_url: `/media/thumbs/${id}.jpg`, gif_url: `/media/gifs/${id}.gif` },
    });
    server.use(
      http.get("/api/v1/programs", () =>
        HttpResponse.json({ items: [{ id: "p1", is_active: false }, { id: "p2", is_active: true }], next_cursor: null }),
      ),
      http.get("/api/v1/programs/p2", () => HttpResponse.json({ exercises: [ex("1"), ex("1"), ex("2")] })),
    );
    expect(await collectActiveProgramMedia()).toEqual([
      "/media/thumbs/1.jpg",
      "/media/gifs/1.gif",
      "/media/thumbs/2.jpg",
      "/media/gifs/2.gif",
    ]);
    server.use(http.get("/api/v1/programs", () => HttpResponse.json({ items: [], next_cursor: null })));
    expect(await collectActiveProgramMedia()).toEqual([]);
  });

  it("requestPrecache habla con el service worker por MessageChannel", async () => {
    const postMessage = vi.fn((_msg: unknown, ports: MessagePort[]) => {
      ports[0]?.postMessage({ ok: true, cached: 3 });
    });
    Object.defineProperty(navigator, "serviceWorker", {
      value: { ready: Promise.resolve({ active: { postMessage } }) },
      configurable: true,
    });
    Object.defineProperty(globalThis, "caches", { value: {}, configurable: true });
    expect(offlineSupported()).toBe(true);
    expect(await requestPrecache(["/media/thumbs/1.jpg"])).toBe(3);
    Object.defineProperty(navigator, "serviceWorker", {
      value: { ready: Promise.resolve({ active: null }) },
      configurable: true,
    });
    await expect(requestPrecache([])).rejects.toThrow();
    Reflect.deleteProperty(navigator, "serviceWorker");
    Reflect.deleteProperty(globalThis, "caches");
  });

  it("no registra el service worker fuera de producción", async () => {
    expect(await registerServiceWorker()).toBeNull();
  });
});

describe("i18n de la parte B", () => {
  it("es y en tienen las mismas claves", () => {
    const flat = (node: unknown, prefix = ""): string[] =>
      typeof node === "object" && node !== null
        ? Object.entries(node).flatMap(([k, v]) => flat(v, prefix === "" ? k : `${prefix}.${k}`))
        : [prefix];
    const bundle = (lng: string): Record<string, unknown> =>
      i18next.getResourceBundle(lng, "translation") as Record<string, unknown>;
    for (const ns of ["session", "todayB", "progressB", "nutrition", "profileB", "admin"]) {
      const es = flat(bundle("es")[ns]).sort();
      const en = flat(bundle("en")[ns]).sort();
      expect(es.length).toBeGreaterThan(5);
      expect(en).toEqual(es);
    }
  });
});

import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** Métodos que ADR 0003 exime de cabecera CSRF (no mutan estado). */
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

const CSRF_COOKIE_NAME = "__Host-forja_csrf";
const CSRF_HEADER_NAME = "X-CSRF-Token";

/** Lee una cookie por nombre desde `document.cookie` (entorno de navegador o jsdom). */
export function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const entry = part.trim();
    if (entry.startsWith(prefix)) {
      return decodeURIComponent(entry.slice(prefix.length));
    }
  }
  return null;
}

/**
 * La API vive en el mismo origen que la SPA detrás de nginx (MASTER_PROMPT §4.3). Se resuelve
 * a una URL absoluta a partir de `window.location.origin` porque el `Request` del Fetch API
 * solo resuelve rutas relativas frente al documento en un navegador real; en Node (tests) no
 * hay documento y una base relativa lanzaría "Invalid URL".
 */
function resolveApiBaseUrl(): string {
  return typeof window === "undefined" ? "/api/v1" : `${window.location.origin}/api/v1`;
}

/**
 * Cliente API tipado generado desde `contracts/openapi.yaml` (`openapi-typescript` +
 * `openapi-fetch`, MASTER_PROMPT §4.1). Nunca se escriben tipos de la API a mano.
 */
export const api = createClient<paths>({
  baseUrl: resolveApiBaseUrl(),
  credentials: "include",
  // `openapi-fetch` resuelve `globalThis.fetch` una sola vez, al crear el cliente. Herramientas
  // que parchean el `fetch` global después de esa creación (p. ej. MSW en los tests, o
  // cualquier interceptor en producción) no tendrían efecto. Se envuelve para leer
  // `globalThis.fetch` en cada petición.
  fetch: (request) => globalThis.fetch(request),
});

api.use({
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method)) {
      const token = readCookie(CSRF_COOKIE_NAME);
      if (token !== null) {
        request.headers.set(CSRF_HEADER_NAME, token);
      }
    }
    return request;
  },
});

function extractTitle(problem: unknown): string | null {
  if (typeof problem !== "object" || problem === null || !("title" in problem)) {
    return null;
  }
  const { title } = problem;
  return typeof title === "string" ? title : null;
}

/** Error de API con el cuerpo `Problem` (RFC 9457, MASTER_PROMPT §9) sin tipar a mano. */
export class ApiError extends Error {
  readonly problem: unknown;

  constructor(problem: unknown) {
    super(extractTitle(problem) ?? "Error de la API");
    this.problem = problem;
  }
}

/**
 * Extrae `data` de una respuesta de `openapi-fetch` o lanza un `ApiError`/`Error` tipado.
 * Evita repetir la comprobación de `{ data, error }` en cada hook de datos.
 */
export function unwrapApi<TData>(result: { data?: TData; error?: unknown }): TData {
  if (result.error !== undefined) {
    throw new ApiError(result.error);
  }
  if (result.data === undefined) {
    throw new Error("Respuesta vacía inesperada del servidor.");
  }
  return result.data;
}

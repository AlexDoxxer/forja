import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { ApiError, api, readCookie, unwrapApi } from "../../src/lib/api/client";
import { server } from "../../src/mocks/server";

/**
 * `__Host-` exige `Secure` + `Path=/` (y, para jsdom, un origen https — ver
 * `test.environmentOptions.jsdom.url` en `vite.config.ts`).
 */
const CSRF_COOKIE = "__Host-forja_csrf";
function setCsrfCookie(value: string): void {
  document.cookie = `${CSRF_COOKIE}=${value}; Path=/; Secure`;
}

afterEach(() => {
  document.cookie = `${CSRF_COOKIE}=; Path=/; Secure; max-age=0`;
  document.cookie = "otra=; max-age=0";
});

describe("readCookie", () => {
  it("lee el valor de una cookie por nombre", () => {
    document.cookie = "otra=valor-a";
    setCsrfCookie("token-de-prueba");
    expect(readCookie(CSRF_COOKIE)).toBe("token-de-prueba");
  });

  it("devuelve null si la cookie no existe", () => {
    expect(readCookie("no-existe")).toBeNull();
  });
});

describe("cliente API — middleware CSRF (ADR 0003)", () => {
  it("añade X-CSRF-Token en peticiones de escritura cuando hay cookie", async () => {
    setCsrfCookie("token-de-prueba");
    let capturedHeader: string | null = null;
    server.use(
      http.post("/api/v1/auth/logout", ({ request }) => {
        capturedHeader = request.headers.get("x-csrf-token");
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await api.POST("/auth/logout");

    expect(capturedHeader).toBe("token-de-prueba");
  });

  it("no añade la cabecera en peticiones de solo lectura (GET)", async () => {
    setCsrfCookie("token-de-prueba");
    let capturedHeader: string | null = "sin-tocar";
    server.use(
      http.get("/api/v1/auth/me", ({ request }) => {
        capturedHeader = request.headers.get("x-csrf-token");
        return HttpResponse.json(
          {
            id: "0192f08a-3b4c-7d5e-8f60-112233445566",
            email: "lucia@example.org",
            display_name: "Lucía",
            role: "user",
            locale: "es",
            units: "metric",
            created_at: "2026-09-01T09:12:00Z",
            last_login_at: null,
            onboarding_completed: true,
            diet_available: false,
          },
          { status: 200 },
        );
      }),
    );

    await api.GET("/auth/me");

    expect(capturedHeader).toBeNull();
  });

  it("no añade la cabecera en escrituras si no hay cookie CSRF", async () => {
    let capturedHeader: string | null = "sin-tocar";
    server.use(
      http.post("/api/v1/auth/logout", ({ request }) => {
        capturedHeader = request.headers.get("x-csrf-token");
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await api.POST("/auth/logout");

    expect(capturedHeader).toBeNull();
  });
});

describe("unwrapApi / ApiError", () => {
  it("devuelve data cuando la respuesta no tiene error", () => {
    expect(unwrapApi({ data: { ok: true } })).toEqual({ ok: true });
  });

  it("lanza ApiError con el título del problema cuando hay error", () => {
    expect(() => unwrapApi({ error: { title: "No autorizado" } })).toThrow(ApiError);
    try {
      unwrapApi({ error: { title: "No autorizado" } });
    } catch (thrown) {
      expect(thrown).toBeInstanceOf(ApiError);
      expect((thrown as ApiError).message).toBe("No autorizado");
      expect((thrown as ApiError).problem).toEqual({ title: "No autorizado" });
    }
  });

  it("usa un mensaje por defecto si el problema no trae título", () => {
    expect(() => unwrapApi({ error: { code: "conflict" } })).toThrow("Error de la API");
    expect(() => unwrapApi({ error: "texto plano" })).toThrow("Error de la API");
    expect(() => unwrapApi({ error: null })).toThrow("Error de la API");
  });

  it("lanza un error si no hay ni data ni error (respuesta vacía inesperada)", () => {
    expect(() => unwrapApi({})).toThrow("Respuesta vacía inesperada del servidor.");
  });
});

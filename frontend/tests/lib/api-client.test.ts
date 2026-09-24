import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { api, readCookie } from "../../src/lib/api/client";
import { server } from "../../src/mocks/server";

afterEach(() => {
  document.cookie = "__Host-forja_csrf=; max-age=0";
  document.cookie = "otra=; max-age=0";
});

describe("readCookie", () => {
  it("lee el valor de una cookie por nombre", () => {
    document.cookie = "otra=valor-a";
    document.cookie = "__Host-forja_csrf=token-de-prueba";
    expect(readCookie("__Host-forja_csrf")).toBe("token-de-prueba");
  });

  it("devuelve null si la cookie no existe", () => {
    expect(readCookie("no-existe")).toBeNull();
  });
});

describe("cliente API — middleware CSRF (ADR 0003)", () => {
  it("añade X-CSRF-Token en peticiones de escritura cuando hay cookie", async () => {
    document.cookie = "__Host-forja_csrf=token-de-prueba";
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
    document.cookie = "__Host-forja_csrf=token-de-prueba";
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

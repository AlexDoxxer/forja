import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  beep,
  ensureNotificationPermission,
  notifyRestOver,
  requestWakeLock,
  restFinished,
  vibrate,
} from "../../src/features/session/feedback";
import { resolveTheme } from "../../src/features/profile/theme";
import { attachSyncTriggers, requestBackgroundSync, scheduler } from "../../src/features/session/scheduler";
import { SessionRoute, SessionSummaryRoute } from "../../src/features/session/SessionRoute";
import { formatClock, parseDecimal } from "../../src/features/shared/format";
import { server } from "../../src/mocks/server";
import { bootPwa } from "../../src/sw/register";
import { renderRoute } from "./renderRoute";

afterEach(() => {
  vi.restoreAllMocks();
  Reflect.deleteProperty(navigator, "vibrate");
  Reflect.deleteProperty(globalThis, "Notification");
  Reflect.deleteProperty(globalThis, "AudioContext");
});

describe("feedback", () => {
  it("vibra solo si el navegador lo soporta", () => {
    expect(vibrate(100)).toBe(false);
    Object.defineProperty(navigator, "vibrate", { value: vi.fn().mockReturnValue(true), configurable: true });
    expect(vibrate([1, 2])).toBe(true);
  });

  it("Wake Lock: null si no existe o si lo rechaza", async () => {
    expect(await requestWakeLock()).toBeNull();
    Object.defineProperty(navigator, "wakeLock", {
      value: { request: vi.fn().mockRejectedValue(new Error("no")) },
      configurable: true,
    });
    expect(await requestWakeLock()).toBeNull();
    Reflect.deleteProperty(navigator, "wakeLock");
  });

  it("pitido con Web Audio y sin él", () => {
    expect(() => { beep(); }).not.toThrow();
    const osc = { frequency: { value: 0 }, connect: vi.fn().mockReturnThis(), start: vi.fn(), stop: vi.fn() };
    class Ctx {
      currentTime = 0;
      destination = {};
      createOscillator = (): typeof osc => osc;
      createGain = (): { gain: { value: number }; connect: () => { connect: () => void } } => ({
        gain: { value: 0 },
        connect: () => osc,
      });
      close = vi.fn().mockResolvedValue(undefined);
    }
    Object.defineProperty(globalThis, "AudioContext", { value: Ctx, configurable: true });
    beep(2);
    expect(osc.start).toHaveBeenCalledTimes(2);
  });

  it("notificaciones: permiso y solo en segundo plano", async () => {
    expect(await ensureNotificationPermission()).toBe("unsupported");
    expect(notifyRestOver("a", "b")).toBe(false);
    const ctor = vi.fn();
    Object.assign(ctor, { permission: "default", requestPermission: vi.fn().mockResolvedValue("granted") });
    Object.defineProperty(globalThis, "Notification", { value: ctor, configurable: true });
    expect(await ensureNotificationPermission()).toBe("granted");
    Object.assign(ctor, { permission: "granted" });
    expect(await ensureNotificationPermission()).toBe("granted");
    expect(notifyRestOver("a", "b")).toBe(false); // visible
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    expect(notifyRestOver("a", "b")).toBe(true);
    restFinished({ sounds: false, vibration: false }, "a", "b");
    expect(ctor).toHaveBeenCalled();
  });
});

describe("scheduler y utilidades", () => {
  it("engancha online y mensajes FLUSH_QUEUE del service worker; pide Background Sync", async () => {
    const trigger = vi.spyOn(scheduler, "trigger").mockResolvedValue({
      sent: 0, applied: 0, duplicate: 0, superseded: 0, rejected: 0, failed: false,
    });
    const register = vi.fn().mockResolvedValue(undefined);
    let onMessage: ((e: MessageEvent) => void) | undefined;
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        ready: Promise.resolve({ sync: { register } }),
        addEventListener: (_t: string, fn: (e: MessageEvent) => void) => { onMessage = fn; },
        removeEventListener: vi.fn(),
      },
      configurable: true,
    });
    const detach = attachSyncTriggers();
    expect(attachSyncTriggers()).toBeTypeOf("function"); // segunda llamada: no duplica
    trigger.mockClear();
    window.dispatchEvent(new Event("online"));
    onMessage?.(new MessageEvent("message", { data: { type: "FLUSH_QUEUE" } }));
    onMessage?.(new MessageEvent("message", { data: { type: "otra" } }));
    expect(trigger).toHaveBeenCalledTimes(2);
    await requestBackgroundSync();
    expect(register).toHaveBeenCalledWith("forja-sync");
    detach();
    Reflect.deleteProperty(navigator, "serviceWorker");
    await requestBackgroundSync();
    bootPwa();
    scheduler.stop();
  });

  it("tema y formatos", () => {
    expect(resolveTheme("dark")).toBe("dark");
    expect(resolveTheme("system")).toBe("dark");
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    expect(resolveTheme("system")).toBe("light");
    expect(formatClock(75)).toBe("1:15");
    expect(parseDecimal("7,5")).toBe(7.5);
    expect(parseDecimal("")).toBeNull();
    expect(parseDecimal("abc")).toBeNull();
  });
});

describe("rutas de sesión", () => {
  it("/sesion sin sesión activa vuelve a Hoy; el resumen sin datos también", async () => {
    server.use(http.get("/api/v1/profile", () => HttpResponse.json({ preferences: {} })));
    const first = renderRoute(<SessionRoute />, "/sesion");
    await userEvent.click(await screen.findByRole("button", { name: "Volver a Hoy" }));
    await waitFor(() => { expect(first.router.state.location.pathname).toBe("/"); });
    first.unmount();
    const second = renderRoute(<SessionSummaryRoute />, "/sesion/resumen/$uuid");
    await userEvent.click(await screen.findByRole("button", { name: "Volver a Hoy" }));
    await waitFor(() => { expect(second.router.state.location.pathname).toBe("/"); });
  });
});

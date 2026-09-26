import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useNow } from "../../src/features/session/useNow";
import { resolveTheme } from "../../src/features/profile/theme";
import { registerServiceWorker } from "../../src/sw/register";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  Reflect.deleteProperty(navigator, "serviceWorker");
});

describe("registro del service worker", () => {
  it("en producción registra /sw.js con alcance raíz y tolera fallos", async () => {
    vi.stubEnv("PROD", true);
    const register = vi.fn().mockResolvedValue({ scope: "/" });
    Object.defineProperty(navigator, "serviceWorker", { value: { register }, configurable: true });
    expect(await registerServiceWorker()).toEqual({ scope: "/" });
    expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" });

    register.mockRejectedValueOnce(new Error("boom"));
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(await registerServiceWorker()).toBeNull();
    expect(error).toHaveBeenCalled();
  });

  it("sin service worker en el navegador devuelve null", async () => {
    vi.stubEnv("PROD", true);
    expect(await registerServiceWorker()).toBeNull();
  });
});

describe("useNow y tema", () => {
  it("useNow se refresca por intervalo y al volver a primer plano; inactivo no corre", () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    const { result, rerender } = renderHook(({ active }) => useNow(active, 100), { initialProps: { active: true } });
    expect(result.current).toBe(1_000);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBe(1_300);
    act(() => {
      vi.setSystemTime(5_000);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(result.current).toBe(5_000);
    rerender({ active: false });
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(result.current).toBe(5_000);
    vi.useRealTimers();
  });

  it("resolveTheme sin matchMedia usa oscuro", () => {
    const original = window.matchMedia.bind(window);
    // @ts-expect-error simulamos un entorno sin matchMedia
    window.matchMedia = undefined;
    expect(resolveTheme("system")).toBe("dark");
    window.matchMedia = original;
  });
});

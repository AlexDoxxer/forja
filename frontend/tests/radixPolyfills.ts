import { vi } from "vitest";

/** jsdom no implementa las APIs de puntero ni ResizeObserver que usan Radix Select/Slider. */
export function installRadixPolyfills(): void {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => undefined;
  Element.prototype.releasePointerCapture = () => undefined;
  class ResizeObserverStub {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
}

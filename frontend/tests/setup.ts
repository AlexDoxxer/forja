import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";

import { server } from "../src/mocks/server";

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
  // jsdom no implementa el desplazamiento; TanStack Router lo llama al restaurar el scroll.
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  // jsdom no implementa matchMedia; valor por defecto "sin preferencia". Una función normal
  // (no `vi.fn()`) para que `restoreMocks` no la borre entre tests; los tests que necesitan
  // simular `prefers-reduced-motion` la sobrescriben en su propio `beforeEach` (p. ej.
  // ExerciseMedia.test.tsx), que se ejecuta después de este. Incluye los métodos heredados
  // `addListener`/`removeListener` (además de los estándar): Framer Motion los usa internamente
  // para su propio `prefers-reduced-motion` (`useReducedMotion` de la librería, distinto del
  // hook propio de `src/lib/useReducedMotion.ts`) y falla si faltan.
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

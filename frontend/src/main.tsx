import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { bootstrapTheme } from "./lib/theme";
import { bootPwa } from "./sw/register";
import "./styles/global.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("No se encontró el contenedor #root en index.html");
}

bootstrapTheme();
bootPwa();

/**
 * En desarrollo, mientras `backend-api` no está integrado (Fase 2, F2-FE-16), la app se sirve
 * contra los mocks de MSW generados desde `contracts/openapi.yaml`. Solo se activa en un
 * navegador real con soporte de Service Worker (nunca en Vitest/jsdom, que ya intercepta las
 * peticiones a nivel de red con `msw/node`, ver `tests/setup.ts`).
 */
async function enableMocking(): Promise<void> {
  if (!import.meta.env.DEV || typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
    return;
  }
  const { worker } = await import("./mocks/browser");
  await worker.start({ onUnhandledRequest: "bypass" });
}

enableMocking()
  .catch((error: unknown) => {
    console.error("No se pudieron activar los mocks de desarrollo (MSW):", error);
  })
  .finally(() => {
    createRoot(container).render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
  });

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
 * Por defecto la app habla con la API real (proxy de Vite). Los mocks de MSW generados desde
 * `contracts/openapi.yaml` solo se activan con `VITE_USE_MSW=1` en desarrollo y en un navegador
 * real con Service Worker (Vitest/jsdom usa `msw/node`, ver `tests/setup.ts`).
 */
async function enableMocking(): Promise<void> {
  if (import.meta.env["VITE_USE_MSW"] !== "1" || !import.meta.env.DEV || typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
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

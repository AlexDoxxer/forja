import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { bootstrapTheme } from "./lib/theme";
import "./styles/global.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("No se encontró el contenedor #root en index.html");
}

bootstrapTheme();

/**
 * En desarrollo, mientras `backend-api` no está integrado (Fase 2, F2-FE-16), la app se sirve
 * contra los mocks de MSW generados desde `contracts/openapi.yaml`.
 */
async function enableMocking(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const { worker } = await import("./mocks/browser");
  await worker.start({ onUnhandledRequest: "bypass" });
}

void enableMocking().then(() => {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});

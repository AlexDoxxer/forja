import { defineConfig, devices } from "@playwright/test";

// E2E (MASTER_PROMPT §13): Chromium de escritorio + WebKit móvil.
// Por defecto se prueba el build estático servido por `vite preview`; en Fase 3 `qa-tests`
// apunta E2E_BASE_URL al despliegue de docker compose.
const externalBaseUrl = process.env.E2E_BASE_URL;
const baseURL = externalBaseUrl ?? "http://localhost:4173";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: process.env.E2E_BASE_URL ? 60_000 : 30_000, // 60s for docker-compose, 30s for vite preview
  use: {
    baseURL,
    locale: "es-ES",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium-desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit-mobile", use: { ...devices["iPhone 13"] } },
  ],
  ...(externalBaseUrl === undefined
    ? {
        webServer: {
          command: "npm run build && npm run preview",
          url: baseURL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }
    : {}),
});

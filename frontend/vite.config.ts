import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Configuración de Vite y Vitest. Umbrales de cobertura: MASTER_PROMPT §2.2 (frontend >= 85 %).
export default defineConfig({
  plugins: [react()],
  build: {
    target: "es2022",
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    // Origen https: la cookie de sesión y la de CSRF (ADR 0003) usan el prefijo `__Host-`,
    // que exige el atributo `Secure` y, por tanto, un origen seguro.
    environmentOptions: {
      jsdom: { url: "https://localhost/" },
    },
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/setup.ts"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        // Datos de ejemplo generados desde contracts/openapi.yaml (`npm run gen:mocks`), no
        // lógica de aplicación; cada handler se cubre indirectamente en los tests que lo usan.
        "src/mocks/handlers.generated.ts",
        // Arranque de MSW en un navegador real (Service Worker); en jsdom nunca se ejecuta a
        // propósito (`main.tsx` lo evita fuera de un navegador real).
        "src/mocks/browser.ts",
      ],
      reporter: ["text", "json-summary", "lcov"],
      thresholds: {
        lines: 85,
        branches: 85,
        functions: 85,
        statements: 85,
      },
    },
  },
});

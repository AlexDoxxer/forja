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
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/setup.ts"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.d.ts"],
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

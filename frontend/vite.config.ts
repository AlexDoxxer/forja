import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";

import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const MEDIA_TYPES: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".gif": "image/gif",
  ".json": "application/json",
};

/**
 * Solo desarrollo: sirve `$MEDIA_ROOT` bajo `/media` (en producción lo hace nginx, ADR 0004).
 * Los ficheros se entregan byte a byte, sin transformar (© Gym visual, MASTER_PROMPT §2.1).
 */
function devMedia(root: string | undefined): Plugin {
  return {
    name: "forja-dev-media",
    apply: "serve",
    configureServer(server) {
      if (root === undefined || root === "") {
        return;
      }
      server.middlewares.use("/media", (req, res, next) => {
        const rel = normalize(decodeURIComponent((req.url ?? "/").split("?")[0] ?? "/"));
        const file = join(root, rel);
        if (rel.includes("..") || !file.startsWith(root) || !existsSync(file) || !statSync(file).isFile()) {
          next();
          return;
        }
        res.setHeader("Content-Type", MEDIA_TYPES[extname(file)] ?? "application/octet-stream");
        res.setHeader("Cache-Control", "public, max-age=3600");
        createReadStream(file).pipe(res);
      });
    },
  };
}

// Configuración de Vite y Vitest. Umbrales de cobertura: MASTER_PROMPT §2.2 (frontend >= 85 %).
export default defineConfig({
  plugins: [
    react(),
    devMedia(process.env.MEDIA_ROOT),
    // Service worker de Workbox (MASTER_PROMPT §10.3): `src/sw/sw.ts` con el shell precacheado.
    // El manifiesto es estático (`public/manifest.webmanifest`); el registro lo hace `src/sw/register.ts`.
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src/sw",
      filename: "sw.ts",
      manifest: false,
      injectRegister: false,
      injectManifest: { globPatterns: ["**/*.{js,css,html,svg,woff2,png,webmanifest}"] },
      devOptions: { enabled: false },
    }),
  ],
  build: {
    target: "es2022",
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // Desarrollo contra la API real (F2-FE-16). `/media` lo sirve `devMedia` desde $MEDIA_ROOT.
      "/api": process.env.VITE_API_TARGET ?? "http://localhost:8000",
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
        // Service worker: solo se ejecuta en un navegador real; su lógica está en cachePolicy.ts.
        "src/sw/sw.ts",
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

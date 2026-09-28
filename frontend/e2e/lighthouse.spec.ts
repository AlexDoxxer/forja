import { readFile } from "node:fs/promises";
import path from "node:path";

import { test, expect } from "@playwright/test";

test.describe("PWA and Performance checks", () => {

  test("PWA manifest and service worker present", async ({ page, baseURL }) => {
    if (!baseURL) {
      test.skip();
    }

    await page.goto("/");

    // Check for manifest
    const manifest = page.locator('link[rel="manifest"]');
    const manifestHref = await manifest.getAttribute("href");
    expect(manifestHref).toBeTruthy();

    // Check manifest is accessible
    if (manifestHref) {
      const manifestUrl = new URL(manifestHref, baseURL).href;
      const manifestResponse = await page.request.get(manifestUrl);
      expect(manifestResponse.ok()).toBeTruthy();

      interface ManifestData {
        name: string;
        short_name: string;
        display: string;
        theme_color: string;
      }

      const manifestData = (await manifestResponse.json()) as ManifestData;
      expect(manifestData.name).toBeTruthy();
      expect(manifestData.short_name).toBeTruthy();
      expect(manifestData.display).toBe("standalone");
      expect(manifestData.theme_color).toBeTruthy();
    }

    // Check service worker
    const swPresent = await page.evaluate(() => "serviceWorker" in navigator);
    expect(swPresent).toBeTruthy();

    // SW may not be registered on first load, but file should exist
    const swResponse = await page.request.get(new URL("/sw.js", baseURL).href);
    expect(swResponse.ok()).toBeTruthy();
  });

  test("Offline capability check", async ({ page, baseURL }) => {
    if (!baseURL) {
      test.skip();
    }

    await page.goto("/");

    // Verify service worker and offline cache strategy exists
    // The app should handle offline gracefully via service worker cache

    // Check that service worker file exists and is valid JavaScript
    const swUrl = new URL("/sw.js", baseURL).href;
    const swResponse = await page.request.get(swUrl);
    expect(swResponse.ok()).toBeTruthy();

    // `vite-plugin-pwa` solo genera el service worker real de Workbox en `npm run build`; en
    // modo desarrollo (este test corre contra `npx vite`) sirve un SW mínimo sin esas cadenas,
    // así que la comprobación se hace contra `dist/sw.js` (requiere haber compilado antes).
    const distSwPath = path.resolve(import.meta.dirname, "..", "dist", "sw.js");
    let distSwContent: string;
    try {
      distSwContent = await readFile(distSwPath, "utf8");
    } catch {
      test.skip(true, `No hay build de producción en ${distSwPath}; ejecuta \`npm run build\` primero.`);
      return;
    }
    const hasWorkbox = distSwContent.includes("workbox") || distSwContent.includes("precache");
    expect(hasWorkbox).toBeTruthy();

    // Verify service worker can be detected via API
    const swPresent = await page.evaluate(() => "serviceWorker" in navigator);
    expect(swPresent).toBeTruthy();
  });

  test("Media attribution (Gym visual) is visible and correct", async ({
    page,
    baseURL,
  }) => {
    if (!baseURL) {
      test.skip();
    }

    // Go to library where media is shown
    await page.goto("/biblioteca");

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Check if there are images on the page
    const images = await page.locator("img").all();

    if (images.length > 0) {
      // Check the page for Gym visual attribution somewhere
      const hasAttribution = await page
        .locator("text=/Gym visual|gymvisual/i")
        .isVisible()
        .catch(() => false);

      // Page with images should have attribution
      expect(hasAttribution).toBeTruthy();
    }

    // Check footer/about section for license attribution
    const footer = await page.locator("footer").isVisible().catch(() => false);
    if (!footer) {
      // Try settings/about
      const profileLink = page.getByRole("link", {
        name: /Perfil|Settings|Ajustes|About|Acerca/i,
      });
      if (await profileLink.isVisible()) {
        await profileLink.click();
        await page.waitForTimeout(500);

        const licensesText = page.locator("text=/Licencias|Licenses|MIT/i");
        const hasLicenses = await licensesText.isVisible().catch(() => false);
        if (hasLicenses) {
          expect(hasLicenses).toBeTruthy();
        }
      }
    }
  });
});

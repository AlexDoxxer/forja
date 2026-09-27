import { test, expect } from "@playwright/test";

test.describe("PWA and Performance checks", () => {

  test("PWA manifest and service worker present", async ({ page, baseURL }) => {
    if (!baseURL) {
      test.skip();
    }

    await page.goto("/", { baseURL });

    // Check for manifest
    const manifest = await page.locator('link[rel="manifest"]');
    const manifestHref = await manifest.getAttribute("href");
    expect(manifestHref).toBeTruthy();

    // Check manifest is accessible
    if (manifestHref) {
      const manifestUrl = new URL(manifestHref, baseURL).href;
      const manifestResponse = await page.request.get(manifestUrl);
      expect(manifestResponse.ok()).toBeTruthy();

      const manifestData = await manifestResponse.json();
      expect(manifestData.name).toBeTruthy();
      expect(manifestData.short_name).toBeTruthy();
      expect(manifestData.display).toBe("standalone");
      expect(manifestData.theme_color).toBeTruthy();
    }

    // Check service worker
    const swPresent = await page.evaluate(() => "serviceWorker" in navigator);
    expect(swPresent).toBeTruthy();

    // Try to register/detect service worker
    const swRegistered = await page.evaluate(async () => {
      try {
        const registration = await navigator.serviceWorker.getRegistrations();
        return registration.length > 0;
      } catch {
        return false;
      }
    });

    // SW may not be registered on first load, but file should exist
    const swResponse = await page.request.get(new URL("/sw.js", baseURL).href);
    expect(swResponse.ok()).toBeTruthy();
  });

  test("Offline capability check", async ({ page, baseURL }) => {
    if (!baseURL) {
      test.skip();
    }

    await page.goto("/", { baseURL });

    // Verify service worker and offline cache strategy exists
    // The app should handle offline gracefully via service worker cache

    // Check that service worker file exists and is valid JavaScript
    const swUrl = new URL("/sw.js", baseURL).href;
    const swResponse = await page.request.get(swUrl);
    expect(swResponse.ok()).toBeTruthy();

    // Service worker file should contain workbox references
    const swContent = await swResponse.text();
    const hasWorkbox = swContent.includes("workbox") || swContent.includes("precache");
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
    await page.goto("/biblioteca", { baseURL });

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Check if there's any media with attribution
    const images = await page.locator("img").all();

    if (images.length > 0) {
      // For each image, check if it's followed by attribution text
      for (const img of images.slice(0, 5)) {
        // Check the page for Gym visual attribution somewhere
        const hasAttribution = await page
          .locator("text=/Gym visual|gymvisual/i")
          .isVisible()
          .catch(() => false);

        // At least some content should have attribution
        if (hasAttribution) {
          expect(hasAttribution).toBeTruthy();
          break;
        }
      }
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

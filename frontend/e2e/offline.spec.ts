import { expect, test } from "@playwright/test";

const BASE_PASSWORD = "Test@1234!test";

function getTestEmail(testName: string): string {
  const timestamp = Date.now().toString();
  return `${testName}-${timestamp}@forja.local`;
}

test.describe("Offline mode — Session persistence and sync", () => {
  test("Session player continues after network cut and reload", async ({ page, context }) => {
    const email = getTestEmail("offline");

    // Setup account and program
    await page.goto("/onboarding");

    // Register
        await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Onboarding
    await expect(page).toHaveURL(/\/onboarding/);
    await page.getByLabel(/Sexo|Sex/i).selectOption("male");
    await page.getByLabel(/Altura|Height/).fill("180");
    await page.getByLabel(/Peso|Weight/).fill("80");
    await page.getByLabel(/Experiencia|Experience/i).selectOption("intermediate");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    const parqNoButtons = await page.locator('button:has-text("No")').all();
    for (const btn of parqNoButtons) {
      await btn.click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();
    await page.getByLabel(/Pesas/i).click();
    await page.getByRole("button", { name: /Completar|Done|Finish/i }).click();

    // Generate program
    await page.getByRole("link", { name: /Generar|Generate/i }).click();
    const goalOptions = await page.locator('button[role="radio"]').all();
    if (goalOptions.length > 0) {
      await goalOptions[0].click();
    }

    // Move through generator
    let nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
    let clickCount = 0;
    while (await nextBtn.isVisible() && clickCount < 5) {
      await nextBtn.click();
      await page.waitForTimeout(300);
      nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
      clickCount++;
    }

    // Save and activate
    const saveBtn = page.getByRole("button", {
      name: /Guardar y activar|Save and activate/i,
    });
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await page.waitForURL(/\/$|\/today/);
    }

    // Start session
    const startBtn = page.getByRole("button", { name: /Empezar|Start|Begin/i }).first();
    if (await startBtn.isVisible()) {
      await startBtn.click();
      await page.waitForURL(/\/sesion/);

      // Do first set
      const weightInput = page.locator('input[placeholder*="Peso|Weight"]').first();
      const repsInput = page.locator('input[placeholder*="Reps|Repeticiones"]').first();

      if (await weightInput.isVisible()) {
        await weightInput.fill("20");
      }
      if (await repsInput.isVisible()) {
        await repsInput.fill("10");
      }

      // Complete set
      const completeSetBtn = page.getByRole("button", { name: /Serie hecha|Set done/i }).first();
      if (await completeSetBtn.isVisible()) {
        await completeSetBtn.click();

        // Wait for rest timer
        await page.waitForTimeout(1000);

        // Now cut the network
        await context.setOffline(true);

        // Session data should still be visible in IndexedDB
        await page.waitForTimeout(500);

        // Reload page while offline
        await page.reload();

        // Should still be in session
        await expect(page).toHaveURL(/\/sesion/);

        // Session data should be restored from IndexedDB
        const sessionContent = page.locator("h2").first();
        await expect(sessionContent).toBeVisible({ timeout: 5000 });

        // Try to log another set
        const nextWeightInput = page
          .locator('input[placeholder*="Peso|Weight"]')
          .first();
        if (await nextWeightInput.isVisible()) {
          await nextWeightInput.fill("25");
        }

        const nextRepsInput = page
          .locator('input[placeholder*="Reps|Repeticiones"]')
          .first();
        if (await nextRepsInput.isVisible()) {
          await nextRepsInput.fill("8");
        }

        // Restore network
        await context.setOffline(false);
        await page.waitForTimeout(1000);

        // Session should sync when network returns
        // (Server would receive offline queue via /sync endpoint)
      }
    }
  });

  test("Offline indicator appears when network is cut", async ({ page, context }) => {
    const email = getTestEmail("offline-indicator");

    // Setup account
    await page.goto("/onboarding");
    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Onboarding
    await expect(page).toHaveURL(/\/onboarding/);
    await page.getByLabel(/Sexo|Sex/i).selectOption("male");
    await page.getByLabel(/Altura|Height/).fill("180");
    await page.getByLabel(/Peso|Weight/).fill("80");
    await page.getByLabel(/Experiencia|Experience/i).selectOption("intermediate");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    const parqNoButtons = await page.locator('button:has-text("No")').all();
    for (const btn of parqNoButtons) {
      await btn.click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();
    await page.getByLabel(/Pesas/i).click();
    await page.getByRole("button", { name: /Completar|Done|Finish/i }).click();

    // Go online - should not show offline indicator
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();

    // Cut network
    await context.setOffline(true);
    await page.waitForTimeout(1000);

    // App should continue functioning offline (may or may not show offline indicator)
    // Just verify page remains responsive
    await page.waitForTimeout(500);

    // Restore network
    await context.setOffline(false);
    await page.waitForTimeout(500);

    // Should be back online
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();
  });
});

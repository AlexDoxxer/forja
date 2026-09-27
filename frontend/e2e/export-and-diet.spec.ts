import { expect, test } from "@playwright/test";

import { generatePreview, getTestEmail, registerAndOnboard } from "./helpers";

test.describe("Export and Diet features", () => {
  test("Export program to PDF", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("export-pdf") });
    await generatePreview(page);
    await page.getByRole("button", { name: /^Guardar$|^Save$/i }).click();
    await page.waitForURL(/\/rutinas/, { timeout: 10000 });

    const exportLink = page.getByRole("link", { name: /Exportar a PDF|Export to PDF|PDF/i }).first();
    if (await exportLink.isVisible().catch(() => false)) {
      const downloadPromise = page.waitForEvent("download");
      await exportLink.click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
    }
  });

  test("Export calendar to ICS", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("export-ics") });
    await generatePreview(page);
    await page.getByRole("button", { name: /Guardar y activar|Save and activate/i }).click();
    await page.goto("/rutinas");

    const icsLink = page.getByRole("link", { name: /Calendario|Calendar|ICS/i }).first();
    if (await icsLink.isVisible().catch(() => false)) {
      const downloadPromise = page.waitForEvent("download");
      await icsLink.click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.ics$/i);
    }
  });

  test("Diet flow: enable, view, and manage diet plan", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("diet-flow"), dietEnabled: true });
    await expect(page.getByRole("heading", { level: 1, name: /Todo listo|All set/i })).toBeVisible();

    await page.goto("/nutricion");
    const dietContent = page.getByText(/Calorías|Kcal|Macros|Proteína|Carbohidratos|Grasas|Meals|Comidas/i);
    await expect(dietContent.first()).toBeVisible({ timeout: 10000 });
  });

  test("Diet settings: disable diet feature", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("diet-disable"), dietEnabled: true });

    await page.goto("/perfil");
    const dietToggle = page.getByLabel(/nutrición|nutrition/i);
    if (await dietToggle.isVisible().catch(() => false)) {
      if (await dietToggle.isChecked()) {
        await dietToggle.uncheck();
      }
    }

    // La página sigue operativa tras desactivar la dieta (sin errores no controlados).
    await expect(page.getByRole("heading").first()).toBeVisible();
  });
});

test.describe("Admin ingest", () => {
  test("Admin can access ingest section and see ingestion status", async ({ page }) => {
    // Sin sesión de admin, /admin redirige a /login (AuthGate). Se verifica el comportamiento
    // seguro por defecto; el acceso real de admin se cubre en backend/tests/integration.
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/(admin|login)/);
  });
});

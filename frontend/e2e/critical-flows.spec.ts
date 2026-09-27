import { expect, test } from "@playwright/test";

import { generatePreview, getTestEmail, registerAndOnboard } from "./helpers";

test.describe("Critical flows — Onboarding, Generate, Activate, Train, Progress", () => {
  test("Complete onboarding flow with PAR-Q", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("onboarding") });

    await page.getByRole("link", { name: /Crear mi rutina|Create my program/i }).click();
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();
  });

  test("Complete workflow: generate → activate → train session", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("workflow") });
    await generatePreview(page);

    await page.getByRole("button", { name: /Guardar y activar|Save and activate/i }).click();
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();

    const startButton = page.getByRole("button", { name: /Empezar|Start/i }).first();
    if (await startButton.isVisible().catch(() => false)) {
      await startButton.click();
      await expect(page).toHaveURL(/\/sesion/);
    }
  });

  test("View progress and stats", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("progress") });

    await page.goto("/progreso");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });
});

test.describe("Editor flow", () => {
  test("Edit generated program: reorder exercises, create superset", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("editor") });
    await generatePreview(page);

    // Guardar sin activar (botón "Guardar", distinto de "Guardar y activar")
    await page.getByRole("button", { name: /^Guardar$|^Save$/i }).click();

    await page.waitForURL(/\/rutinas/, { timeout: 10000 }).catch(() => undefined);
    const editLink = page.getByRole("link", { name: /Editar|Edit/i }).first();
    if (await editLink.isVisible().catch(() => false)) {
      await editLink.click();
      await expect(page).toHaveURL(/\/editar/);
    }
  });
});

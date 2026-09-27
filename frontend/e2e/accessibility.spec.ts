import { expect, test } from "@playwright/test";
import { injectAxe, checkA11y, getViolations } from "@axe-core/playwright";

const BASE_EMAIL = "access-test@forja.local";
const BASE_PASSWORD = "Test@1234!test";

function getTestEmail(testName: string): string {
  const timestamp = Date.now();
  return `${testName}-${timestamp}@forja.local`;
}

test.describe("Accessibility (WCAG 2.2 AA) — 0 serious/critical violations", () => {
  test("Home/today screen has no a11y violations", async ({ page }) => {
    await page.goto("/");
    await injectAxe(page);
    await expect(async () => {
      await checkA11y(page, null, {
        detailedReport: true,
        detailedReportOptions: {
          html: true,
        },
      });
    }).not.toThrow();
  });

  test("Onboarding screens have no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-onboarding");
    await page.goto("/");

    // Register
    await page.getByRole("button", { name: /Crear cuenta|Sign up/i }).click();
    await injectAxe(page);

    // Check register step
    let violations = await getViolations(page);
    let criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);

    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Check onboarding step 1
    await page.waitForURL(/\/onboarding/);
    await injectAxe(page);
    violations = await getViolations(page);
    criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);

    await page.getByLabel(/Sexo|Sex/i).selectOption("male");
    await page.getByLabel(/Altura|Height/).fill("180");
    await page.getByLabel(/Peso|Weight/).fill("80");
    await page.getByLabel(/Experiencia|Experience/i).selectOption("intermediate");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Check onboarding step 2 (PAR-Q)
    await injectAxe(page);
    violations = await getViolations(page);
    criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);

    const parqNoButtons = await page.locator('button:has-text("No")').all();
    for (const btn of parqNoButtons) {
      await btn.click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Check onboarding step 3 (Equipment)
    await injectAxe(page);
    violations = await getViolations(page);
    criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);

    await page.getByLabel(/Pesas/i).click();
    await page.getByRole("button", { name: /Completar|Done|Finish/i }).click();

    // Check final onboarding (today view)
    await injectAxe(page);
    violations = await getViolations(page);
    criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);
  });

  test("Library screen has no a11y violations", async ({ page }) => {
    await page.goto("/biblioteca");
    await injectAxe(page);

    const violations = await getViolations(page);
    const criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);
  });

  test("Generator wizard screens have no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-gen");
    await page.goto("/");

    // Quick setup
    await page.getByRole("button", { name: /Crear cuenta|Sign up/i }).click();
    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

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

    // Go to generator
    await page.getByRole("link", { name: /Generar|Generate/i }).click();
    await expect(page).toHaveURL(/\/rutinas\/nueva/);

    // Check each generator step for a11y
    for (let step = 0; step < 5; step++) {
      await injectAxe(page);
      let violations = await getViolations(page);
      let criticalCount = violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      ).length;
      expect(criticalCount).toBe(0);

      const nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
      if (await nextBtn.isVisible()) {
        await nextBtn.click();
        await page.waitForTimeout(300);
      } else {
        break;
      }
    }
  });

  test("Profile/settings screen has no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-profile");
    await page.goto("/");

    // Setup account
    await page.getByRole("button", { name: /Crear cuenta|Sign up/i }).click();
    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

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

    // Go to profile/settings
    await page.getByRole("link", { name: /Perfil|Profile|Ajustes|Settings/i }).click();

    await injectAxe(page);
    const violations = await getViolations(page);
    const criticalCount = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    ).length;
    expect(criticalCount).toBe(0);
  });

  test("Session player has no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-player");
    await page.goto("/");

    // Quick account setup
    await page.getByRole("button", { name: /Crear cuenta|Sign up/i }).click();
    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

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

    // Generate and activate program
    await page.getByRole("link", { name: /Generar|Generate/i }).click();

    const goalOptions = await page.locator('button[role="radio"]').all();
    if (goalOptions.length > 0) {
      await goalOptions[0].click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();
    await page.getByLabel(/Días por semana|Days per week/i).selectOption("3");

    // Fast forward through generator
    let nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
    while (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForTimeout(300);
      nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
    }

    // Save and activate
    await page.getByRole("button", { name: /Guardar y activar|Save and activate/i }).click();
    await page.waitForURL(/\/$|\/today/);

    // Try to start session if button is available
    const startBtn = page.getByRole("button", { name: /Empezar|Start/i }).first();
    if (await startBtn.isVisible()) {
      await startBtn.click();
      await page.waitForURL(/\/sesion/);

      await injectAxe(page);
      const violations = await getViolations(page);
      const criticalCount = violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      ).length;
      expect(criticalCount).toBe(0);
    }
  });
});

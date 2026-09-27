import { expect, test } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

const BASE_EMAIL = "access-test@forja.local";
const BASE_PASSWORD = "Test@1234!test";

function getTestEmail(testName: string): string {
  const timestamp = Date.now();
  return `${testName}-${timestamp}@forja.local`;
}

async function checkA11y(page: any, context: string | null = null) {
  const builder = new AxeBuilder({ page });
  if (context) {
    builder.include(context);
  }
  const results = await builder.analyze();

  const criticalViolations = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious"
  );

  expect(
    criticalViolations,
    `Found ${criticalViolations.length} critical/serious a11y violations: ${criticalViolations
      .map((v) => v.id)
      .join(", ")}`
  ).toHaveLength(0);
}

test.describe("Accessibility (WCAG 2.2 AA) — 0 serious/critical violations", () => {
  test("Home/today screen has no a11y violations", async ({ page }) => {
    await page.goto("/onboarding");
    await checkA11y(page);
  });

  test("Onboarding screens have no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-onboarding");
    await page.goto("/");

    // Register
        await checkA11y(page);

    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Check onboarding step 1
    await page.waitForURL(/\/onboarding/);
    await checkA11y(page);

    await page.getByLabel(/Sexo|Sex/i).selectOption("male");
    await page.getByLabel(/Altura|Height/).fill("180");
    await page.getByLabel(/Peso|Weight/).fill("80");
    await page.getByLabel(/Experiencia|Experience/i).selectOption("intermediate");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Check onboarding step 2 (PAR-Q)
    await checkA11y(page);

    const parqNoButtons = await page.locator('button:has-text("No")').all();
    for (const btn of parqNoButtons) {
      await btn.click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Check onboarding step 3 (Equipment)
    await checkA11y(page);

    await page.getByLabel(/Pesas/i).click();
    await page.getByRole("button", { name: /Completar|Done|Finish/i }).click();

    // Check final onboarding (today view)
    await checkA11y(page);
  });

  test("Library screen has no a11y violations", async ({ page }) => {
    await page.goto("/biblioteca");
    await checkA11y(page);
  });

  test("Profile/settings screen has no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-profile");
    await page.goto("/onboarding");

    // Setup account
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

    await checkA11y(page);
  });
});

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

import { getTestEmail, registerAndOnboard } from "./helpers";

async function checkA11y(page: Page, context: string | null = null): Promise<void> {
  const builder = new AxeBuilder({ page });
  if (context !== null) {
    builder.include(context);
  }
  const results = await builder.analyze();

  const criticalViolations = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious",
  );

  expect(
    criticalViolations,
    `Found ${criticalViolations.length.toString()} critical/serious a11y violations: ${criticalViolations
      .map((v) => v.id)
      .join(", ")}`,
  ).toHaveLength(0);
}

const PARQ_KEYS = [
  "heart_condition",
  "chest_pain_activity",
  "chest_pain_rest",
  "dizziness_or_fainting",
  "bone_or_joint_problem",
  "blood_pressure_or_heart_medication",
  "other_reason",
] as const;

test.describe("Accessibility (WCAG 2.2 AA) — 0 serious/critical violations", () => {
  test("Home/today screen has no a11y violations", async ({ page }) => {
    await page.goto("/onboarding");
    await checkA11y(page);
  });

  test("Onboarding screens have no a11y violations", async ({ page }) => {
    const email = getTestEmail("a11y-onboarding");
    await page.goto("/onboarding");
    await checkA11y(page); // Paso 1: cuenta

    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Nombre para mostrar|Display name/i).fill("Prueba E2E");
    await page.getByLabel(/Contraseña|Password/i).fill("ClaveSegura123");
    await page.getByRole("button", { name: /Continuar|Continue/i }).click();

    await checkA11y(page); // Paso 2: datos básicos
    await page.getByLabel(/Fecha de nacimiento|Date of birth/i).fill("1990-01-01");
    await page.getByLabel(/Altura|Height/i).fill("180");
    await page.getByRole("button", { name: /Continuar|Continue/i }).click();

    await checkA11y(page); // Paso 3: PAR-Q
    for (const key of PARQ_KEYS) {
      await page.locator(`input[name="${key}"]`).nth(1).check();
    }
    await page.getByRole("button", { name: /Continuar|Continue/i }).click();

    await checkA11y(page); // Paso 4: equipamiento
    await page.getByRole("button", { name: /Terminar|Finish/i }).click();

    await expect(page.getByRole("heading", { level: 1, name: /Todo listo|All set/i })).toBeVisible();
    await checkA11y(page); // Pantalla final «Todo listo»
  });

  test("Library screen has no a11y violations", async ({ page }) => {
    await page.goto("/biblioteca");
    await checkA11y(page);
  });

  test("Profile/settings screen has no a11y violations", async ({ page }) => {
    await registerAndOnboard(page, { email: getTestEmail("a11y-profile") });
    await page.goto("/perfil");
    await checkA11y(page);
  });
});

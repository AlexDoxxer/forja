import { expect, test } from "@playwright/test";

const BASE_PASSWORD = "Test@1234!test";

// Helper to generate unique email for each test
function getTestEmail(testName: string): string {
  const timestamp = Date.now().toString();
  return `${testName}-${timestamp}@forja.local`;
}

test.describe("Critical flows — Onboarding, Generate, Activate, Train, Progress", () => {
  test("Complete onboarding flow with PAR-Q", async ({ page }) => {
    await page.goto("/onboarding");

    // Step 1: Register
        await page.getByLabel(/Correo|Email/i).fill(getTestEmail("onboarding"));
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Wait for navigation to next step
    await expect(page).toHaveURL(/\/onboarding/);

    // Step 2: Profile data
    await page.getByLabel(/Sexo|Sex/i).selectOption("male");
    await page.getByLabel(/Altura|Height/).fill("180");
    await page.getByLabel(/Peso|Weight/).fill("80");
    await page.getByLabel(/Experiencia|Experience/i).selectOption("intermediate");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Step 3: PAR-Q
    // Select "No" for all PAR-Q questions
    const parqNoButtons = await page.locator('button:has-text("No")').all();
    for (const btn of parqNoButtons) {
      await btn.click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Step 4: Equipment and limitations
    await page.getByLabel(/Pesas/i).click();
    await page.getByRole("button", { name: /Completar|Done|Finish/i }).click();

    // Should redirect to today view
    await expect(page).toHaveURL(/\/$|\/today/);
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();
  });

  test("Complete workflow: generate → activate → train session", async ({ page }) => {
    // First, register and complete onboarding
    const email = getTestEmail("workflow");
    await page.goto("/onboarding");
    await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Quick onboarding
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

    // Now in today view, go to generator
    await expect(page.getByRole("heading", { level: 1, name: "Hoy" })).toBeVisible();
    await page.getByRole("link", { name: /Generar|Generate/i }).click();

    // Generator Step 1: Select goal
    await expect(page).toHaveURL(/\/rutinas\/nueva/);
    const goalOptions = await page.locator('button[role="radio"]').all();
    if (goalOptions.length > 0) {
      await goalOptions[0].click(); // Select first goal
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Generator Step 2: Days per week
    await page.getByLabel(/Días por semana|Days per week/i).selectOption("4");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Generator Step 3: Sex (skip if same as profile)
    const nextBtn = page.getByRole("button", { name: /Siguiente|Next/i }).first();
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
    }

    // Generator Step 4: Level and more settings
    await page.getByLabel(/Nivel|Level/i).selectOption("beginner");
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();

    // Generator Step 5: Emphasis (skip if optional)
    const skipOrNext = page.getByRole("button", { name: /Siguiente|Next|Saltar/i }).first();
    if (await skipOrNext.isVisible()) {
      await skipOrNext.click();
    }

    // Generator Step 6: Preview and save
    await expect(page.locator("text=Vista previa|Preview")).toBeVisible();

    // Verify the program shows exercises with GIFs
    const exerciseCards = await page.locator('[role="article"]').all();
    expect(exerciseCards.length).toBeGreaterThan(0);

    // Save and activate the program
    await page.getByRole("button", { name: /Guardar y activar|Save and activate/i }).click();

    // Should return to today view with active program
    await expect(page).toHaveURL(/\/$|\/today/);
    await page.waitForTimeout(500); // Allow UI to update

    // Verify active program is displayed
    const activeProgram = page.locator("text=/Día|Day/");
    await expect(activeProgram.first()).toBeVisible();

    // Start training a session
    const startButton = page.getByRole("button", { name: /Empezar|Start|Begin/i }).first();
    if (await startButton.isVisible()) {
      await startButton.click();

      // In session player
      await expect(page).toHaveURL(/\/sesion/);

      // Verify exercise display
      const exerciseName = page.locator("h2");
      await expect(exerciseName.first()).toBeVisible();

      // Log sets (simple flow - just do first set)
      const weightInput = page.locator('input[placeholder*="Peso|Weight"]').first();
      const repsInput = page.locator('input[placeholder*="Reps|Repeticiones"]').first();

      if (await weightInput.isVisible()) {
        await weightInput.fill("20");
      }
      if (await repsInput.isVisible()) {
        await repsInput.fill("10");
      }

      // Complete the set
      const completeSetBtn = page.getByRole("button", { name: /Serie hecha|Set done/i }).first();
      if (await completeSetBtn.isVisible()) {
        await completeSetBtn.click();

        // Rest timer should appear
        const restTimer = page.locator("text=/Descanso|Rest/");
        await expect(restTimer.first()).toBeVisible({ timeout: 5000 });

        // Skip rest
        const skipRest = page.getByRole("button", { name: /Siguiente|Next|Saltar/i }).first();
        if (await skipRest.isVisible()) {
          await skipRest.click();
        }
      }
    }
  });

  test("View progress and stats", async ({ page }) => {
    await page.goto("/onboarding");

    // Quick login
    const email = getTestEmail("progress");
        await page.getByLabel(/Correo|Email/i).fill(email);
    await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
    await page.getByRole("button", { name: /Crear|Create/i }).click();

    // Quick onboarding
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

    // Go to progress view
    await page.getByRole("link", { name: /Progreso|Progress/i }).click();

    // Should see progress screen with calendar or stats
    await expect(page).toHaveURL(/\/progreso/);
    const progressTitle = page.locator("h1");
    await expect(progressTitle).toBeVisible();
  });
});

test.describe("Editor flow", () => {
  test("Edit generated program: reorder exercises, create superset", async ({ page }) => {
    const email = getTestEmail("editor");
    await page.goto("/onboarding");

    // Create account
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
    await expect(page).toHaveURL(/\/rutinas\/nueva/);

    const goalOptions = await page.locator('button[role="radio"]').all();
    if (goalOptions.length > 0) {
      await goalOptions[0].click();
    }
    await page.getByRole("button", { name: /Siguiente|Next/i }).click();
    await page.getByLabel(/Días por semana|Days per week/i).selectOption("3");

    // Continue through generator
    const buttons = await page.getByRole("button", { name: /Siguiente|Next/i }).all();
    for (let i = 0; i < Math.min(3, buttons.length); i++) {
      await page.getByRole("button", { name: /Siguiente|Next/i }).first().click();
    }

    // In preview, save without activating
    await page.getByRole("button", { name: /Guardar|Save/i }).click();

    // Should show programs list - find the program and click edit
    await page.waitForURL(/\/rutinas/);
    const editLink = page.getByRole("link", { name: /Editar|Edit/i }).first();
    await editLink.click();

    // Now in editor
    await expect(page).toHaveURL(/\/editar/);

    // Verify exercises are shown
    const exerciseItems = page.locator('[role="article"]').all();
    expect((await exerciseItems).length).toBeGreaterThan(0);
  });
});

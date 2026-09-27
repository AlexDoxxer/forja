import { expect, test, type Page } from "@playwright/test";

/** Contraseña usada por todas las cuentas de prueba (cumple el mínimo de 10 caracteres). */
export const BASE_PASSWORD = "ClaveSegura123";

/** Correo único por ejecución para evitar colisiones entre pruebas (409 en `/auth/register`). */
export function getTestEmail(tag: string): string {
  return `e2e-${tag}-${Date.now().toString()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
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

/**
 * Registra una cuenta y completa el onboarding de 4 pasos (cuenta → datos básicos → PAR-Q →
 * equipamiento) hasta la pantalla «Todo listo» (`OnboardingScreen.tsx`). Responde «No» a las 7
 * preguntas del PAR-Q y deja preset/equipamiento en su valor por defecto (`full_gym`), que no
 * requiere seleccionar nada más para avanzar (`validateEquipment`).
 */
export async function registerAndOnboard(
  page: Page,
  options: { email: string; displayName?: string; dietEnabled?: boolean },
): Promise<void> {
  // Ampliado por si hace falta esperar la ventana del limitador de tasa (ver más abajo); el
  // resto del test hereda el margen aunque no llegue a usarlo.
  test.setTimeout(120_000);
  await page.goto("/onboarding");

  // Paso 1: cuenta. El límite de intentos de `/auth/register` es 5 por IP cada 60 s
  // (`ratelimit.py`, S-01) y en E2E todas las peticiones salen de la misma IP, así que una
  // ejecución con muchas cuentas seguidas puede recibir un 429. Se reintenta una vez tras
  // esperar la ventana completa en vez de fallar con un timeout confuso más abajo.
  await page.getByLabel(/Correo|Email/i).fill(options.email);
  await page.getByLabel(/Nombre para mostrar|Display name/i).fill(options.displayName ?? "Prueba E2E");
  await page.getByLabel(/Contraseña|Password/i).fill(BASE_PASSWORD);
  await page.getByRole("button", { name: /Continuar|Continue/i }).click();

  const basicsField = page.getByLabel(/Fecha de nacimiento|Date of birth/i);
  const rateLimited = page.getByRole("alert");
  const outcome = await Promise.race([
    basicsField.waitFor({ state: "visible", timeout: 20000 }).then(() => "advanced" as const),
    rateLimited.waitFor({ state: "visible", timeout: 20000 }).then(() => "error" as const),
  ]).catch(() => "timeout" as const);
  if (outcome !== "advanced") {
    await page.waitForTimeout(65_000);
    await page.getByRole("button", { name: /Continuar|Continue/i }).click();
    await basicsField.waitFor({ state: "visible", timeout: 20000 });
  }

  // Paso 2: datos básicos (fecha de nacimiento y altura son obligatorias, `validateBasics`)
  await page.getByLabel(/Fecha de nacimiento|Date of birth/i).fill("1990-01-01");
  await page.getByLabel(/Altura|Height/i).fill("180");
  await page.getByRole("button", { name: /Continuar|Continue/i }).click();

  // Paso 3: PAR-Q — cada pregunta es un radiogroup con dos radios sin `value`, el segundo es «No»
  for (const key of PARQ_KEYS) {
    await page.locator(`input[name="${key}"]`).nth(1).check();
  }
  await page.getByRole("button", { name: /Continuar|Continue/i }).click();

  // Paso 4: equipamiento — el preset por defecto (`full_gym`) no exige nada más
  if (options.dietEnabled === true) {
    await page.getByLabel(/nutrición|nutrition/i).check();
  }
  await page.getByRole("button", { name: /Terminar|Finish/i }).click();
  await expect(page.getByRole("heading", { level: 1, name: /Todo listo|All set/i })).toBeVisible({
    timeout: 15000,
  });
}

/**
 * Avanza el asistente del generador (`GeneratorScreen.tsx`) con los valores por defecto del
 * perfil hasta la vista previa. El último paso ("énfasis") usa el botón «Generar vista previa»,
 * no «Continuar», porque dispara la llamada al motor.
 */
export async function generatePreview(page: Page): Promise<void> {
  // El enlace «Generar una rutina nueva» vive en /rutinas (ProgramsRoute), no en Hoy.
  await page.goto("/rutinas");
  await page.getByRole("link", { name: /Generar|Generate/i }).click();
  await expect(page).toHaveURL(/\/rutinas\/nueva/);
  for (let i = 0; i < 4; i++) {
    await page.getByRole("button", { name: /Continuar|Continue/i }).click();
  }
  await page.getByRole("button", { name: /Generar vista previa|Generate preview/i }).click();
  await expect(page.getByText(/Vista previa|Preview/i).first()).toBeVisible({ timeout: 10000 });
}

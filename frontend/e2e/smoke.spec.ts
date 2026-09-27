import { expect, test } from "@playwright/test";

test("la aplicación carga en español, y sin sesión redirige a iniciar sesión", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Forja");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  // AuthGate: sin cookie de sesión, cualquier ruta protegida redirige a /login.
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

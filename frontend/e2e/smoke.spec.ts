import { expect, test } from "@playwright/test";

test("la aplicación carga en español con su encabezado principal", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Forja");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("heading", { level: 1, name: "Forja" })).toBeVisible();
});

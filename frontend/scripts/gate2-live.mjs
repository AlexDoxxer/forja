// Recorrido Gate 2 contra la API REAL (no MSW): alta → onboarding → generar → activar →
// entrenar (con descanso) → resumen → progreso. Guarda capturas en docs/screenshots/.
//
// Uso (con la API en :8000 y `vite` en :5173, ver docs/handoffs/f2-frontend-integration.md):
//   BASE_URL=http://localhost:5173 node scripts/gate2-live.mjs
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), "../../docs/screenshots");
mkdirSync(OUT, { recursive: true });
const email = `gate2-${Date.now()}@example.com`;
const problems = [];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "es-ES" });
const p = await ctx.newPage();
p.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
p.on("response", async (r) => {
  if (r.url().includes("/api/") && r.status() >= 400 && !(r.status() === 401 && r.url().endsWith("/auth/me"))) {
    problems.push(`HTTP ${r.status()} ${r.request().method()} ${r.url().replace(BASE, "")} ${(await r.text().catch(() => "")).slice(0, 200)}`);
  }
});
p.on("request", (r) => { if (r.url().includes("/finish")) console.log("[gate2] finish", r.postData()); });
const shot = (name, opts = {}) => p.screenshot({ path: `${OUT}/${name}.png`, ...opts });
const step = (msg) => console.log(`[gate2] ${msg}`);

// 1. Alta + onboarding
await p.goto(`${BASE}/onboarding`);
await shot("01-onboarding-cuenta");
await p.getByLabel("Correo electrónico").fill(email);
await p.getByLabel("Contraseña").fill("correct-horse-battery");
await p.getByLabel(/Nombre para mostrar/).fill("Ana");
await p.getByRole("button", { name: "Continuar" }).click();
await p.getByLabel(/Fecha de nacimiento/).fill("1992-04-15");
await p.getByLabel(/Altura/).fill("170");
await p.getByLabel(/Peso \(kg\)/).fill("70");
await p.getByRole("button", { name: "Continuar" }).click();
for (const r of await p.getByRole("radio", { name: "No" }).all()) await r.check();
await p.getByRole("button", { name: "Continuar" }).click();
await p.getByRole("button", { name: "Terminar" }).click();
await p.getByText("Todo listo").waitFor();
step("onboarding OK");

// 2. Generar y activar
await p.goto(`${BASE}/rutinas/nueva`);
await shot("02-generador-objetivo");
await p.getByRole("button", { name: /^Hipertrofia/ }).click();
for (let i = 0; i < 5; i++) await p.getByRole("button", { name: /Continuar|Generar|Ver vista previa/ }).first().click();
await p.getByText("Por qué esta rutina").waitFor();
await p.getByRole("button", { name: /Guardar y activar/ }).waitFor();
await p.waitForTimeout(1500);
await shot("03-generador-vista-previa", { fullPage: false });
await p.getByRole("button", { name: /Guardar y activar/ }).click();
await p.getByText("Rutina guardada y activada", { exact: true }).waitFor();
await shot("04-rutinas");
step("generar + activar OK");

// 3. Hoy y sesión
await p.goto(`${BASE}/`);
await p.getByText(/Toca hoy/).waitFor();
await shot("05-hoy");
await p.getByRole("button", { name: /Empezar/ }).or(p.getByRole("link", { name: /Empezar/ })).first().click();
await p.waitForURL(/\/sesion/);
let restShot = false;
let sets = 0;
for (let guard = 0; guard < 300; guard++) {
  if (await p.getByText("¿Qué esfuerzo has sentido?").isVisible().catch(() => false)) break;
  const done = p.getByRole("button", { name: "Serie hecha" });
  if (await done.isVisible().catch(() => false)) {
    if (sets === 3) {
      await p.evaluate(() => window.scrollTo(0, 0));
      await shot("06-sesion-serie");
    }
    const fields = p.locator("button[aria-pressed]").filter({ hasText: /Peso|Repeticiones/ });
    const pad = p.locator("[role=group][aria-label^=Teclado] button");
    for (let i = 0; i < (await fields.count()); i++) {
      await fields.nth(i).click();
      for (let k = 0; k < 5; k++) await pad.nth(11).click();
      await pad.nth(i === 0 ? 5 : 7).click(); // peso 6 · reps 8
      if (i === 0) await pad.nth(10).click(); // 60 kg
    }
    await done.click();
    sets += 1;
    await p.waitForTimeout(350);
    continue;
  }
  const skip = p.getByRole("button", { name: /Saltar/ });
  if (await skip.isVisible().catch(() => false)) {
    if (!restShot) {
      restShot = true;
      await p.waitForTimeout(1200);
      await p.evaluate(() => window.scrollTo(0, 0));
      await shot("07-sesion-descanso");
    }
    await skip.click();
    await p.waitForTimeout(250);
    continue;
  }
  await p.waitForTimeout(300);
}
step(`series registradas: ${sets}, descanso capturado: ${restShot}`);
await p.locator("button[aria-pressed]").filter({ hasText: "7" }).first().click();
await shot("08-sesion-esfuerzo");
await p.getByRole("button", { name: "Guardar y ver resumen" }).click();
await p.waitForURL(/resumen/);
await p.waitForTimeout(7000);
await shot("09-resumen-sesion");
step("sesión OK");

// 4. Progreso y resto de pantallas
await p.goto(`${BASE}/progreso`);
await p.waitForTimeout(2500);
await shot("10-progreso");
await p.goto(`${BASE}/`);
await p.waitForTimeout(1500);
await shot("11-hoy-tras-sesion");
await p.goto(`${BASE}/biblioteca`);
await p.waitForTimeout(2500);
await shot("12-biblioteca");
await p.locator("a[href^='/biblioteca/']").first().click();
await p.waitForTimeout(2000);
await shot("13-detalle-ejercicio");
await p.goto(`${BASE}/rutinas`);
await p.getByRole("link", { name: /Editar/ }).first().click();
await p.waitForTimeout(2000);
await shot("14-editor");
await p.goto(`${BASE}/perfil`);
await p.waitForTimeout(1500);
await shot("15-perfil");
const d = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: "es-ES", storageState: await ctx.storageState() });
const dp = await d.newPage();
await dp.goto(`${BASE}/progreso`);
await dp.waitForTimeout(2500);
await dp.screenshot({ path: `${OUT}/16-progreso-escritorio.png` });
await dp.goto(`${BASE}/biblioteca`);
await dp.waitForTimeout(2500);
await dp.screenshot({ path: `${OUT}/17-biblioteca-escritorio.png` });

console.log(problems.length === 0 ? "[gate2] sin errores HTTP/JS" : `[gate2] PROBLEMAS:\n${problems.join("\n")}`);
await browser.close();
process.exit(problems.length === 0 ? 0 : 1);

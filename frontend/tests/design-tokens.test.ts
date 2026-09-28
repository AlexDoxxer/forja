import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const TOKENS_PATH = resolve(__dirname, "../src/styles/tokens.css");

/** Extrae los pares `--token: #hex;` de un bloque de reglas CSS. */
function extractHexTokens(block: string): Record<string, string> {
  const tokens: Record<string, string> = {};
  const pattern = /--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g;
  for (const match of block.matchAll(pattern)) {
    const [, name, hex] = match;
    if (name !== undefined && hex !== undefined) {
      tokens[name] = hex;
    }
  }
  return tokens;
}

function readTokenBlocks(): { dark: Record<string, string>; light: Record<string, string> } {
  const css = readFileSync(TOKENS_PATH, "utf8");
  const lightStart = css.indexOf(':root[data-theme="light"]');
  const darkBlock = css.slice(0, lightStart === -1 ? css.length : lightStart);
  const lightBlockRaw = lightStart === -1 ? "" : css.slice(lightStart);
  const dark = extractHexTokens(darkBlock);
  const light = { ...dark, ...extractHexTokens(lightBlockRaw) };
  return { dark, light };
}

function channelLuminance(channel: number): number {
  const normalized = channel / 255;
  return normalized <= 0.03928 ? normalized / 12.92 : Math.pow((normalized + 0.055) / 1.055, 2.4);
}

function relativeLuminance(hex: string): number {
  const value = hex.replace("#", "");
  const r = Number.parseInt(value.slice(0, 2), 16);
  const g = Number.parseInt(value.slice(2, 4), 16);
  const b = Number.parseInt(value.slice(4, 6), 16);
  return 0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b);
}

/** Devuelve el valor de un token o falla la prueba si no existe (evita asertar `!`/`as`). */
function requireToken(tokens: Record<string, string>, name: string): string {
  const value = tokens[name];
  if (value === undefined) {
    throw new Error(`El token --${name} no está definido en tokens.css`);
  }
  return value;
}

/** Ratio de contraste WCAG 2.x entre dos colores hexadecimales. */
function contrastRatio(a: string, b: string): number {
  const luminanceA = relativeLuminance(a);
  const luminanceB = relativeLuminance(b);
  const lighter = Math.max(luminanceA, luminanceB);
  const darker = Math.min(luminanceA, luminanceB);
  return (lighter + 0.05) / (darker + 0.05);
}

const AA_NORMAL_TEXT = 4.5;
const AA_LARGE_TEXT_OR_UI = 3;

describe("tokens de diseño — contraste WCAG AA (MASTER_PROMPT §10.1)", () => {
  const { dark, light } = readTokenBlocks();

  it.each([
    ["texto sobre fondo", "color-text", "color-bg"],
    ["texto sobre superficie 1", "color-text", "color-surface-1"],
    ["texto sobre superficie 2", "color-text", "color-surface-2"],
    ["éxito sobre fondo", "color-success-text", "color-bg"],
    ["aviso sobre fondo", "color-warning-text", "color-bg"],
    ["error sobre fondo", "color-error-text", "color-bg"],
    // Botón primario deshabilitado (F5, corrección «Hoy»): texto atenuado sobre superficie 2.
    ["texto atenuado sobre superficie 2 (botón primario deshabilitado)", "color-text-muted", "color-surface-2"],
  ])("tema oscuro: %s cumple AA (>= 4.5:1)", (_label, fg, bg) => {
    const ratio = contrastRatio(requireToken(dark, fg), requireToken(dark, bg));
    expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it.each([
    ["texto sobre fondo", "color-text", "color-bg"],
    ["texto sobre superficie 1", "color-text", "color-surface-1"],
    ["texto sobre superficie 2", "color-text", "color-surface-2"],
    ["éxito sobre fondo", "color-success-text", "color-bg"],
    ["aviso sobre fondo", "color-warning-text", "color-bg"],
    ["error sobre fondo", "color-error-text", "color-bg"],
    // Botón primario deshabilitado (F5, corrección «Hoy»): texto atenuado sobre superficie 2.
    ["texto atenuado sobre superficie 2 (botón primario deshabilitado)", "color-text-muted", "color-surface-2"],
  ])("tema claro: %s cumple AA (>= 4.5:1)", (_label, fg, bg) => {
    const ratio = contrastRatio(requireToken(light, fg), requireToken(light, bg));
    expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it.each([
    ["tinta sobre acento", "color-on-accent", "color-accent"],
    ["tinta sobre acento 2", "color-on-accent", "color-accent-2"],
  ])("botones primarios: %s cumple AA de texto grande/UI (>= 3:1)", (_label, fg, bg) => {
    const ratio = contrastRatio(requireToken(dark, fg), requireToken(dark, bg));
    expect(ratio).toBeGreaterThanOrEqual(AA_LARGE_TEXT_OR_UI);
  });
});

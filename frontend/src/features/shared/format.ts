import { i18next } from "../../i18n";

/** Formateo con `Intl` en el idioma activo (MASTER_PROMPT §10.4). */
export function formatNumber(value: number, maximumFractionDigits = 1): string {
  return new Intl.NumberFormat(i18next.language, { maximumFractionDigits }).format(value);
}

export function formatDate(value: string | Date, options: Intl.DateTimeFormatOptions = { dateStyle: "medium" }): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(i18next.language, options).format(date);
}

/** `mm:ss` para cronómetros. */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(s / 60);
  return `${String(minutes)}:${String(s % 60).padStart(2, "0")}`;
}

/** Parte un número decimal escrito con coma o punto; `null` si no es un número válido. */
export function parseDecimal(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number(text.replace(",", "."));
  return Number.isFinite(value) ? value : null;
}

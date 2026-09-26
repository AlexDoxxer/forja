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

import type { components } from "../../lib/api/schema";

type Prescription = components["schemas"]["ExercisePrescription"];

/** «3×8-12», «3×45 s» (con «/lado» si es por lado). Solo presentación; la prescripción la fija el motor. */
export function formatPrescription(p: Pick<Prescription, "sets" | "rep_min" | "rep_max" | "duration_s" | "per_side">, perSideLabel: string): string {
  let amount: string;
  if (p.duration_s !== null) {
    amount = `${String(p.duration_s)} s`;
  } else if (p.rep_min !== null && p.rep_max !== null) {
    amount = p.rep_min === p.rep_max ? String(p.rep_min) : `${String(p.rep_min)}-${String(p.rep_max)}`;
  } else {
    amount = String(p.rep_min ?? p.rep_max ?? "");
  }
  return `${String(p.sets)}×${amount}${p.per_side ? ` ${perSideLabel}` : ""}`;
}

/** Semilla aleatoria segura en JavaScript (entero <= 2^53-1) para «regenerar con otra semilla». */
export function randomSeed(): number {
  const buffer = new Uint32Array(2);
  crypto.getRandomValues(buffer);
  const high = (buffer[0] ?? 0) & 0x1fffff;
  const low = buffer[1] ?? 0;
  return high * 2 ** 32 + low;
}

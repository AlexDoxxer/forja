export interface WeightPoint {
  date: string;
  weightKg: number;
}

export interface WeightWithAverage extends WeightPoint {
  /** Media móvil de los últimos 7 días naturales (incluido el actual). */
  average7d: number;
}

const DAY_MS = 86_400_000;

/**
 * Media móvil de 7 días naturales del peso corporal (MASTER_PROMPT §10.2.8). Solo es
 * presentación de la serie ya guardada; el resumen «Hoy» usa la media que calcula el servidor.
 */
export function withMovingAverage(points: WeightPoint[]): WeightWithAverage[] {
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  return sorted.map((point, index) => {
    const end = Date.parse(point.date);
    const window = sorted
      .slice(0, index + 1)
      .filter((p) => end - Date.parse(p.date) < 7 * DAY_MS);
    const sum = window.reduce((acc, p) => acc + p.weightKg, 0);
    return { ...point, average7d: Math.round((sum / window.length) * 100) / 100 };
  });
}

export interface HeatCell {
  date: string;
  sessions: number;
  volumeKg: number;
  /** 0 = sin actividad; 1–4 = intensidad relativa al día de mayor volumen (cuartos). */
  level: 0 | 1 | 2 | 3 | 4;
}

/** Rejilla de semanas (columnas, lunes a domingo) para el calendario tipo mapa de calor. */
export function buildHeatmap(
  activity: { date: string; session_count: number; volume_kg: number }[],
  weeks: number,
  today: Date,
): HeatCell[][] {
  const byDate = new Map(activity.map((a) => [a.date, a]));
  const max = Math.max(0, ...activity.filter((a) => a.session_count > 0).map((a) => a.volume_kg));
  const level = (sessions: number, volume: number): HeatCell["level"] => {
    if (sessions === 0) return 0;
    const ratio = max === 0 ? 1 : volume / max;
    if (ratio <= 0.25) return 1;
    if (ratio <= 0.5) return 2;
    if (ratio <= 0.75) return 3;
    return 4;
  };
  const utc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const mondayOffset = (new Date(utc).getUTCDay() + 6) % 7;
  const start = utc - mondayOffset * DAY_MS - (weeks - 1) * 7 * DAY_MS;
  const columns: HeatCell[][] = [];
  for (let w = 0; w < weeks; w += 1) {
    const column: HeatCell[] = [];
    for (let d = 0; d < 7; d += 1) {
      const ms = start + (w * 7 + d) * DAY_MS;
      const iso = new Date(ms).toISOString().slice(0, 10);
      const entry = byDate.get(iso);
      const sessions = entry?.session_count ?? 0;
      const volumeKg = entry?.volume_kg ?? 0;
      column.push({ date: iso, sessions, volumeKg, level: level(sessions, volumeKg) });
    }
    columns.push(column);
  }
  return columns;
}

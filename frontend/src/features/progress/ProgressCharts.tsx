import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { WeightWithAverage } from "./math";

const INITIAL = { width: 320, height: 240 } as const;
const AXIS = { fontSize: 12, fill: "var(--color-text-muted)" } as const;
const GRID = "var(--color-border)";
const ACCENT = "var(--color-accent)";
const TOOLTIP_STYLE = {
  background: "var(--color-surface-2)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  color: "var(--color-text)",
} as const;

export interface VolumeBarDatum {
  group: string;
  label: string;
  sets: number;
  volumeKg: number;
}

/** Series efectivas por grupo muscular de una semana (barras horizontales, un solo tono). */
export function VolumeChart({ data }: { data: VolumeBarDatum[] }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <ResponsiveContainer width="100%" height={280} initialDimension={{ width: 320, height: 280 }}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="label" tick={AXIS} width={84} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value) => [String(value), t("progressB.effectiveSets")]}
        />
        <Bar dataKey="sets" fill={ACCENT} radius={[0, 4, 4, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface E1rmDatum {
  date: string;
  e1rm: number | null;
}

/** Evolución del e1RM de un ejercicio. */
export function E1rmChart({ data }: { data: E1rmDatum[] }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <ResponsiveContainer width="100%" height={240} initialDimension={INITIAL}>
      <LineChart data={data} margin={{ left: 0, right: 16 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="date" tick={AXIS} />
        <YAxis tick={AXIS} domain={["auto", "auto"]} unit=" kg" width={64} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => [`${String(value)} kg`, t("progressB.e1rm")]} />
        <Line type="monotone" dataKey="e1rm" stroke={ACCENT} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Peso corporal (puntos) y su media móvil de 7 días (línea). */
export function WeightChart({ data }: { data: WeightWithAverage[] }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <ResponsiveContainer width="100%" height={240} initialDimension={INITIAL}>
      <LineChart data={data} margin={{ left: 0, right: 16 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="date" tick={AXIS} />
        <YAxis tick={AXIS} domain={["auto", "auto"]} unit=" kg" width={64} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Line
          type="linear"
          dataKey="weightKg"
          name={t("progressB.weight")}
          stroke="var(--color-text-muted)"
          strokeWidth={0}
          dot={{ r: 3, fill: "var(--color-text-muted)" }}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="average7d"
          name={t("progressB.average7d")}
          stroke={ACCENT}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { components } from "../../lib/api/schema";

type GroupVolume = components["schemas"]["GroupVolume"];

/** Volumen semanal por grupo frente al rango objetivo. Recharts vive en un chunk diferido (§10.5). */
export default function VolumeChart({ volume }: { volume: readonly GroupVolume[] }): React.JSX.Element {
  const { t } = useTranslation();
  const data = volume.map((row) => ({
    group: t(`enums.group.${row.group}`),
    min: row.target_min,
    planned: row.planned_sets,
    max: row.target_max,
  }));
  return (
    <div style={{ width: "100%", height: 280 }} aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis dataKey="group" stroke="var(--color-text-muted)" tick={{ fontSize: 12 }} interval={0} angle={-30} textAnchor="end" height={60} />
          <YAxis stroke="var(--color-text-muted)" allowDecimals={false} />
          <Tooltip contentStyle={{ background: "var(--color-surface-1)", border: "1px solid var(--color-border)" }} />
          <Legend />
          <Bar dataKey="min" name={t("generator.preview.targetMin")} fill="var(--color-surface-2)" stroke="var(--color-border)" />
          <Bar dataKey="planned" name={t("generator.preview.planned")} fill="var(--color-accent)" />
          <Bar dataKey="max" name={t("generator.preview.targetMax")} fill="var(--color-text-muted)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

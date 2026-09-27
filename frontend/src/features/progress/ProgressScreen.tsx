import { lazy, Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import { formatDate, formatNumber } from "../shared/format";
import shared from "../shared/ui.module.css";
import { buildHeatmap, withMovingAverage } from "./math";
import { useBodyMetrics, useExerciseStats, useOverview, useRecords, useVolume } from "./queries";
import styles from "./progress.module.css";
import "./strings";

// Recharts vive en un chunk aparte (MASTER_PROMPT §10.5): solo se descarga al abrir Progreso.
const VolumeChart = lazy(async () => ({ default: (await import("./ProgressCharts")).VolumeChart }));
const E1rmChart = lazy(async () => ({ default: (await import("./ProgressCharts")).E1rmChart }));
const WeightChart = lazy(async () => ({ default: (await import("./ProgressCharts")).WeightChart }));

const HEAT_WEEKS = 26;
const LEVEL_CLASS = [undefined, styles["l1"], styles["l2"], styles["l3"], styles["l4"]] as const;

function Heatmap(): React.JSX.Element {
  const { t } = useTranslation();
  const overview = useOverview();
  const columns = useMemo(
    () => buildHeatmap(overview.data?.activity ?? [], HEAT_WEEKS, new Date()),
    [overview.data],
  );
  return (
    <section className={`${shared["card"] ?? ""} ${styles["heatCard"] ?? ""}`} aria-labelledby="heat-title">
      <h2 id="heat-title">{t("progressB.heatmap")}</h2>
      <p className={shared["muted"]}>{t("progressB.heatmapHelp")}</p>
      <QueryState
        isLoading={overview.isLoading}
        isError={overview.isError}
        loadingLabel={t("progress.loading")}
        errorLabel={t("progress.error")}
      >
        <ul
          className={styles["heatmap"]}
          aria-label={t("progressB.heatmap")}
          // Lo más reciente (última columna) debe verse sin desplazarse.
          ref={(node) => {
            if (node !== null) node.scrollLeft = node.scrollWidth;
          }}
        >
          {columns.flat().map((cell) => (
            <li
              key={cell.date}
              className={[styles["cell"], LEVEL_CLASS[cell.level]].filter(Boolean).join(" ")}
              aria-label={t("progressB.heatmapCell", {
                date: formatDate(cell.date),
                sessions: cell.sessions,
                volume: formatNumber(cell.volumeKg, 0),
              })}
              data-level={cell.level}
            />
          ))}
        </ul>
        <p className={styles["legend"]}>
          {t("progressB.heatmapLegendLess")}
          {[0, 1, 2, 3, 4].map((l) => (
            <span key={l} className={[styles["cell"], LEVEL_CLASS[l]].filter(Boolean).join(" ")} aria-hidden="true" />
          ))}
          {t("progressB.heatmapLegendMore")}
        </p>
      </QueryState>
    </section>
  );
}

function VolumeSection(): React.JSX.Element {
  const { t } = useTranslation();
  const volume = useVolume();
  const [weekIndex, setWeekIndex] = useState<number | null>(null);
  const weeks = volume.data?.weeks ?? [];
  const index = weekIndex ?? weeks.length - 1;
  const week = weeks[index];
  const data = (week?.groups ?? []).map((g) => ({
    group: g.group,
    label: t(`progressB.group_${g.group}`),
    sets: g.effective_sets,
    volumeKg: g.volume_kg,
  }));
  return (
    <section className={shared["card"]} aria-labelledby="vol-title">
      <h2 id="vol-title">{t("progressB.volume")}</h2>
      <QueryState
        isLoading={volume.isLoading}
        isError={volume.isError}
        loadingLabel={t("progress.loading")}
        errorLabel={t("progress.error")}
      >
        {week === undefined ? (
          <p className={shared["muted"]}>{t("progressB.noVolume")}</p>
        ) : (
          <div className={shared["stack"]}>
            <label className={shared["field"]}>
              {t("progressB.week")}
              <select
                value={index}
                onChange={(e) => {
                  setWeekIndex(Number(e.target.value));
                }}
              >
                {weeks.map((w, i) => (
                  <option key={w.week_start} value={i}>
                    {formatDate(w.week_start)}
                  </option>
                ))}
              </select>
            </label>
            <div className={styles["chartWrap"]}>
              <Suspense fallback={<p role="status">{t("progressB.chartLoading")}</p>}>
                <VolumeChart data={data} />
              </Suspense>
            </div>
            <DataTable
              caption={t("progressB.volume")}
              headers={[t("progressB.week"), t("progressB.effectiveSets"), "kg"]}
              rows={data.map((d) => [d.label, String(d.sets), formatNumber(d.volumeKg, 0)])}
            />
          </div>
        )}
      </QueryState>
    </section>
  );
}

function DataTable({ caption, headers, rows }: { caption: string; headers: string[]; rows: string[][] }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <details>
      <summary>{t("progressB.showData")}</summary>
      <table className={shared["table"]}>
        <caption className={shared["visuallyHidden"]}>{caption}</caption>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.join("|")}>
              {row.map((cell, i) => (
                <td key={`${String(i)}-${cell}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function E1rmSection(): React.JSX.Element {
  const { t } = useTranslation();
  const records = useRecords();
  const [selected, setSelected] = useState<string | null>(null);
  const options = useMemo(() => {
    const seen = new Map<string, string>();
    for (const r of records.data?.items ?? []) seen.set(r.exercise_id, r.exercise_name_es);
    return [...seen.entries()];
  }, [records.data]);
  const exerciseId = selected ?? options[0]?.[0] ?? null;
  const stats = useExerciseStats(exerciseId);
  const data = (stats.data?.points ?? []).map((p) => ({ date: p.date, e1rm: p.e1rm_kg }));

  return (
    <section className={shared["card"]} aria-labelledby="e1rm-title">
      <h2 id="e1rm-title">{t("progressB.e1rmTitle")}</h2>
      {options.length === 0 ? (
        <p className={shared["muted"]}>{t("progressB.noRecordsExercise")}</p>
      ) : (
        <div className={shared["stack"]}>
          <label className={shared["field"]}>
            {t("progressB.chooseExercise")}
            <select
              value={exerciseId ?? ""}
              onChange={(e) => {
                setSelected(e.target.value);
              }}
            >
              {options.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <QueryState
            isLoading={stats.isLoading}
            isError={stats.isError}
            loadingLabel={t("progress.loading")}
            errorLabel={t("progress.error")}
          >
            <div className={styles["chartWrap"]}>
              <Suspense fallback={<p role="status">{t("progressB.chartLoading")}</p>}>
                <E1rmChart data={data} />
              </Suspense>
            </div>
            <DataTable
              caption={t("progressB.e1rmTitle")}
              headers={[t("progressB.date"), t("progressB.e1rm")]}
              rows={data.map((d) => [formatDate(d.date), d.e1rm === null ? "–" : formatNumber(d.e1rm)])}
            />
          </QueryState>
        </div>
      )}
    </section>
  );
}

function RecordsSection(): React.JSX.Element {
  const { t } = useTranslation();
  const records = useRecords();
  return (
    <section className={shared["card"]} aria-labelledby="rec-title">
      <h2 id="rec-title">{t("progressB.records")}</h2>
      <QueryState
        isLoading={records.isLoading}
        isError={records.isError}
        loadingLabel={t("progress.loading")}
        errorLabel={t("progress.error")}
      >
        {records.data?.items.length === 0 ? (
          <p className={shared["muted"]}>{t("progressB.noRecords")}</p>
        ) : (
          <ul className={styles["records"]}>
            {records.data?.items.map((r) => (
              <li key={r.id} className={styles["record"]}>
                <span>
                  <strong>{r.exercise_name_es}</strong>
                  <br />
                  <small className={shared["muted"]}>
                    {t(`progressB.kind_${r.kind}`)} · {formatDate(r.achieved_at)}
                    {r.weight_kg !== null && r.reps !== null
                      ? ` · ${t("progressB.recordDetail", { weight: formatNumber(r.weight_kg), reps: r.reps })}`
                      : ""}
                  </small>
                </span>
                <strong>{t("progressB.recordLine", { value: formatNumber(r.value) })}</strong>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </section>
  );
}

function BodyWeightSection(): React.JSX.Element {
  const { t } = useTranslation();
  const metrics = useBodyMetrics();
  const data = useMemo(
    () => withMovingAverage((metrics.data?.items ?? []).map((m) => ({ date: m.date, weightKg: m.weight_kg }))),
    [metrics.data],
  );
  return (
    <section className={shared["card"]} aria-labelledby="bw-chart-title">
      <h2 id="bw-chart-title">{t("progressB.bodyWeight")}</h2>
      <QueryState
        isLoading={metrics.isLoading}
        isError={metrics.isError}
        loadingLabel={t("progress.loading")}
        errorLabel={t("progress.error")}
      >
        {data.length === 0 ? (
          <p className={shared["muted"]}>{t("progressB.noBodyWeight")}</p>
        ) : (
          <div className={shared["stack"]}>
            <div className={styles["chartWrap"]}>
              <Suspense fallback={<p role="status">{t("progressB.chartLoading")}</p>}>
                <WeightChart data={data} />
              </Suspense>
            </div>
            <DataTable
              caption={t("progressB.bodyWeight")}
              headers={[t("progressB.date"), t("progressB.weight"), t("progressB.average7d")]}
              rows={data.map((d) => [formatDate(d.date), formatNumber(d.weightKg), formatNumber(d.average7d)])}
            />
          </div>
        )}
      </QueryState>
    </section>
  );
}

/** Pantalla «Progreso» (MASTER_PROMPT §10.2.8). */
export function ProgressScreen(): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="progress-title" className={shared["page"]}>
      <h1 id="progress-title">{t("progress.title")}</h1>
      <div className={shared["grid"]}>
        <Heatmap />
        <RecordsSection />
      </div>
      <VolumeSection />
      <E1rmSection />
      <BodyWeightSection />
    </section>
  );
}

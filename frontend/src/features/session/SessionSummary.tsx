import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { IconTrophy } from "../../components/icons";
import { cx } from "../../lib/cx";
import { formatNumber } from "../shared/format";
import shared from "../shared/ui.module.css";
import { localVolumeKg, type PlayerState } from "./playerMachine";
import { fetchSessionSummary } from "./queries";
import { scheduler } from "./scheduler";
import { loadPlayerState } from "./storage";
import styles from "./session.module.css";
import "./strings";

export interface SessionSummaryProps {
  sessionUuid: string;
  onExit: () => void;
}

function localTotals(state: PlayerState): {
  durationS: number;
  volumeKg: number;
  sets: number;
  reps: number;
  exercises: number;
} {
  const work = state.sets.filter((s) => !s.isWarmup);
  const end = state.finishedAt === null ? Date.now() : Date.parse(state.finishedAt);
  return {
    durationS: Math.max(0, Math.round((end - Date.parse(state.startedAt)) / 1000)),
    volumeKg: localVolumeKg(state),
    sets: work.length,
    reps: work.reduce((n, s) => n + (s.reps ?? 0), 0),
    exercises: new Set(work.map((s) => s.slotKey)).size,
  };
}

/**
 * Resumen de sesión (MASTER_PROMPT §10.2.6). Los totales se muestran al instante desde el
 * estado local (funciona offline); los récords llegan del servidor en cuanto la sesión está
 * sincronizada (`POST /sessions/{id}/finish` es idempotente).
 */
export function SessionSummary({ sessionUuid, onExit }: SessionSummaryProps): React.JSX.Element {
  const { t } = useTranslation();
  const local = useQuery({
    queryKey: ["session-local", sessionUuid],
    queryFn: async () => (await loadPlayerState(sessionUuid)) ?? null,
  });
  const server = useQuery({
    queryKey: ["session-summary", sessionUuid],
    enabled: local.data?.phase === "completed",
    refetchInterval: (query) => (query.state.data == null ? 4000 : false),
    queryFn: async () => {
      let state = await loadPlayerState(sessionUuid);
      if (state?.serverId == null) {
        await scheduler.trigger();
        state = await loadPlayerState(sessionUuid);
      }
      if (state?.serverId == null || state.finishedAt === null) return null;
      return fetchSessionSummary(state.serverId, state.finishedAt, state.perceivedEffort);
    },
  });

  if (local.isLoading) return <p role="status">{t("session.summaryLoading")}</p>;
  if (local.data == null) {
    return (
      <section className={shared["stack"]}>
        <p>{t("session.empty")}</p>
        <button type="button" className={shared["btn"]} onClick={onExit}>
          {t("session.backToToday")}
        </button>
      </section>
    );
  }
  const totals = localTotals(local.data);
  const remote = server.data ?? null;
  const durationS = remote?.duration_s ?? totals.durationS;
  const volume = remote?.volume_kg ?? totals.volumeKg;
  const sets = remote?.total_sets ?? totals.sets;
  const reps = remote?.total_reps ?? totals.reps;
  const exercises = remote?.exercises_completed ?? totals.exercises;

  return (
    <section className={styles["player"]} aria-labelledby="summary-title">
      <h1 id="summary-title">{t("session.summaryTitle")}</h1>
      <p className={shared["muted"]}>{local.data.name}</p>
      <dl className={`${shared["card"] ?? ""} ${styles["summaryGrid"] ?? ""}`}>
        <div>
          <dt>{t("session.duration")}</dt>
          <dd>{t("session.minutes", { count: Math.max(1, Math.round(durationS / 60)) })}</dd>
        </div>
        <div>
          <dt>{t("session.volume")}</dt>
          <dd>{formatNumber(volume, 0)} kg</dd>
        </div>
        <div>
          <dt>{t("session.sets")}</dt>
          <dd>{sets}</dd>
        </div>
        <div>
          <dt>{t("session.totalReps")}</dt>
          <dd>{reps}</dd>
        </div>
        <div>
          <dt>{t("session.exercises")}</dt>
          <dd>{exercises}</dd>
        </div>
        {local.data.perceivedEffort !== null && (
          <div>
            <dt>{t("session.effortLabel")}</dt>
            <dd>{local.data.perceivedEffort}/10</dd>
          </div>
        )}
      </dl>
      <section className={shared["card"]} aria-labelledby="records-title">
        <div className={shared["cardHeader"]}>
          <span className={shared["cardIcon"]}>
            <IconTrophy />
          </span>
          <h2 id="records-title">{t("session.records")}</h2>
        </div>
        {remote === null ? (
          <p className={shared["muted"]} role="status">
            {t("session.localSummary")}
          </p>
        ) : remote.new_records.length === 0 ? (
          <p>{t("session.recordNone")}</p>
        ) : (
          <ul className={shared["list"]}>
            {remote.new_records.map((r) => (
              <li key={r.id} className={styles["record"]}>
                <strong>{r.exercise_name_es}</strong> · {t(`session.recordKind_${r.kind}`)}: {formatNumber(r.value)}
                {" kg"}
              </li>
            ))}
          </ul>
        )}
      </section>
      <button type="button" className={cx(shared["btn"], shared["primary"])} onClick={onExit}>
        {t("session.backToToday")}
      </button>
    </section>
  );
}

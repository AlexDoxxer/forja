import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ExerciseMedia } from "../../components/ExerciseMedia";
import { formatNumber, parseDecimal } from "../shared/format";
import shared from "../shared/ui.module.css";
import { ensureNotificationPermission, requestWakeLock, restFinished, type WakeLockHandle } from "./feedback";
import {
  currentSlot,
  restRemainingMs,
  workSetsDone,
  type PlayerSlot,
  type PlayerState,
} from "./playerMachine";
import { useAlternatives, useExerciseDetail, useProfilePrefs } from "./queries";
import { RestRing } from "./RestRing";
import { SessionNumberPad } from "./SessionNumberPad";
import { usePendingSync } from "./usePendingSync";
import { usePlayer } from "./usePlayer";
import "./strings";
import styles from "./session.module.css";

type Field = "weight" | "reps";

export interface SessionPlayerProps {
  sessionUuid?: string;
  /** Se llama al guardar la sesión terminada (navegar al resumen). */
  onFinished: (sessionUuid: string) => void;
  /** Sin sesión que reproducir: volver a «Hoy». */
  onExit: () => void;
}

const RIR_OPTIONS = [0, 1, 2, 3, 4, 5] as const;

function initialWeight(slot: PlayerSlot, state: PlayerState): string {
  const previous = [...state.sets].reverse().find((s) => s.slotKey === slot.key && !s.isWarmup);
  const value = previous?.weightKg ?? slot.suggestion?.suggested_weight_kg ?? null;
  return value === null ? "" : String(value).replace(".", ",");
}

function initialReps(slot: PlayerSlot, state: PlayerState): string {
  const previous = [...state.sets].reverse().find((s) => s.slotKey === slot.key && !s.isWarmup);
  const value = previous?.reps ?? slot.suggestion?.suggested_rep_max ?? slot.repMax;
  return value === null ? "" : String(value);
}

/** Reproductor de sesión (MASTER_PROMPT §10.2.5): un ejercicio y una serie a la vez. */
export function SessionPlayer({ sessionUuid, onFinished, onExit }: SessionPlayerProps): React.JSX.Element {
  const { t } = useTranslation();
  const player = usePlayer(sessionUuid);
  const { state } = player;
  const prefs = useProfilePrefs().data?.preferences;
  const pending = usePendingSync();
  const [field, setField] = useState<Field>("weight");
  const [weightText, setWeightText] = useState("");
  const [repsText, setRepsText] = useState("");
  const [rir, setRir] = useState<number | null>(null);
  const [showSteps, setShowSteps] = useState(false);
  const [showSwap, setShowSwap] = useState(false);
  const [effort, setEffort] = useState<number | null>(null);
  const [ending, setEnding] = useState(false);
  const slot = state === null ? null : currentSlot(state);
  const slotKey = slot?.key ?? null;
  const setIndex = state?.setIndex ?? 0;
  const swapId = slot?.exercise.id ?? null;

  // Wake Lock mientras la sesión está abierta; se readquiere al volver a primer plano.
  const lockWanted = state !== null && state.phase !== "completed";
  useEffect(() => {
    if (!lockWanted) return undefined;
    let handle: WakeLockHandle | null = null;
    let active = true;
    const acquire = (): void => {
      void requestWakeLock().then((h) => {
        if (active) handle = h;
        else void h?.release();
      });
    };
    acquire();
    const onVisible = (): void => {
      if (document.visibilityState === "visible") acquire();
    };
    document.addEventListener("visibilitychange", onVisible);
    void ensureNotificationPermission();
    return () => {
      active = false;
      document.removeEventListener("visibilitychange", onVisible);
      void handle?.release();
    };
  }, [lockWanted]);

  // Rellena el peso y las repeticiones al cambiar de serie o de ejercicio.
  useEffect(() => {
    if (state === null || slot === null) return;
    setWeightText(initialWeight(slot, state));
    setRepsText(initialReps(slot, state));
    setRir(slot.targetRir);
    setShowSteps(false);
    setShowSwap(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slotKey, setIndex, swapId]);

  const detail = useExerciseDetail(showSteps ? swapId : null);
  const alternatives = useAlternatives(swapId, showSwap);

  const { dispatch } = player;
  const onRestDone = useCallback(() => {
    dispatch({ type: "REST_DONE" });
    restFinished(
      { sounds: prefs?.sounds ?? true, vibration: prefs?.vibration ?? true },
      t("session.restOver"),
      t("session.restOverBody"),
    );
  }, [dispatch, prefs, t]);

  const doneSets = useMemo(() => (state === null ? 0 : state.sets.filter((s) => !s.isWarmup).length), [state]);
  const totalSets = useMemo(() => (state === null ? 0 : state.slots.reduce((n, s) => n + s.sets, 0)), [state]);

  if (player.loading) return <p role="status">{t("session.loading")}</p>;
  if (state === null) {
    return (
      <section className={shared["stack"]}>
        <p>{t("session.empty")}</p>
        <button type="button" className={shared["btn"]} onClick={onExit}>
          {t("session.backToToday")}
        </button>
      </section>
    );
  }

  if (state.phase !== "completed" && (state.phase === "finished" || ending || slot === null)) {
    return (
      <section className={styles["player"]} aria-labelledby="effort-title">
        <h1 id="effort-title">{t("session.effortTitle")}</h1>
        <p className={shared["muted"]}>{t("session.effortHelp")}</p>
        <div className={styles["rirRow"]} role="group" aria-label={t("session.effortTitle")}>
          {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              className={styles["rirBtn"]}
              aria-pressed={effort === n}
              aria-label={t("session.effort", { value: n })}
              onClick={() => {
                setEffort(n);
              }}
            >
              {n}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={styles["doneBtn"]}
          onClick={() => {
            player.finish(effort);
            onFinished(state.sessionUuid);
          }}
        >
          {t("session.saveFinish")}
        </button>
      </section>
    );
  }

  if (state.phase === "completed") {
    return (
      <section className={shared["stack"]}>
        <button type="button" className={shared["btn"]} onClick={() => { onFinished(state.sessionUuid); }}>
          {t("session.summaryTitle")}
        </button>
      </section>
    );
  }

  if (slot === null) return <p role="status">{t("session.loading")}</p>;

  const workDone = workSetsDone(state, slot.key);
  const suggestion = slot.suggestion;
  const submit = (): void => {
    player.logSet({ weightKg: parseDecimal(weightText), reps: parseDecimal(repsText), rir });
  };
  const platesText = (plates: number[]): string =>
    plates.length === 0 ? t("session.noPlates") : t("session.plates", { plates: plates.join(" + ") });

  const resting = state.phase === "resting" && state.rest !== null;
  const remainingSlots = state.slots.length;

  return (
    <section className={styles["player"]} aria-labelledby="player-title">
      <header className={styles["header"]}>
        <p className={shared["muted"]}>
          {t("session.exerciseOf", { current: state.slotIndex + 1, total: remainingSlots })}
        </p>
        <h1 id="player-title">{slot.exercise.name_es}</h1>
        <div
          className={styles["progress"]}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={totalSets}
          aria-valuenow={doneSets}
          aria-label={t("session.title")}
        >
          <div className={styles["progressBar"]} style={{ width: `${String(totalSets === 0 ? 0 : (doneSets / totalSets) * 100)}%` }} />
        </div>
        {pending > 0 && (
          <p className={shared["muted"]} role="status">
            {t("session.pendingSync", { count: pending })}
          </p>
        )}
      </header>

      <div className={styles["plate"]}>
        <ExerciseMedia media={slot.exercise.media} alt={slot.exercise.name_es} variant="animated" />
      </div>

      {resting && state.rest !== null ? (
        <RestRing
          rest={state.rest}
          onAdjust={(deltaMs) => {
            player.dispatch({ type: "REST_ADJUST", deltaMs, now: Date.now() });
          }}
          onSkip={() => {
            player.dispatch({ type: "REST_DONE" });
          }}
          onDone={onRestDone}
        />
      ) : null}
      {resting && state.rest !== null && restRemainingMs(state.rest, Date.now()) > 0 ? (
        <p className={shared["muted"]}>
          {t("session.next")}: {slot.exercise.name_es} · {t("session.setOf", { current: Math.min(workDone + 1, slot.sets), total: slot.sets })}
        </p>
      ) : null}

      <div className={shared["card"]}>
        <p>
          <strong>{t("session.setOf", { current: Math.min(workDone + 1, slot.sets), total: slot.sets })}</strong>
        </p>
        <dl className={styles["targets"]}>
          <div>
            <dt>{t("session.target")}</dt>
            <dd>
              {slot.repMin !== null && slot.repMax !== null
                ? t("session.repsRange", { min: slot.repMin, max: slot.repMax })
                : t("session.reps")}
              {slot.targetRir !== null ? ` · ${t("session.rirTarget", { rir: slot.targetRir })}` : ""}
            </dd>
          </div>
          {suggestion?.suggested_weight_kg != null && (
            <div>
              <dt>{t("session.suggested")}</dt>
              <dd>
                {formatNumber(suggestion.suggested_weight_kg)} kg
                <br />
                <small>{platesText(suggestion.plates_per_side_kg)}</small>
              </dd>
            </div>
          )}
          {suggestion?.last_performance != null && (
            <div>
              <dt>{t("session.lastTime")}</dt>
              <dd>
                {suggestion.last_performance.sets
                  .map((s) => t("session.lastSet", { weight: s.weight_kg ?? "–", reps: s.reps ?? "–" }))
                  .join(" · ")}
              </dd>
            </div>
          )}
        </dl>
        {suggestion !== null && <p className={shared["muted"]}>{suggestion.reason_es}</p>}
        {slot.notesEs !== null && (
          <p className={shared["notice"]} role="note">
            <strong>{t("session.notes")}: </strong>
            {slot.notesEs}
          </p>
        )}
      </div>

      {suggestion !== null && suggestion.warmup_sets.length > 0 && workDone === 0 && (
        <details className={shared["card"]}>
          <summary>{t("session.warmup")}</summary>
          <ul className={shared["list"]} aria-label={t("session.platesTitle")}>
            {suggestion.warmup_sets.map((w, i) => {
              const done = state.sets.some((s) => s.slotKey === slot.key && s.isWarmup && s.setIndex === i);
              return (
                <li key={`${String(w.percent)}-${String(i)}`} className={shared["row"]}>
                  <span>
                    {t("session.warmupSet", { weight: w.weight_kg, reps: w.reps, percent: w.percent })}
                    <br />
                    <small className={shared["muted"]}>{platesText(w.plates_per_side_kg)}</small>
                  </span>
                  <button
                    type="button"
                    className={shared["btn"]}
                    disabled={done}
                    onClick={() => {
                      player.logSet({ weightKg: w.weight_kg, reps: w.reps, rir: null, isWarmup: true });
                    }}
                  >
                    {t("session.warmupDone")}
                  </button>
                </li>
              );
            })}
          </ul>
        </details>
      )}

      {!resting && (
        <>
          <div className={styles["fields"]}>
            <button
              type="button"
              className={styles["fieldBtn"]}
              aria-pressed={field === "weight"}
              onClick={() => {
                setField("weight");
              }}
            >
              <span className={styles["fieldLabel"]}>{t("session.weight")}</span>
              <span className={styles["fieldValue"]} data-testid="weight-value">
                {weightText === "" ? "–" : weightText}
              </span>
            </button>
            <button
              type="button"
              className={styles["fieldBtn"]}
              aria-pressed={field === "reps"}
              onClick={() => {
                setField("reps");
              }}
            >
              <span className={styles["fieldLabel"]}>{t("session.repsField")}</span>
              <span className={styles["fieldValue"]} data-testid="reps-value">
                {repsText === "" ? "–" : repsText}
              </span>
            </button>
          </div>
          <SessionNumberPad
            value={field === "weight" ? weightText : repsText}
            onChange={field === "weight" ? setWeightText : setRepsText}
            allowDecimal={field === "weight"}
            fieldLabel={field === "weight" ? t("session.weight") : t("session.repsField")}
          />
          <div className={shared["stack"]}>
            <span id="rir-label">{t("session.rir")}</span>
            <div className={styles["rirRow"]} role="group" aria-labelledby="rir-label">
              {RIR_OPTIONS.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={styles["rirBtn"]}
                  aria-pressed={rir === n}
                  onClick={() => {
                    setRir(n);
                  }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <button type="button" className={styles["doneBtn"]} onClick={submit}>
            {t("session.done")}
          </button>
        </>
      )}

      <div className={shared["row"]}>
        <button type="button" className={shared["btn"]} onClick={() => { setShowSteps((v) => !v); }} aria-expanded={showSteps}>
          {showSteps ? t("session.hideInstructions") : t("session.instructions")}
        </button>
        <button type="button" className={shared["btn"]} onClick={() => { setShowSwap((v) => !v); }} aria-expanded={showSwap}>
          {t("session.swap")}
        </button>
        <button type="button" className={shared["btn"]} onClick={player.undoLast} disabled={state.sets.length === 0}>
          {t("session.undo")}
        </button>
        <button
          type="button"
          className={shared["btn"]}
          onClick={() => {
            setEnding(true);
          }}
        >
          {t("session.finishNow")}
        </button>
      </div>

      {showSteps && (
        <div className={shared["card"]}>
          <h2>{t("session.instructions")}</h2>
          {detail.data ? (
            <ol className={styles["steps"]}>
              {detail.data.instructions.steps.map((step, i) => (
                <li key={`${String(i)}-${step}`}>{step}</li>
              ))}
            </ol>
          ) : (
            <p role="status">{t("session.loading")}</p>
          )}
        </div>
      )}

      {showSwap && (
        <div className={shared["card"]}>
          <h2>{t("session.swapTitle")}</h2>
          {alternatives.data?.items.length === 0 && <p>{t("session.swapNone")}</p>}
          <ul className={shared["list"]}>
            {alternatives.data?.items.map((alt) => (
              <li key={alt.exercise.id}>
                <button
                  type="button"
                  className={shared["btn"]}
                  onClick={() => {
                    player.dispatch({ type: "SWAP_EXERCISE", exercise: alt.exercise });
                  }}
                >
                  {t("session.swapUse", { name: alt.exercise.name_es })}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

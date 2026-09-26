import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { formatClock } from "../shared/format";
import { restRemainingMs, type RestState } from "./playerMachine";
import styles from "./session.module.css";
import { useNow } from "./useNow";

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export interface RestRingProps {
  rest: RestState;
  onAdjust: (deltaMs: number) => void;
  onSkip: () => void;
  onDone: () => void;
}

/** Anillo de descanso con ±15 s y saltar. `aria-live` educado cada 15 s y en los últimos 3 s. */
export function RestRing({ rest, onAdjust, onSkip, onDone }: RestRingProps): React.JSX.Element {
  const { t } = useTranslation();
  const now = useNow(true);
  const remaining = restRemainingMs(rest, now);
  const total = Math.max(1, rest.endsAt - rest.startedAt);
  const fraction = Math.min(1, remaining / total);
  const seconds = Math.ceil(remaining / 1000);
  const doneRef = useRef(false);

  useEffect(() => {
    if (remaining === 0 && !doneRef.current) {
      doneRef.current = true;
      onDone();
    }
    if (remaining > 0) doneRef.current = false;
  }, [remaining, onDone]);

  const announce = seconds <= 3 || seconds % 15 === 0;
  return (
    <section className={styles["rest"]} aria-label={t("session.rest")}>
      <div className={styles["ringWrap"]}>
        <svg viewBox="0 0 120 120" className={styles["ring"]} aria-hidden="true">
          <circle cx="60" cy="60" r={RADIUS} className={styles["ringTrack"]} />
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            className={styles["ringValue"]}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - fraction)}
            transform="rotate(-90 60 60)"
          />
        </svg>
        <span className={styles["ringTime"]}>{formatClock(seconds)}</span>
      </div>
      <p className={styles["visuallyHidden"]} role="status" aria-live="polite">
        {announce ? t("session.restRemaining", { seconds }) : ""}
      </p>
      <div className={styles["restActions"]}>
        <button
          type="button"
          className={styles["restBtn"]}
          onClick={() => {
            onAdjust(-15_000);
          }}
        >
          <span aria-hidden="true">−15 s</span>
          <span className={styles["visuallyHidden"]}>{t("session.restMinus")}</span>
        </button>
        <button type="button" className={styles["restBtn"]} onClick={onSkip}>
          {t("session.restSkip")}
        </button>
        <button
          type="button"
          className={styles["restBtn"]}
          onClick={() => {
            onAdjust(15_000);
          }}
        >
          <span aria-hidden="true">+15 s</span>
          <span className={styles["visuallyHidden"]}>{t("session.restPlus")}</span>
        </button>
      </div>
    </section>
  );
}

import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { useReducedMotion } from "../../lib/useReducedMotion";
import { formatClock } from "../shared/format";
import { restRemainingMs, type RestState } from "./playerMachine";
import styles from "./session.module.css";
import { useNow } from "./useNow";

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** Últimos segundos en los que el anillo «respira» como una brasa que se enfría. */
const FINAL_STRETCH_S = 5;
/** Mismos tonos que `--color-accent`/`--color-accent-2` en `tokens.css` (sin tocar los tokens):
 * Framer Motion necesita valores de color literales para poder interpolarlos. */
const EMBER_HOT = "#ff6a2b";
const EMBER_HOTTER = "#ffb23f";

export interface RestRingProps {
  rest: RestState;
  onAdjust: (deltaMs: number) => void;
  onSkip: () => void;
  onDone: () => void;
}

/**
 * Anillo de descanso con ±15 s y saltar. `aria-live` educado cada 15 s y en los últimos 3 s.
 * El progreso interpola con Framer Motion en vez de saltar entre lecturas del reloj (§10.1); en
 * los últimos 5 s el anillo pulsa suavemente en tonos brasa, como si se enfriara — el único
 * momento de movimiento con «carácter» de esta pantalla. Se omite con `prefers-reduced-motion`.
 */
export function RestRing({ rest, onAdjust, onSkip, onDone }: RestRingProps): React.JSX.Element {
  const { t } = useTranslation();
  const now = useNow(true);
  const reducedMotion = useReducedMotion();
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
  const isFinalStretch = seconds > 0 && seconds <= FINAL_STRETCH_S && !reducedMotion;

  return (
    <section className={styles["rest"]} aria-label={t("session.rest")}>
      <motion.div
        className={styles["ringWrap"]}
        initial={false}
        animate={
          isFinalStretch
            ? {
                scale: [1, 1.04, 1],
                filter: [
                  "drop-shadow(0 0 0px rgba(255, 106, 43, 0))",
                  "drop-shadow(0 0 16px rgba(255, 106, 43, 0.6))",
                  "drop-shadow(0 0 0px rgba(255, 106, 43, 0))",
                ],
              }
            : { scale: 1, filter: "drop-shadow(0 0 0px rgba(255, 106, 43, 0))" }
        }
        transition={isFinalStretch ? { duration: 1.1, repeat: Infinity, ease: "easeInOut" } : { duration: 0.3 }}
      >
        <svg viewBox="0 0 120 120" className={styles["ring"]} aria-hidden="true">
          <circle cx="60" cy="60" r={RADIUS} className={styles["ringTrack"]} />
          <motion.circle
            cx="60"
            cy="60"
            r={RADIUS}
            className={styles["ringValue"]}
            strokeDasharray={CIRCUMFERENCE}
            transform="rotate(-90 60 60)"
            initial={false}
            animate={{
              strokeDashoffset: CIRCUMFERENCE * (1 - fraction),
              stroke: isFinalStretch ? [EMBER_HOT, EMBER_HOTTER, EMBER_HOT] : EMBER_HOT,
            }}
            transition={{
              strokeDashoffset: { duration: reducedMotion ? 0 : 0.25, ease: "linear" },
              stroke: { duration: 1.1, repeat: isFinalStretch ? Infinity : 0, ease: "easeInOut" },
            }}
          />
        </svg>
        <span className={styles["ringTime"]}>{formatClock(seconds)}</span>
      </motion.div>
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

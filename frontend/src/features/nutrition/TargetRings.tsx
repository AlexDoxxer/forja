import { useTranslation } from "react-i18next";

import type { components } from "../../lib/api/schema";
import { formatNumber } from "../shared/format";
import styles from "./nutrition.module.css";

type Target = components["schemas"]["NutritionTarget"];

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** Energía por gramo (Atwater); solo para dibujar la proporción del anillo. */
const KCAL_PER_G = { protein: 4, fat: 9, carbs: 4 } as const;

interface RingProps {
  name: string;
  valueText: string;
  fraction: number;
  caption?: string;
}

function Ring({ name, valueText, fraction, caption }: RingProps): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <li className={styles["ringItem"]}>
      <svg
        viewBox="0 0 100 100"
        className={styles["ring"]}
        role="img"
        aria-label={t("nutrition.ringLabel", { name, value: valueText })}
      >
        <circle cx="50" cy="50" r={RADIUS} className={styles["track"]} />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          className={styles["value"]}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - Math.min(1, Math.max(0, fraction)))}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <span className={styles["ringValue"]}>{valueText}</span>
      <span>{name}</span>
      {caption !== undefined && <small>{caption}</small>}
    </li>
  );
}

/** Objetivo diario en anillos de tono neutro (sin colores que juzguen; MASTER_PROMPT §10.2.9). */
export function TargetRings({ target }: { target: Target }): React.JSX.Element | null {
  const { t } = useTranslation();
  if (target.target_kcal === null) return null;
  const kcal = target.target_kcal;
  const share = (grams: number | null, factor: number): number =>
    grams === null || kcal === 0 ? 0 : (grams * factor) / kcal;
  const macro = (key: "protein" | "fat" | "carbs", grams: number | null): React.JSX.Element => {
    const fraction = share(grams, KCAL_PER_G[key]);
    return (
      <Ring
        name={t(`nutrition.${key}`)}
        valueText={grams === null ? "–" : t("nutrition.grams", { value: formatNumber(grams, 0) })}
        fraction={fraction}
        caption={t("nutrition.ringShare", { percent: Math.round(fraction * 100) })}
      />
    );
  };
  return (
    <ul className={styles["rings"]} aria-label={t("nutrition.targetTitle")}>
      <Ring name={t("nutrition.kcal")} valueText={formatNumber(kcal, 0)} fraction={1} />
      {macro("protein", target.protein_g)}
      {macro("fat", target.fat_g)}
      {macro("carbs", target.carbs_g)}
    </ul>
  );
}

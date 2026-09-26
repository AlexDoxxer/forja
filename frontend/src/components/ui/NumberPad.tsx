import { useTranslation } from "react-i18next";

import { Button } from "./Button";
import styles from "./ui.module.css";

export interface NumberPadProps {
  /** Valor actual como texto (permite «12.» mientras se teclea). */
  value: string;
  onChange: (value: string) => void;
  /** Permite coma/punto decimal (pesos); las repeticiones no. */
  allowDecimal?: boolean;
  maxLength?: number;
}

/** Teclado numérico propio para peso/reps del reproductor (§10.2.5); teclas de 56 px. */
export function NumberPad({ value, onChange, allowDecimal = false, maxLength = 6 }: NumberPadProps): React.JSX.Element {
  const { t } = useTranslation();

  const append = (digit: string): void => {
    if (value.length >= maxLength) return;
    onChange(value === "0" && digit !== "." ? digit : value + digit);
  };

  return (
    <div className={styles["pad"]} role="group" aria-label={t("ui.numberPad")}>
      {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((digit) => (
        <Button
          key={digit}
          className={styles["padKey"]}
          onClick={() => {
            append(digit);
          }}
        >
          {digit}
        </Button>
      ))}
      <Button
        className={styles["padKey"]}
        disabled={!allowDecimal || value.includes(".")}
        aria-label={t("ui.decimalPoint")}
        onClick={() => {
          append(value === "" ? "0." : ".");
        }}
      >
        .
      </Button>
      <Button
        className={styles["padKey"]}
        onClick={() => {
          append("0");
        }}
      >
        0
      </Button>
      <Button
        className={styles["padKey"]}
        aria-label={t("ui.backspace")}
        onClick={() => {
          onChange(value.slice(0, -1));
        }}
      >
        ⌫
      </Button>
    </div>
  );
}

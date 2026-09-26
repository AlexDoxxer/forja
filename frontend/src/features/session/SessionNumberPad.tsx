import { useTranslation } from "react-i18next";

import { applyKey } from "./keypad";
import styles from "./session.module.css";

export interface SessionNumberPadProps {
  /** Texto actual del campo (permite «7,5» a medio escribir). */
  value: string;
  onChange: (next: string) => void;
  allowDecimal: boolean;
  /** Nombre del campo, para el nombre accesible del grupo. */
  fieldLabel: string;
}

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"] as const;

/** Teclado numérico propio del reproductor: objetivos táctiles de 56 px (>= 48 px, §10.1). */
export function SessionNumberPad({
  value,
  onChange,
  allowDecimal,
  fieldLabel,
}: SessionNumberPadProps): React.JSX.Element {
  const { t } = useTranslation();
  const press = (key: string): void => {
    onChange(applyKey(value, key, allowDecimal));
  };

  return (
    <div role="group" aria-label={t("session.keypadFor", { field: fieldLabel })} className={styles["keypad"]}>
      {KEYS.map((key) => (
        <button
          key={key}
          type="button"
          className={styles["key"]}
          aria-label={t("session.key", { key })}
          onClick={() => {
            press(key);
          }}
        >
          {key}
        </button>
      ))}
      <button
        type="button"
        className={styles["key"]}
        aria-label={t("session.decimal")}
        disabled={!allowDecimal}
        onClick={() => {
          press(",");
        }}
      >
        ,
      </button>
      <button
        type="button"
        className={styles["key"]}
        aria-label={t("session.key", { key: "0" })}
        onClick={() => {
          press("0");
        }}
      >
        0
      </button>
      <button
        type="button"
        className={styles["key"]}
        aria-label={t("session.backspace")}
        onClick={() => {
          press("back");
        }}
      >
        ⌫
      </button>
    </div>
  );
}

import { useId, type HTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";

import { cx } from "../../lib/cx";
import styles from "./ui.module.css";

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: string;
  hint?: string;
  error?: string | null;
}

/** Campo de texto con etiqueta, pista y error asociados (`aria-describedby`, `aria-invalid`). */
export function TextField({ label, hint, error, className, ...rest }: TextFieldProps): React.JSX.Element {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint === undefined ? null : hintId, error ? errorId : null].filter(Boolean).join(" ");
  return (
    <div className={styles["field"]}>
      <label htmlFor={id} className={styles["label"]}>
        {label}
      </label>
      <input
        id={id}
        className={cx(styles["input"], className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        {...rest}
      />
      {hint !== undefined && (
        <p id={hintId} className={styles["hint"]}>
          {hint}
        </p>
      )}
      {error ? (
        <p id={errorId} role="alert" className={styles["fieldError"]}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export interface CheckFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> {
  label: ReactNode;
}

/** Casilla con etiqueta clicable de >= 48 px. */
export function CheckField({ label, ...rest }: CheckFieldProps): React.JSX.Element {
  const id = useId();
  return (
    <div className={styles["checkRow"]}>
      <input id={id} type="checkbox" {...rest} />
      <label htmlFor={id}>{label}</label>
    </div>
  );
}

/** Tarjeta contenedora neutra. */
export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>): React.JSX.Element {
  return <div className={cx(styles["card"], className)} {...rest} />;
}

export interface ChoiceCardProps {
  selected: boolean;
  onSelect: () => void;
  title: string;
  description?: string;
}

/** Tarjeta seleccionable con explicación (objetivo del generador, etc.). */
export function ChoiceCard({ selected, onSelect, title, description }: ChoiceCardProps): React.JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cx(styles["card"], styles["cardSelectable"])}
      onClick={onSelect}
    >
      <strong>{title}</strong>
      {description !== undefined && <span className={styles["hint"]} style={{ display: "block" }}>{description}</span>}
    </button>
  );
}

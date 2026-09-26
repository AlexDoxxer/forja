import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cx } from "../../lib/cx";
import styles from "./ui.module.css";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "md" | "sm";
}

/** Botón base: objetivo táctil >= 48 px (§10.1); el degradado solo en la acción primaria. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(styles["button"], styles[variant], size === "sm" && styles["small"], className)}
      {...rest}
    />
  );
});

export interface ChipProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  selected: boolean;
  onSelectedChange?: (selected: boolean) => void;
}

/** Chip conmutable (filtros, equipamiento…). Estado accesible con `aria-pressed`. */
export function Chip({ selected, onSelectedChange, className, onClick, ...rest }: ChipProps): React.JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cx(styles["chip"], className)}
      onClick={(event) => {
        onClick?.(event);
        onSelectedChange?.(!selected);
      }}
      {...rest}
    />
  );
}

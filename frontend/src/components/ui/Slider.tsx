import * as RadixSlider from "@radix-ui/react-slider";
import { useId } from "react";

import styles from "./ui.module.css";

export interface SliderProps {
  label: string;
  value: number;
  onValueChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  /** Texto legible del valor actual (p. ej. «60 min»); se anuncia como `aria-valuetext`. */
  valueText?: string;
}

/** Deslizador accesible con etiqueta y valor visibles (no solo por posición). */
export function Slider({ label, value, onValueChange, min, max, step = 1, valueText }: SliderProps): React.JSX.Element {
  const labelId = useId();
  return (
    <div className={styles["field"]}>
      <span id={labelId} className={styles["label"]}>
        {label}: <strong>{valueText ?? String(value)}</strong>
      </span>
      <RadixSlider.Root
        className={styles["sliderRoot"]}
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={(next) => {
          const first = next[0];
          if (first !== undefined) onValueChange(first);
        }}
      >
        <RadixSlider.Track className={styles["sliderTrack"]}>
          <RadixSlider.Range className={styles["sliderRange"]} />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          className={styles["sliderThumb"]}
          aria-labelledby={labelId}
          {...(valueText === undefined ? {} : { "aria-valuetext": valueText })}
        />
      </RadixSlider.Root>
    </div>
  );
}

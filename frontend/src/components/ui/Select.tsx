import * as RadixSelect from "@radix-ui/react-select";
import { useId } from "react";

import styles from "./ui.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: readonly SelectOption[];
  placeholder?: string;
}

/** Selector accesible sobre Radix con etiqueta visible. */
export function Select({ label, value, onValueChange, options, placeholder }: SelectProps): React.JSX.Element {
  const labelId = useId();
  return (
    <div className={styles["field"]}>
      <span id={labelId} className={styles["label"]}>
        {label}
      </span>
      <RadixSelect.Root value={value} onValueChange={onValueChange}>
        <RadixSelect.Trigger className={styles["selectTrigger"]} aria-labelledby={labelId}>
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon aria-hidden="true">▾</RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content className={styles["selectContent"]} position="popper" sideOffset={4}>
            <RadixSelect.Viewport>
              {options.map((option) => (
                <RadixSelect.Item key={option.value} value={option.value} className={styles["selectItem"]}>
                  <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  );
}

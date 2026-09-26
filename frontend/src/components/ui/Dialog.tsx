import * as RadixDialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "./Button";
import styles from "./ui.module.css";

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}

function Frame({
  open,
  onOpenChange,
  title,
  description,
  children,
  contentClass,
}: DialogProps & { contentClass: string }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className={styles["overlay"]} />
        <RadixDialog.Content
          className={contentClass}
          {...(description === undefined ? { "aria-describedby": undefined } : {})}
        >
          <RadixDialog.Title className={styles["dialogTitle"]}>{title}</RadixDialog.Title>
          {description !== undefined && (
            <RadixDialog.Description className={styles["dialogDescription"]}>{description}</RadixDialog.Description>
          )}
          {children}
          <RadixDialog.Close asChild>
            <Button variant="ghost" size="sm">
              {t("ui.close")}
            </Button>
          </RadixDialog.Close>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

/** Diálogo modal accesible (foco atrapado, Esc, título obligatorio). */
export function Dialog(props: DialogProps): React.JSX.Element {
  return <Frame {...props} contentClass={styles["dialog"] ?? ""} />;
}

/** Hoja: inferior en móvil, lateral en escritorio (§10.1). Misma semántica que `Dialog`. */
export function Sheet(props: DialogProps): React.JSX.Element {
  return <Frame {...props} contentClass={styles["sheet"] ?? ""} />;
}

import * as RadixToast from "@radix-ui/react-toast";
import { useCallback, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cx } from "../../lib/cx";
import styles from "./ui.module.css";
import { ToastContext, type ToastApi, type ToastMessage } from "./toastContext";

interface ActiveToast extends ToastMessage {
  id: number;
}

let nextId = 0;

/** Proveedor de avisos (Radix Toast: región `aria-live`, cierre por teclado). */
export function ToastProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<ActiveToast[]>([]);

  const push = useCallback((message: ToastMessage) => {
    nextId += 1;
    const id = nextId;
    setToasts((current) => [...current, { ...message, id }]);
  }, []);

  const api = useMemo<ToastApi>(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={api}>
      <RadixToast.Provider duration={5000} label={t("ui.notifications")}>
        {children}
        {toasts.map((toast) => (
          <RadixToast.Root
            key={toast.id}
            className={cx(
              styles["toast"],
              toast.tone === "error" ? styles["toastError"] : toast.tone === "success" ? styles["toastSuccess"] : styles["toastInfo"],
            )}
            onOpenChange={(open) => {
              if (!open) setToasts((current) => current.filter((item) => item.id !== toast.id));
            }}
          >
            <RadixToast.Title className={styles["toastTitle"]}>{toast.title}</RadixToast.Title>
            {toast.description !== undefined && (
              <RadixToast.Description className={styles["toastDescription"]}>{toast.description}</RadixToast.Description>
            )}
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className={styles["toastViewport"]} />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

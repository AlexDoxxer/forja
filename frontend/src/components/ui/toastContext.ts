import { createContext, useContext } from "react";

export interface ToastMessage {
  title: string;
  description?: string;
  tone?: "info" | "success" | "error";
}

export interface ToastApi {
  push: (message: ToastMessage) => void;
}

export const ToastContext = createContext<ToastApi>({
  push: () => undefined,
});

/** Publica avisos efímeros; sin `ToastProvider` es un no-op (tests de pantallas aisladas). */
export function useToast(): ToastApi {
  return useContext(ToastContext);
}

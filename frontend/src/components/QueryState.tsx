import type { ReactNode } from "react";

export interface QueryStateProps {
  isLoading: boolean;
  isError: boolean;
  loadingLabel: string;
  errorLabel: string;
  children: ReactNode;
}

/** Estados de carga/error comunes a las pantallas que consultan la API (§10.2). */
export function QueryState({ isLoading, isError, loadingLabel, errorLabel, children }: QueryStateProps): React.JSX.Element {
  if (isLoading) {
    return <p role="status">{loadingLabel}</p>;
  }
  if (isError) {
    return <p role="alert">{errorLabel}</p>;
  }
  return <>{children}</>;
}

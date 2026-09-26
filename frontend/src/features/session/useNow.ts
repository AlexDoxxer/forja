import { useEffect, useState } from "react";

/** Hora actual que se refresca solo mientras `active`; la cuenta sale siempre de marcas de tiempo. */
export function useNow(active: boolean, intervalMs = 250): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return undefined;
    setNow(Date.now());
    const id = window.setInterval(() => {
      setNow(Date.now());
    }, intervalMs);
    // Al volver de segundo plano los temporizadores se congelan: se recalcula al instante.
    const onVisible = (): void => {
      setNow(Date.now());
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [active, intervalMs]);
  return now;
}

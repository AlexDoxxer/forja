import { useEffect, useState } from "react";

import { scheduler } from "./scheduler";
import { queueLength } from "./storage";

/** Número de escrituras pendientes en la cola offline; se refresca tras cada envío. */
export function usePendingSync(): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let alive = true;
    const refresh = (): void => {
      void queueLength().then((n) => {
        if (alive) setCount(n);
      });
    };
    refresh();
    const unsubscribe = scheduler.subscribe(refresh);
    const id = window.setInterval(refresh, 3000);
    return () => {
      alive = false;
      unsubscribe();
      window.clearInterval(id);
    };
  }, []);
  return count;
}

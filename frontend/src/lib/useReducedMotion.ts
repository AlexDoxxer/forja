import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** Refleja `prefers-reduced-motion` en vivo (MASTER_PROMPT §10.1, §10.4). */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(() =>
    typeof window === "undefined" ? false : window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const media = window.matchMedia(QUERY);
    const onChange = (event: MediaQueryListEvent): void => {
      setReduced(event.matches);
    };
    media.addEventListener("change", onChange);
    setReduced(media.matches);
    return () => {
      media.removeEventListener("change", onChange);
    };
  }, []);

  return reduced;
}

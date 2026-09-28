import { motion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

import { useReducedMotion } from "../lib/useReducedMotion";

export type RevealVariant = "scale" | "soft" | "pop" | "side" | "stat";

/** Misma curva que `--ease-out-expo` en `tokens.css`; Framer Motion no puede leer custom
 * properties de CSS, así que el valor vive aquí como constante literal (mismo patrón que
 * `RestRing.tsx`/`PrConfetti.tsx` para los colores brasa). */
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const;
const DURATION_S = 0.9;

/** Paso de retraso recomendado entre etapas de una misma cascada (`delay={REVEAL_STEP * n}`). */
export const REVEAL_STEP = 0.08;

const VARIANTS: Record<RevealVariant, Variants> = {
  // Entrada por defecto: aparece y sube 14 px (vocabulario del spec de referencia).
  soft: { hidden: { opacity: 0, y: 14 }, visible: { opacity: 1, y: 0 } },
  // Bloque «héroe» de la pantalla: aparece con un ligero acercamiento.
  scale: { hidden: { opacity: 0, scale: 0.96 }, visible: { opacity: 1, scale: 1 } },
  // Acciones/CTAs: un asentamiento más corto y con algo más de rebote visual.
  pop: { hidden: { opacity: 0, scale: 0.92, y: 8 }, visible: { opacity: 1, scale: 1, y: 0 } },
  // Listas/rieles: entra lateralmente en vez de desde abajo.
  side: { hidden: { opacity: 0, x: -16 }, visible: { opacity: 1, x: 0 } },
  // Cifras/estadísticas: desplazamiento más corto que "soft", pensado para bloques compactos.
  stat: { hidden: { opacity: 0, y: 10, scale: 0.98 }, visible: { opacity: 1, y: 0, scale: 1 } },
};

export interface RevealProps {
  children: ReactNode;
  /** Variante de la coreografía (MASTER_PROMPT «F5», vocabulario del spec de referencia). */
  variant?: RevealVariant;
  /** Retraso en segundos respecto al montaje de la pantalla, para escalonar la cascada. */
  delay?: number;
  className?: string;
}

/**
 * Coreografía de entrada reutilizable (F5): una única cascada por pantalla (cabecera → bloque
 * principal → bloques secundarios → acciones), nunca un efecto repetido en cada elemento suelto.
 * El estado de reposo es siempre visible — si Framer Motion no llegara a ejecutarse, `visible` es
 * el estado final declarado, nunca queda contenido oculto. Con `prefers-reduced-motion`, no se
 * anima nada: los hijos se muestran directamente (MASTER_PROMPT §10.1, §10.4).
 */
export function Reveal({ children, variant = "soft", delay = 0, className }: RevealProps): React.JSX.Element {
  const reducedMotion = useReducedMotion();

  if (reducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      variants={VARIANTS[variant]}
      initial="hidden"
      animate="visible"
      transition={{ duration: DURATION_S, delay, ease: EASE_OUT_EXPO }}
    >
      {children}
    </motion.div>
  );
}

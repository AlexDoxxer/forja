import { motion } from "framer-motion";
import { useState } from "react";

import styles from "./PrConfetti.module.css";

const PARTICLE_COUNT = 8;
/** Mismos tonos que `--color-accent`/`--color-accent-2` en `tokens.css` (sin tocar los tokens):
 * Framer Motion necesita valores de color literales para animarlos. */
const COLORS = ["#ff6a2b", "#ffb23f"] as const;
const EMBER_FALLBACK = "#ff6a2b";

interface Particle {
  id: number;
  x: number;
  y: number;
  color: string;
  size: number;
}

function makeParticles(): Particle[] {
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => {
    const angle = (i / PARTICLE_COUNT) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
    const distance = 22 + Math.random() * 20;
    return {
      id: i,
      x: Math.round(Math.cos(angle) * distance),
      y: Math.round(Math.sin(angle) * distance),
      color: COLORS[i % COLORS.length] ?? EMBER_FALLBACK,
      size: 4 + Math.round(Math.random() * 3),
    };
  });
}

/**
 * Confeti «discreto» de récord personal (MASTER_PROMPT §10.1): un puñado de motas color brasa
 * que estallan brevemente junto al récord y se apagan, menos de 1.5 s en total. Se importa con
 * `import()` dinámico desde donde se muestra un récord (chunk aparte: solo pesa cuando hay algo
 * que celebrar) y nunca se monta con `prefers-reduced-motion` (lo decide quien lo usa).
 */
export default function PrConfetti(): React.JSX.Element {
  const [particles] = useState(makeParticles);
  return (
    <span className={styles["burst"]} aria-hidden="true">
      {particles.map((p) => (
        <motion.span
          key={p.id}
          className={styles["particle"]}
          style={{ backgroundColor: p.color, width: p.size, height: p.size }}
          initial={{ opacity: 1, x: 0, y: 0, scale: 0.5 }}
          animate={{ opacity: 0, x: p.x, y: p.y, scale: 1 }}
          transition={{ duration: 0.85, ease: "easeOut" }}
        />
      ))}
    </span>
  );
}

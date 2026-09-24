import { useState } from "react";
import { useTranslation } from "react-i18next";

import { cx } from "../lib/cx";
import { useReducedMotion } from "../lib/useReducedMotion";
import styles from "./ExerciseMedia.module.css";
import type { components } from "../lib/api/schema";

export type ExerciseMediaValue = components["schemas"]["ExerciseMedia"];

/**
 * Atribución exigida por la licencia de Gym visual (MASTER_PROMPT §2.1, ADR 0004).
 * Ensanchadas a `string` a propósito: aunque el contrato declara estos campos como `const`,
 * el valor real llega por red y no debe darse por bueno solo porque el tipo lo sugiera.
 */
const REQUIRED_ATTRIBUTION_TEXT = "© Gym visual" as string;
const REQUIRED_ATTRIBUTION_URL = "https://gymvisual.com/" as string;

export interface ExerciseMediaProps {
  /** Medio del ejercicio devuelto por la API (`media` en `ExerciseSummary`/`ExerciseDetail`). */
  media: ExerciseMediaValue;
  /** Nombre del ejercicio; se usa como texto alternativo del medio (§10.4). */
  alt: string;
  /**
   * `"thumbnail"` (por defecto, listados): miniatura JPG estática. `"animated"` (detalle y
   * reproductor): reproduce el GIF directamente. En ambos casos, `prefers-reduced-motion`
   * fuerza la miniatura estática con un botón explícito para reproducir la animación
   * (§10.1, §10.4). La vista previa al pasar el cursor en tarjetas de listado (§10.1) se añade
   * en la Fase 2 con su equivalente por teclado/foco.
   */
  variant?: "thumbnail" | "animated";
  className?: string;
}

/**
 * Único componente autorizado para mostrar medios de ejercicio (© Gym visual). Nunca se debe
 * usar `<img>` fuera de aquí (regla ESLint `no-restricted-syntax` en `eslint.config.js`).
 *
 * Reglas no negociables (MASTER_PROMPT §2.1, §10.1, ADR 0004):
 * - Máximo 180 px CSS, con `width`/`height` explícitos, `loading="lazy"` y `decoding="async"`.
 * - Atribución «© Gym visual — https://gymvisual.com/» siempre visible debajo, con
 *   `rel="noopener"`. Si el medio recibido no trae la atribución exacta, el componente falla
 *   de forma ruidosa en vez de mostrar el medio sin ella.
 * - Respeta `prefers-reduced-motion`.
 */
export function ExerciseMedia({
  media,
  alt,
  variant = "thumbnail",
  className,
}: ExerciseMediaProps): React.JSX.Element {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const [userRequestedPlay, setUserRequestedPlay] = useState(false);

  const attributionText: string = media.attribution.text;
  const attributionUrl: string = media.attribution.url;
  if (attributionText !== REQUIRED_ATTRIBUTION_TEXT || attributionUrl !== REQUIRED_ATTRIBUTION_URL) {
    throw new Error(
      "ExerciseMedia: no se puede mostrar un medio de Gym visual sin su atribución exacta " +
        `(«${REQUIRED_ATTRIBUTION_TEXT} — ${REQUIRED_ATTRIBUTION_URL}»).`,
    );
  }

  const wantsAnimated = variant === "animated" || userRequestedPlay;
  const showGif = wantsAnimated && !prefersReducedMotion;
  const showPlayButton = prefersReducedMotion && !userRequestedPlay;

  return (
    <figure className={cx(styles["figure"], className)}>
      <div className={styles["plate"]}>
        <img
          className={styles["media"]}
          src={showGif ? media.gif_url : media.thumb_url}
          alt={alt}
          width={media.width}
          height={media.height}
          loading="lazy"
          decoding="async"
          style={{ maxWidth: "180px", maxHeight: "180px" }}
        />
        {showPlayButton && (
          <button
            type="button"
            className={styles["playButton"]}
            onClick={() => {
              setUserRequestedPlay(true);
            }}
          >
            {t("media.playAnimation")}
          </button>
        )}
      </div>
      <figcaption className={styles["attribution"]} aria-label={t("media.attributionLabel")}>
        <a href={attributionUrl} rel="noopener" target="_blank">
          {attributionText}
        </a>
      </figcaption>
    </figure>
  );
}

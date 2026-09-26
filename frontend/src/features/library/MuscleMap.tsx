import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui";
import { cx } from "../../lib/cx";
import type { MuscleCode } from "../shared/enums";
import styles from "./MuscleMap.module.css";

type Shape =
  | { kind: "ellipse"; cx: number; cy: number; rx: number; ry: number }
  | { kind: "rect"; x: number; y: number; w: number; h: number };

interface Region {
  muscle: MuscleCode;
  shapes: readonly Shape[];
}

const rect = (x: number, y: number, w: number, h: number): Shape => ({ kind: "rect", x, y, w, h });
const ellipse = (cx: number, cy: number, rx: number, ry: number): Shape => ({ kind: "ellipse", cx, cy, rx, ry });

/** Mapa muscular SVG propio (sin recursos externos): siluetas esquemáticas frontal y posterior. */
const FRONT: readonly Region[] = [
  { muscle: "neck", shapes: [rect(44, 20, 12, 9)] },
  { muscle: "shoulders", shapes: [ellipse(30, 41, 8, 7), ellipse(70, 41, 8, 7)] },
  { muscle: "chest", shapes: [ellipse(41, 52, 9, 7), ellipse(59, 52, 9, 7)] },
  { muscle: "biceps", shapes: [rect(19, 50, 8, 20), rect(73, 50, 8, 20)] },
  { muscle: "forearms", shapes: [rect(15, 72, 8, 22), rect(77, 72, 8, 22)] },
  { muscle: "abs", shapes: [rect(43, 62, 14, 26)] },
  { muscle: "obliques", shapes: [rect(35, 62, 7, 24), rect(58, 62, 7, 24)] },
  { muscle: "hip_flexors", shapes: [rect(38, 90, 24, 8)] },
  { muscle: "quads", shapes: [rect(34, 100, 14, 40), rect(52, 100, 14, 40)] },
  { muscle: "adductors", shapes: [rect(46, 100, 8, 30)] },
  { muscle: "lower_leg", shapes: [rect(35, 146, 11, 38), rect(54, 146, 11, 38)] },
];

const BACK: readonly Region[] = [
  { muscle: "traps", shapes: [ellipse(50, 34, 14, 8)] },
  { muscle: "rear_delts", shapes: [ellipse(30, 41, 8, 7), ellipse(70, 41, 8, 7)] },
  { muscle: "upper_back", shapes: [rect(38, 46, 24, 14)] },
  { muscle: "lats", shapes: [rect(32, 60, 10, 22), rect(58, 60, 10, 22)] },
  { muscle: "lower_back", shapes: [rect(42, 82, 16, 12)] },
  { muscle: "triceps", shapes: [rect(19, 50, 8, 20), rect(73, 50, 8, 20)] },
  { muscle: "forearms", shapes: [rect(15, 72, 8, 22), rect(77, 72, 8, 22)] },
  { muscle: "glutes", shapes: [ellipse(42, 104, 9, 8), ellipse(58, 104, 9, 8)] },
  { muscle: "hamstrings", shapes: [rect(34, 116, 14, 30), rect(52, 116, 14, 30)] },
  { muscle: "calves", shapes: [rect(35, 150, 11, 34), rect(54, 150, 11, 34)] },
];

export interface MuscleMapProps {
  /** Músculos resaltados como principal (o filtro activo en la biblioteca). */
  selected: readonly MuscleCode[];
  /** Músculos secundarios (detalle de ejercicio). */
  secondary?: readonly MuscleCode[];
  /** Si se pasa, las regiones son botones que conmutan el músculo (filtro). */
  onToggle?: (muscle: MuscleCode) => void;
}

function Silhouette({ regions, view, selected, secondary, onToggle }: MuscleMapProps & { regions: readonly Region[]; view: "front" | "back" }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <svg
      viewBox="0 0 100 200"
      className={styles["svg"]}
      role="group"
      aria-label={t(view === "front" ? "library.map.front" : "library.map.back")}
    >
      <ellipse cx="50" cy="12" rx="9" ry="10" className={styles["body"]} />
      <rect x="40" y="26" width="20" height="70" rx="8" className={styles["body"]} />
      <rect x="32" y="96" width="36" height="92" rx="8" className={styles["body"]} />
      {regions.map((region) => {
        const isSelected = selected.includes(region.muscle);
        const isSecondary = !isSelected && (secondary?.includes(region.muscle) ?? false);
        const name = t(`enums.muscle.${region.muscle}`);
        const className = cx(styles["region"], isSelected && styles["selected"], isSecondary && styles["secondary"]);
        const shapes = region.shapes.map((shape, index) =>
          shape.kind === "ellipse" ? (
            <ellipse key={index} cx={shape.cx} cy={shape.cy} rx={shape.rx} ry={shape.ry} />
          ) : (
            <rect key={index} x={shape.x} y={shape.y} width={shape.w} height={shape.h} rx={3} />
          ),
        );
        if (onToggle === undefined) {
          return (
            <g key={region.muscle} className={className} role="img" aria-label={`${name}${isSelected ? ` (${t("library.map.target")})` : isSecondary ? ` (${t("library.map.secondary")})` : ""}`}>
              {shapes}
            </g>
          );
        }
        return (
          <g
            key={region.muscle}
            className={cx(className, styles["interactive"])}
            role="button"
            tabIndex={0}
            aria-pressed={isSelected}
            aria-label={name}
            onClick={() => {
              onToggle(region.muscle);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onToggle(region.muscle);
              }
            }}
          >
            {shapes}
          </g>
        );
      })}
    </svg>
  );
}

/** Mapa muscular frontal/posterior. Con `onToggle` funciona como filtro clicable y accesible por teclado. */
export function MuscleMap(props: MuscleMapProps): React.JSX.Element {
  const { t } = useTranslation();
  const [view, setView] = useState<"front" | "back">("front");
  return (
    <Tabs value={view} onValueChange={(value) => { setView(value === "back" ? "back" : "front"); }}>
      <TabsList aria-label={t("library.map.title")}>
        <TabsTrigger value="front">{t("library.map.front")}</TabsTrigger>
        <TabsTrigger value="back">{t("library.map.back")}</TabsTrigger>
      </TabsList>
      <TabsContent value="front">
        <Silhouette {...props} regions={FRONT} view="front" />
      </TabsContent>
      <TabsContent value="back">
        <Silhouette {...props} regions={BACK} view="back" />
      </TabsContent>
    </Tabs>
  );
}

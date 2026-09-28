import { lazy, Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ExerciseMedia } from "../../components/ExerciseMedia";
import { Reveal, REVEAL_STEP } from "../../components/Reveal";
import { Button, Sheet, Tabs, TabsContent, TabsList, TabsTrigger, useToast } from "../../components/ui";
import type { components } from "../../lib/api/schema";
import { formatPrescription } from "../shared/format";
import styles from "./Generator.module.css";
import {
  useRegenerateDay,
  useSwapPreviewExercise,
  type GeneratorPreview,
  type SlotAddress,
} from "./useGenerator";

const VolumeChart = lazy(() => import("./VolumeChart"));

type ExerciseSummary = components["schemas"]["ExerciseSummary"];

interface SwapTarget {
  address: SlotAddress;
  exerciseId: string;
  alternatives: readonly string[];
}

export interface PreviewPanelProps {
  preview: GeneratorPreview;
  onChange: (preview: GeneratorPreview) => void;
}

/**
 * Vista previa del programa (§10.2.3): semana tipo con GIFs, series×reps, descansos y minutos,
 * volumen por grupo, `rationale_es` y `warnings`; regenerar un día y cambiar ejercicio (hoja con
 * alternativas). Toda decisión de contenido la toma el motor en el backend.
 */
export function PreviewPanel({ preview, onChange }: PreviewPanelProps): React.JSX.Element {
  const { t } = useTranslation();
  const { push } = useToast();
  const regenerateDay = useRegenerateDay();
  const swap = useSwapPreviewExercise();
  const [swapTarget, setSwapTarget] = useState<SwapTarget | null>(null);

  const exercisesById = useMemo(() => {
    const map = new Map<string, ExerciseSummary>();
    for (const exercise of preview.exercises) map.set(exercise.id, exercise);
    return map;
  }, [preview.exercises]);

  const { plan } = preview;
  const week = plan.weeks[0];
  if (week === undefined) return <p role="alert">{t("generator.preview.empty")}</p>;
  const firstDay = week.days[0];

  const doSwap = (target: SwapTarget, replacementId: string | null): void => {
    swap.mutate(
      { plan, address: target.address, excludeIds: [target.exerciseId], replacementId },
      {
        onSuccess: (next) => {
          onChange(next);
          setSwapTarget(null);
        },
        onError: () => {
          push({ title: t("generator.preview.swapError"), tone: "error" });
        },
      },
    );
  };

  return (
    <div className={styles["preview"]}>
      <Reveal variant="soft">
        <section aria-labelledby="rationale-title">
          <h2 id="rationale-title">{t("generator.preview.rationale")}</h2>
          <ul>
            {plan.rationale_es.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      </Reveal>

      {plan.warnings.length > 0 && (
        <Reveal variant="soft" delay={REVEAL_STEP}>
          <section aria-labelledby="warnings-title" className={styles["warnings"]}>
            <h2 id="warnings-title">{t("generator.preview.warnings")}</h2>
            <ul>
              {plan.warnings.map((warning, index) => (
                <li key={`${warning.code}-${String(index)}`}>
                  <strong>{t("generator.preview.warningLabel")}: </strong>
                  {warning.message_es}
                </li>
              ))}
            </ul>
          </section>
        </Reveal>
      )}

      <Reveal variant="scale" delay={REVEAL_STEP * 2}>
      <section aria-labelledby="week-title">
        <h2 id="week-title">{t("generator.preview.typicalWeek")}</h2>
        {firstDay !== undefined && (
          <Tabs defaultValue={String(firstDay.index)}>
            <TabsList aria-label={t("generator.preview.days")}>
              {week.days.map((day) => (
                <TabsTrigger key={day.index} value={String(day.index)}>
                  {day.name_es}
                </TabsTrigger>
              ))}
            </TabsList>
            {week.days.map((day) => (
              <TabsContent key={day.index} value={String(day.index)}>
                <p className={styles["dayMeta"]}>
                  {day.focus_es} · {t("generator.preview.minutes", { count: day.estimated_minutes })}
                  {day.is_recovery && ` · ${t("generator.preview.recovery")}`}
                </p>
                <Button
                  size="sm"
                  disabled={regenerateDay.isPending}
                  onClick={() => {
                    regenerateDay.mutate(
                      { plan, dayIndex: day.index },
                      {
                        onSuccess: onChange,
                        onError: () => {
                          push({ title: t("generator.preview.regenerateError"), tone: "error" });
                        },
                      },
                    );
                  }}
                >
                  {t("generator.preview.regenerateDay")}
                </Button>
                {day.blocks.map((block) => (
                  <div key={block.order} className={styles["block"]}>
                    <h3>
                      {t(`enums.blockKind.${block.kind}`)}
                      {block.rounds > 1 && ` · ${t("generator.preview.rounds", { count: block.rounds })}`}
                    </h3>
                    <ul className={styles["exercises"]}>
                      {block.exercises.map((item) => {
                        const exercise = exercisesById.get(item.exercise_id);
                        const address: SlotAddress = {
                          week_index: week.index,
                          day_index: day.index,
                          block_order: block.order,
                          exercise_order: item.order,
                        };
                        return (
                          <li key={`${String(block.order)}-${String(item.order)}`} className={styles["exercise"]}>
                            {exercise !== undefined && (
                              <ExerciseMedia media={exercise.media} alt={exercise.name_es} />
                            )}
                            <div>
                              <strong className={styles["exerciseName"]}>{exercise?.name_es ?? item.exercise_id}</strong>
                              <p className={styles["prescription"]}>
                                {formatPrescription(item, t("generator.preview.perSide"))} ·{" "}
                                {t("generator.preview.rest", { seconds: item.rest_s })}
                                {item.target_rir !== null && ` · RIR ${String(item.target_rir)}`}
                              </p>
                              {item.notes_es !== null && <p className={styles["notes"]}>{item.notes_es}</p>}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setSwapTarget({ address, exerciseId: item.exercise_id, alternatives: item.alternatives });
                                }}
                              >
                                {t("generator.preview.swap")}
                              </Button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </TabsContent>
            ))}
          </Tabs>
        )}
      </section>
      </Reveal>

      <Reveal variant="stat" delay={REVEAL_STEP * 3}>
        <section aria-labelledby="volume-title">
          <h2 id="volume-title">{t("generator.preview.volume")}</h2>
          <Suspense fallback={<p role="status">{t("generator.preview.loadingChart")}</p>}>
            <VolumeChart volume={plan.weekly_volume} />
          </Suspense>
          <table className={styles["volumeTable"]}>
            <caption>{t("generator.preview.volumeCaption")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("generator.preview.group")}</th>
                <th scope="col">{t("generator.preview.planned")}</th>
                <th scope="col">{t("generator.preview.target")}</th>
              </tr>
            </thead>
            <tbody>
              {plan.weekly_volume.map((row) => (
                <tr key={row.group}>
                  <th scope="row">{t(`enums.group.${row.group}`)}</th>
                  <td>{row.planned_sets}</td>
                  <td>
                    {row.target_min}–{row.target_max}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </Reveal>

      <Sheet
        open={swapTarget !== null}
        onOpenChange={(open) => {
          if (!open) setSwapTarget(null);
        }}
        title={t("generator.preview.swapTitle")}
        description={t("generator.preview.swapDescription")}
      >
        {swapTarget !== null && (
          <>
            <ul className={styles["alternatives"]}>
              {swapTarget.alternatives.map((id) => {
                const alternative = exercisesById.get(id);
                if (alternative === undefined) return null;
                return (
                  <li key={id}>
                    <ExerciseMedia media={alternative.media} alt={alternative.name_es} />
                    <Button
                      size="sm"
                      disabled={swap.isPending}
                      onClick={() => {
                        doSwap(swapTarget, id);
                      }}
                    >
                      {t("generator.preview.use", { name: alternative.name_es })}
                    </Button>
                  </li>
                );
              })}
            </ul>
            <Button
              variant="secondary"
              disabled={swap.isPending}
              onClick={() => {
                doSwap(swapTarget, null);
              }}
            >
              {t("generator.preview.swapAuto")}
            </Button>
          </>
        )}
      </Sheet>
    </div>
  );
}

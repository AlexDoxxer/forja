import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ExerciseMedia } from "../../components/ExerciseMedia";
import { QueryState } from "../../components/QueryState";
import { Button, Select } from "../../components/ui";
import { LANGS, type InstructionLang } from "../shared/enums";
import styles from "./Detail.module.css";
import { MuscleMap } from "./MuscleMap";
import {
  useExerciseAlternatives,
  useExerciseDetail,
  useExerciseStats,
  useToggleFavorite,
} from "./useCatalog";

export interface ExerciseDetailScreenProps {
  /** Permite usar la pantalla sin router (tests); por defecto se lee de la ruta. */
  exerciseId?: string;
}

function isLang(value: string): value is InstructionLang {
  return LANGS.some((lang) => lang === value);
}


/**
 * Detalle de ejercicio (§10.2.7): GIF con atribución, músculos (objetivo y secundarios resaltados
 * en el mapa), pasos numerados en uno de los 10 idiomas, conmutador de ángulo/demostrador
 * (variantes), alternativas, historial personal y favorito.
 */
export function ExerciseDetailScreen({ exerciseId }: ExerciseDetailScreenProps): React.JSX.Element {
  const params: { exerciseId?: string } = useParams({ strict: false });
  return <DetailBody id={exerciseId ?? params.exerciseId ?? ""} />;
}

function DetailBody({ id }: { id: string }): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const [lang, setLang] = useState<InstructionLang>(i18n.language === "en" ? "en" : "es");
  const detail = useExerciseDetail(id, lang);
  const alternatives = useExerciseAlternatives(id);
  const stats = useExerciseStats(id);
  const favorite = useToggleFavorite(id);
  const exercise = detail.data;

  return (
    <section aria-labelledby="detail-title" className={styles["root"]}>
      <Link to="/biblioteca" className={styles["back"]}>
        {t("library.detail.back")}
      </Link>
      <QueryState
        isLoading={detail.isLoading}
        isError={detail.isError}
        loadingLabel={t("library.loading")}
        errorLabel={t("library.detail.error")}
      >
        {exercise && (
          <>
            <h1 id="detail-title" className={styles["title"]}>
              {exercise.name_es}
              {exercise.variant_label_es !== null && ` (${exercise.variant_label_es})`}
            </h1>
            <p className={styles["subtitle"]}>{exercise.name_en}</p>

            <div className={styles["columns"]}>
              <div>
                <ExerciseMedia media={exercise.media} alt={exercise.name_es} variant="animated" />
                <Button
                  aria-pressed={exercise.is_favorite}
                  disabled={favorite.isPending}
                  onClick={() => {
                    favorite.mutate(!exercise.is_favorite);
                  }}
                >
                  {exercise.is_favorite ? t("library.detail.unfavorite") : t("library.detail.favorite")}
                </Button>

                {exercise.variants.length > 0 && (
                  <nav aria-label={t("library.detail.variants")} className={styles["variants"]}>
                    <h2>{t("library.detail.variants")}</h2>
                    <ul>
                      {exercise.variants.map((variant) => (
                        <li key={variant.id}>
                          <Link to="/biblioteca/$exerciseId" params={{ exerciseId: variant.id }}>
                            {variant.label_es}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </nav>
                )}
              </div>

              <div>
                <h2>{t("library.detail.muscles")}</h2>
                <MuscleMap
                  selected={[exercise.target_muscle]}
                  secondary={exercise.secondary_muscles}
                />
                <p>
                  <strong>{t("library.detail.target")}:</strong> {t(`enums.muscle.${exercise.target_muscle}`)}
                </p>
                {exercise.secondary_muscles.length > 0 && (
                  <p>
                    <strong>{t("library.detail.secondary")}:</strong>{" "}
                    {exercise.secondary_muscles.map((muscle) => t(`enums.muscle.${muscle}`)).join(", ")}
                  </p>
                )}
                <p>
                  <strong>{t("library.equipment")}:</strong> {t(`enums.equipment.${exercise.equipment_code}`)} ·{" "}
                  <strong>{t("library.pattern")}:</strong> {t(`enums.pattern.${exercise.movement_pattern}`)} ·{" "}
                  <strong>{t("library.difficulty")}:</strong> {t(`enums.difficulty.${String(exercise.difficulty)}`)}
                </p>
              </div>
            </div>

            <div className={styles["instructions"]}>
              <Select
                label={t("library.detail.language")}
                value={lang}
                onValueChange={(value) => {
                  if (isLang(value)) setLang(value);
                }}
                options={exercise.available_langs.map((code) => ({ value: code, label: t(`enums.lang.${code}`) }))}
              />
              <h2>{t("library.detail.instructions")}</h2>
              <ol lang={exercise.instructions.lang}>
                {exercise.instructions.steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            </div>

            <h2>{t("library.detail.history")}</h2>
            {stats.data && stats.data.points.length > 0 ? (
              <p>
                {t("library.detail.bestE1rm", { kg: stats.data.best_e1rm_kg ?? 0 })} ·{" "}
                {t("library.detail.sessionsLogged", { count: stats.data.points.length })}
              </p>
            ) : (
              <p className={styles["subtitle"]}>{t("library.detail.noHistory")}</p>
            )}

            <h2>{t("library.detail.alternatives")}</h2>
            {alternatives.data && alternatives.data.items.length > 0 ? (
              <ul className={styles["alternatives"]}>
                {alternatives.data.items.map((alternative) => (
                  <li key={alternative.exercise.id}>
                    <ExerciseMedia media={alternative.exercise.media} alt={alternative.exercise.name_es} />
                    <Link to="/biblioteca/$exerciseId" params={{ exerciseId: alternative.exercise.id }}>
                      {alternative.exercise.name_es}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles["subtitle"]}>{t("library.detail.noAlternatives")}</p>
            )}

            <Link to="/rutinas" className={styles["addLink"]}>
              {t("library.detail.addToRoutine")}
            </Link>
          </>
        )}
      </QueryState>
    </section>
  );
}

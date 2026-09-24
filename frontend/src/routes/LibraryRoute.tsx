import { useTranslation } from "react-i18next";

import { ExerciseMedia } from "../components/ExerciseMedia";
import { QueryState } from "../components/QueryState";
import { useExerciseList } from "../features/library/useExerciseList";

/**
 * Pantalla «Biblioteca» (MASTER_PROMPT §10.2.7). Primera página desde `GET /exercises`; la
 * cuadrícula virtualizada, la búsqueda sin acentos y el mapa muscular llegan en la Fase 2
 * (F2-FE-08).
 */
export function LibraryRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const exercises = useExerciseList();

  return (
    <section aria-labelledby="library-title">
      <h1 id="library-title">{t("library.title")}</h1>
      <QueryState
        isLoading={exercises.isLoading}
        isError={exercises.isError}
        loadingLabel={t("library.loading")}
        errorLabel={t("library.error")}
      >
        {exercises.data && (
          <>
            <p>{t("library.resultCount", { count: exercises.data.items.length })}</p>
            <ul>
              {exercises.data.items.map((exercise) => (
                <li key={exercise.id}>
                  <ExerciseMedia media={exercise.media} alt={exercise.name_es} />
                  <p>{exercise.name_es}</p>
                </li>
              ))}
            </ul>
          </>
        )}
      </QueryState>
    </section>
  );
}

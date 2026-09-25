import { useTranslation } from "react-i18next";

import { QueryState } from "../components/QueryState";
import { useVolumeStats } from "../features/progress/useVolumeStats";

/** Pantalla «Progreso» (MASTER_PROMPT §10.2.8). Volumen semanal desde `GET /stats/volume`. */
export function ProgressRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const volume = useVolumeStats();

  return (
    <section aria-labelledby="progress-title">
      <h1 id="progress-title">{t("progress.title")}</h1>
      <QueryState
        isLoading={volume.isLoading}
        isError={volume.isError}
        loadingLabel={t("progress.loading")}
        errorLabel={t("progress.error")}
      >
        {volume.data && (
          <ul>
            {volume.data.weeks.map((week) => (
              <li key={week.week_start}>
                <strong>{week.week_start}</strong>
                <ul>
                  {week.groups.map((group) => (
                    <li key={group.group}>
                      {group.group}: {group.effective_sets} · {group.volume_kg} kg
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </section>
  );
}

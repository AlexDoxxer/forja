import { useTranslation } from "react-i18next";

import { QueryState } from "../components/QueryState";
import { useTodayOverview } from "../features/today/useTodayOverview";

/** Pantalla «Hoy» (MASTER_PROMPT §10.2.2). Resumen semanal desde `GET /stats/overview`. */
export function TodayRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const overview = useTodayOverview();

  return (
    <section aria-labelledby="today-title">
      <h1 id="today-title">{t("today.title")}</h1>
      <QueryState
        isLoading={overview.isLoading}
        isError={overview.isError}
        loadingLabel={t("today.loading")}
        errorLabel={t("today.error")}
      >
        {overview.data && (
          <dl>
            <div>
              <dt>{t("today.sessionsCompleted")}</dt>
              <dd>{overview.data.sessions_completed}</dd>
            </div>
            <div>
              <dt>{t("today.sessionsPlanned")}</dt>
              <dd>{overview.data.sessions_planned}</dd>
            </div>
            <div>
              <dt>{t("today.volume")}</dt>
              <dd>{overview.data.volume_kg} kg</dd>
            </div>
            <div>
              <dt>{t("today.streak")}</dt>
              <dd>{overview.data.streak_weeks}</dd>
            </div>
          </dl>
        )}
      </QueryState>
    </section>
  );
}

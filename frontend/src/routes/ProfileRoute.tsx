import { useTranslation } from "react-i18next";

import { QueryState } from "../components/QueryState";
import { useAboutInfo } from "../features/profile/useAboutInfo";

/**
 * Pantalla «Perfil» (MASTER_PROMPT §10.2.10). Muestra los créditos y licencias desde
 * `GET /about`: MIT del dataset, aviso de medios de Gym visual y commit SHA ingerido (§2.1).
 * El resto de ajustes llega en la Fase 2 (F2-FE-12).
 */
export function ProfileRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const about = useAboutInfo();

  return (
    <section aria-labelledby="profile-title">
      <h1 id="profile-title">{t("profile.title")}</h1>
      <QueryState
        isLoading={about.isLoading}
        isError={about.isError}
        loadingLabel={t("profile.loading")}
        errorLabel={t("profile.error")}
      >
        {about.data && (
          <section aria-label={t("profile.credits")}>
            <h2>{t("profile.credits")}</h2>
            <dl>
              <div>
                <dt>{t("profile.datasetCommit")}</dt>
                <dd>
                  <code>{about.data.dataset.commit}</code>
                </dd>
              </div>
              <div>
                <dt>{t("profile.exerciseCount")}</dt>
                <dd>{about.data.dataset.exercise_count}</dd>
              </div>
            </dl>
            <p>
              <a href={about.data.media_attribution.url} rel="noopener" target="_blank">
                {about.data.media_attribution.text}
              </a>
            </p>
            <details>
              <summary>MIT — hasaneyldrm/exercises-dataset</summary>
              <pre>{about.data.licenses.dataset_mit}</pre>
            </details>
            <details>
              <summary>{t("profile.credits")} — Gym visual</summary>
              <pre>{about.data.licenses.media_notice}</pre>
            </details>
            <p role="note">
              <strong>{t("profile.healthDisclaimer")}: </strong>
              {about.data.health_disclaimer_es}
            </p>
          </section>
        )}
      </QueryState>
    </section>
  );
}

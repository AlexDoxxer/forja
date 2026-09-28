import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { QueryState } from "../components/QueryState";
import { IconDumbbell, IconInbox } from "../components/icons";
import { useProgramList } from "../features/programs/useProgramList";
import { cx } from "../lib/cx";
import shared from "../features/shared/ui.module.css";

/** Pantalla «Rutinas» (MASTER_PROMPT §10.2.7). Lista desde `GET /programs`. */
export function ProgramsRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const programs = useProgramList();

  const getApiBaseUrl = (): string => {
    return typeof window === "undefined" ? "/api/v1" : `${window.location.origin}/api/v1`;
  };

  return (
    <section aria-labelledby="programs-title" className={shared["page"]}>
      <h1 id="programs-title">{t("programs.title")}</h1>
      <p>
        <Link to="/rutinas/nueva" className={cx(shared["btn"], shared["primary"])}>
          {t("programs.generate")}
        </Link>
      </p>
      <QueryState
        isLoading={programs.isLoading}
        isError={programs.isError}
        loadingLabel={t("programs.loading")}
        errorLabel={t("programs.error")}
      >
        {programs.data?.items.length === 0 && (
          <div className={shared["empty"]}>
            <span className={shared["emptyIcon"]}>
              <IconInbox />
            </span>
            <p>{t("programs.empty")}</p>
          </div>
        )}
        {programs.data && programs.data.items.length > 0 && (
          <ul className={shared["list"]}>
            {programs.data.items.map((program) => (
              <li key={program.id} className={shared["card"]}>
                <div className={shared["cardHeader"]}>
                  <span className={shared["cardIcon"]}>
                    <IconDumbbell />
                  </span>
                  <div>
                    <strong>{program.name}</strong> {program.is_active && <span>({t("programs.active")})</span>}
                  </div>
                </div>
                <div className={shared["muted"]}>{t("programs.daysPerWeek", { count: program.days_per_week })}</div>
                <div className={shared["row"]}>
                  <Link
                    to="/rutinas/$programId/editar"
                    params={{ programId: program.id }}
                    className={shared["btn"]}
                  >
                    {t("programs.edit", { name: program.name })}
                  </Link>
                  <a href={`${getApiBaseUrl()}/programs/${program.id}/export.pdf`} download className={shared["btn"]}>
                    {t("programs.exportPdf")}
                  </a>
                  <a
                    href={`${getApiBaseUrl()}/programs/${program.id}/calendar.ics`}
                    download
                    className={shared["btn"]}
                  >
                    {t("programs.exportCalendar")}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </section>
  );
}

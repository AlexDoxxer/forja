import { useTranslation } from "react-i18next";

import { QueryState } from "../components/QueryState";
import { useProgramList } from "../features/programs/useProgramList";

/** Pantalla «Rutinas» (MASTER_PROMPT §10.2.7). Lista desde `GET /programs`. */
export function ProgramsRoute(): React.JSX.Element {
  const { t } = useTranslation();
  const programs = useProgramList();

  return (
    <section aria-labelledby="programs-title">
      <h1 id="programs-title">{t("programs.title")}</h1>
      <QueryState
        isLoading={programs.isLoading}
        isError={programs.isError}
        loadingLabel={t("programs.loading")}
        errorLabel={t("programs.error")}
      >
        {programs.data?.items.length === 0 && <p>{t("programs.empty")}</p>}
        {programs.data && programs.data.items.length > 0 && (
          <ul>
            {programs.data.items.map((program) => (
              <li key={program.id}>
                <strong>{program.name}</strong>{" "}
                {program.is_active && <span>({t("programs.active")})</span>}
                <div>{t("programs.daysPerWeek", { count: program.days_per_week })}</div>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </section>
  );
}

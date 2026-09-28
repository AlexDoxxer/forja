import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import { IconCalendar, IconChartBar, IconInbox, IconScale } from "../../components/icons";
import { Reveal, REVEAL_STEP } from "../../components/Reveal";
import { api, unwrapApi } from "../../lib/api/client";
import { cx } from "../../lib/cx";
import { useNextSession } from "../session/queries";
import { usePendingSync } from "../session/usePendingSync";
import { startSession } from "../session/usePlayer";
import { loadActiveState } from "../session/storage";
import "../session/strings";
import { formatNumber, parseDecimal } from "../shared/format";
import shared from "../shared/ui.module.css";
import { useProfileSummary } from "./useProfileSummary";
import { useTodayOverview } from "./useTodayOverview";

function BodyWeightCard(): React.JSX.Element {
  const { t } = useTranslation();
  const overview = useTodayOverview();
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const mutation = useMutation({
    mutationFn: async (weight: number) =>
      unwrapApi(
        await api.POST("/body-metrics", {
          body: { date: new Date().toISOString().slice(0, 10), weight_kg: weight },
        }),
      ),
    onSuccess: async () => {
      setText("");
      await queryClient.invalidateQueries({ queryKey: ["stats"] });
      await queryClient.invalidateQueries({ queryKey: ["body-metrics"] });
    },
  });
  const weight = parseDecimal(text);
  const latest = overview.data?.body_weight.latest ?? null;
  const average = overview.data?.body_weight.moving_average_7d_kg ?? null;

  return (
    <section className={shared["card"]} aria-labelledby="bw-title">
      <div className={shared["cardHeader"]}>
        <span className={shared["cardIcon"]}>
          <IconScale />
        </span>
        <h2 id="bw-title">{t("todayB.bodyWeight")}</h2>
      </div>
      {latest !== null && <p>{t("todayB.bodyWeightLatest", { weight: formatNumber(latest.weight_kg) })}</p>}
      {average !== null && (
        <p className={shared["muted"]}>{t("todayB.bodyWeightAverage", { weight: formatNumber(average) })}</p>
      )}
      <form
        className={shared["row"]}
        onSubmit={(event) => {
          event.preventDefault();
          if (weight !== null && weight > 0) mutation.mutate(weight);
        }}
      >
        <label className={shared["field"]}>
          {t("todayB.bodyWeightInput")}
          <input
            inputMode="decimal"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          className={cx(shared["btn"], shared["primary"])}
          disabled={weight === null || weight <= 0 || mutation.isPending}
        >
          {t("todayB.bodyWeightSave")}
        </button>
      </form>
      {mutation.isSuccess && <p role="status">{t("todayB.bodyWeightSaved")}</p>}
      {mutation.isError && <p role="alert">{t("todayB.bodyWeightError")}</p>}
    </section>
  );
}

function NextSessionCard(): React.JSX.Element {
  const { t } = useTranslation();
  const next = useNextSession();
  const navigate = useNavigate();
  const active = useQuery({ queryKey: ["active-session"], queryFn: async () => (await loadActiveState()) ?? null });
  const [starting, setStarting] = useState(false);
  const [failed, setFailed] = useState(false);

  const begin = async (): Promise<void> => {
    if (next.data === undefined) return;
    setStarting(true);
    setFailed(false);
    try {
      await startSession(next.data);
      await navigate({ to: "/sesion" });
    } catch {
      setFailed(true);
      setStarting(false);
    }
  };

  return (
    <section className={shared["card"]} aria-labelledby="next-title">
      <div className={shared["cardHeader"]}>
        <span className={shared["cardIcon"]}>
          <IconCalendar />
        </span>
        <h2 id="next-title">{t("today.title")}</h2>
      </div>
      <QueryState
        isLoading={next.isLoading}
        isError={next.isError}
        loadingLabel={t("today.loading")}
        errorLabel={t("today.error")}
      >
        {active.data != null && (
          <p>
            <Link to="/sesion" className={cx(shared["btn"], shared["primary"])}>
              {t("todayB.resume")}
            </Link>
          </p>
        )}
        {next.data?.status === "scheduled" && next.data.day !== null && (
          <div className={shared["stack"]}>
            <p>
              <strong>{t("todayB.scheduledFor", { name: next.data.day.name })}</strong>
            </p>
            <p className={shared["muted"]}>{t("todayB.minutes", { count: next.data.day.estimated_minutes })}</p>
            <button
              type="button"
              className={cx(shared["btn"], shared["primary"])}
              disabled={starting || active.data != null}
              onClick={() => void begin()}
            >
              {starting ? t("todayB.starting") : t("todayB.start")}
            </button>
            {failed && <p role="alert">{t("session.startingError")}</p>}
          </div>
        )}
        {next.data?.status === "rest_day" && <p>{t("todayB.restDay")}</p>}
        {next.data?.status === "program_completed" && <p>{t("todayB.programCompleted")}</p>}
        {next.data?.status === "no_active_program" && (
          <div className={shared["empty"]}>
            <span className={shared["emptyIcon"]}>
              <IconInbox />
            </span>
            <p>{t("todayB.noProgram")}</p>
            <Link to="/rutinas" className={cx(shared["btn"], shared["primary"])}>
              {t("todayB.createProgram")}
            </Link>
          </div>
        )}
      </QueryState>
    </section>
  );
}

/** Pantalla «Hoy» (MASTER_PROMPT §10.2.2). */
export function TodayScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const overview = useTodayOverview();
  const profile = useProfileSummary();
  const pending = usePendingSync();

  return (
    <section aria-labelledby="today-title" className={shared["page"]}>
      <Reveal variant="soft">
        <h1 id="today-title">{t("today.title")}</h1>
        {pending > 0 && (
          <p className={shared["notice"]} role="status">
            {t("todayB.pendingSync", { count: pending })}
          </p>
        )}
      </Reveal>
      <div className={shared["grid"]}>
        <Reveal variant="scale" delay={REVEAL_STEP}>
          <NextSessionCard />
        </Reveal>
        <Reveal variant="soft" delay={REVEAL_STEP * 2}>
          <section className={shared["card"]} aria-labelledby="week-title">
            <div className={shared["cardHeader"]}>
              <span className={shared["cardIcon"]}>
                <IconChartBar />
              </span>
              <h2 id="week-title">{t("todayB.weekSummary")}</h2>
            </div>
            <QueryState
              isLoading={overview.isLoading}
              isError={overview.isError}
              loadingLabel={t("today.loading")}
              errorLabel={t("today.error")}
            >
              {overview.data && (
                <>
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
                      <dd>{formatNumber(overview.data.volume_kg, 0)} kg</dd>
                    </div>
                    <div>
                      <dt>{t("today.streak")}</dt>
                      <dd>{overview.data.streak_weeks}</dd>
                    </div>
                  </dl>
                  <h3>{t("todayB.lastRecord")}</h3>
                  <p>
                    {overview.data.last_record === null
                      ? t("todayB.noRecord")
                      : t("todayB.recordValue", {
                          name: overview.data.last_record.exercise_name_es,
                          value: formatNumber(overview.data.last_record.value),
                        })}
                  </p>
                </>
              )}
            </QueryState>
          </section>
        </Reveal>
        <Reveal variant="soft" delay={REVEAL_STEP * 2}>
          <BodyWeightCard />
        </Reveal>
      </div>
      {profile.data?.diet_available === true && (
        <Reveal variant="pop" delay={REVEAL_STEP * 3}>
          <p>
            <Link to="/nutricion" className={shared["btn"]}>
              {t("todayB.nutrition")}
            </Link>
          </p>
        </Reveal>
      )}
    </section>
  );
}

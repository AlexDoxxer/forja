import { useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import type { components } from "../../lib/api/schema";
import { formatDate } from "../shared/format";
import shared from "../shared/ui.module.css";
import { useProfileSummary } from "../today/useProfileSummary";
import {
  useAdminSettings,
  useAdminUsers,
  useIngestRuns,
  useStartIngest,
  useUpdateAdminSettings,
  useUpdateUser,
} from "./queries";
import "./strings";

type Schemas = components["schemas"];

function SettingsSection(): React.JSX.Element {
  const { t } = useTranslation();
  const settings = useAdminSettings();
  const update = useUpdateAdminSettings();
  const data = settings.data;
  const change = (patch: Partial<Schemas["AdminSettingsFields"]>): void => {
    if (data === undefined) return;
    update.mutate({
      registration_open: data.registration_open,
      diet_feature_enabled: data.diet_feature_enabled,
      ...patch,
    });
  };
  return (
    <section className={shared["card"]} aria-labelledby="admin-settings-title">
      <h2 id="admin-settings-title">{t("admin.settings")}</h2>
      <QueryState
        isLoading={settings.isLoading}
        isError={settings.isError}
        loadingLabel={t("admin.loading")}
        errorLabel={t("admin.error")}
      >
        {data && (
          <div className={shared["stack"]}>
            <label className={shared["row"]}>
              <input
                type="checkbox"
                checked={data.registration_open}
                disabled={update.isPending}
                onChange={(e) => { change({ registration_open: e.target.checked }); }}
              />
              {t("admin.registrationOpen")}
            </label>
            <label className={shared["row"]}>
              <input
                type="checkbox"
                checked={data.diet_feature_enabled}
                disabled={update.isPending}
                onChange={(e) => { change({ diet_feature_enabled: e.target.checked }); }}
              />
              {t("admin.dietFeature")}
            </label>
            <p className={shared["muted"]}>
              {t("admin.mediaAuth", { value: data.media_require_auth ? t("admin.yes") : t("admin.no") })}
              <br />
              {t("admin.datasetCommit")}: <code>{data.dataset_commit}</code>
            </p>
            {update.isSuccess && <p role="status">{t("admin.saved")}</p>}
            {update.isError && <p role="alert">{t("admin.saveError")}</p>}
          </div>
        )}
      </QueryState>
    </section>
  );
}

function UsersSection(): React.JSX.Element {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const users = useAdminUsers(q);
  const update = useUpdateUser();
  return (
    <section className={shared["card"]} aria-labelledby="admin-users-title">
      <h2 id="admin-users-title">{t("admin.users")}</h2>
      <label className={shared["field"]}>
        {t("admin.search")}
        <input type="search" value={q} onChange={(e) => { setQ(e.target.value); }} />
      </label>
      <QueryState
        isLoading={users.isLoading}
        isError={users.isError}
        loadingLabel={t("admin.loading")}
        errorLabel={t("admin.error")}
      >
        <table className={shared["table"]}>
          <thead>
            <tr>
              <th scope="col">{t("admin.email")}</th>
              <th scope="col">{t("admin.name")}</th>
              <th scope="col">{t("admin.role")}</th>
              <th scope="col">{t("admin.active")}</th>
              <th scope="col">{t("admin.lastLogin")}</th>
            </tr>
          </thead>
          <tbody>
            {users.data?.items.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.display_name}</td>
                <td>
                  <select
                    aria-label={t("admin.roleOf", { email: u.email })}
                    value={u.role}
                    disabled={update.isPending}
                    onChange={(e) => {
                      update.mutate({ id: u.id, patch: { role: e.target.value as Schemas["UserRole"] } });
                    }}
                  >
                    <option value="user">{t("admin.role_user")}</option>
                    <option value="admin">{t("admin.role_admin")}</option>
                  </select>
                </td>
                <td>
                  <input
                    type="checkbox"
                    aria-label={t("admin.activeOf", { email: u.email })}
                    checked={u.is_active}
                    disabled={update.isPending}
                    onChange={(e) => {
                      update.mutate({ id: u.id, patch: { is_active: e.target.checked } });
                    }}
                  />
                </td>
                <td>
                  {u.last_login_at === null
                    ? t("admin.never")
                    : formatDate(u.last_login_at, { dateStyle: "medium", timeStyle: "short" })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {update.isError && <p role="alert">{t("admin.saveError")}</p>}
      </QueryState>
    </section>
  );
}

function IngestSection(): React.JSX.Element {
  const { t } = useTranslation();
  const runs = useIngestRuns();
  const start = useStartIngest();
  return (
    <section className={shared["card"]} aria-labelledby="admin-ingest-title">
      <h2 id="admin-ingest-title">{t("admin.ingest")}</h2>
      <p className={shared["muted"]}>{t("admin.ingestHelp")}</p>
      <div className={shared["row"]}>
        <button type="button" className={shared["btn"]} disabled={start.isPending} onClick={() => { start.mutate(true); }}>
          {t("admin.ingestDry")}
        </button>
        <button type="button" className={shared["btn"]} disabled={start.isPending} onClick={() => { start.mutate(false); }}>
          {t("admin.ingestReal")}
        </button>
      </div>
      {start.isSuccess && <p role="status">{t("admin.ingestStarted")}</p>}
      {start.isError && <p role="alert">{t("admin.saveError")}</p>}
      <h3>{t("admin.runs")}</h3>
      <QueryState
        isLoading={runs.isLoading}
        isError={runs.isError}
        loadingLabel={t("admin.loading")}
        errorLabel={t("admin.error")}
      >
        {runs.data?.items.length === 0 && <p className={shared["muted"]}>{t("admin.noRuns")}</p>}
        <ul className={shared["list"]}>
          {runs.data?.items.map((run) => (
            <li key={run.id} className={shared["card"]}>
              <strong>
                {t("admin.runTitle", { status: t(`admin.status_${run.status}`), commit: run.commit.slice(0, 7) })}
              </strong>
              {run.dry_run && <span className={shared["muted"]}> · {t("admin.dryRun")}</span>}
              {run.started_at !== null && (
                <p className={shared["muted"]}>
                  {t("admin.started", { date: formatDate(run.started_at, { dateStyle: "medium", timeStyle: "short" }) })}
                </p>
              )}
              {run.counts !== null && <p>{t("admin.counts", { added: run.counts.added, updated: run.counts.updated, deprecated: run.counts.deprecated, unchanged: run.counts.unchanged })}</p>}
              {run.diff !== null && (
                <p className={shared["muted"]}>
                  {t("admin.diff", { added: run.diff.added.length, updated: run.diff.updated.length, deprecated: run.diff.deprecated.length })}
                </p>
              )}
              {run.errors.length > 0 && (
                <div role="group" aria-label={t("admin.errors")}>
                  <strong>{t("admin.errors")}</strong>
                  <ul>{run.errors.map((e) => <li key={e}>{e}</li>)}</ul>
                </div>
              )}
              {run.warnings.length > 0 && (
                <div role="group" aria-label={t("admin.warnings")}>
                  <strong>{t("admin.warnings")}</strong>
                  <ul>{run.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
                </div>
              )}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

/** Pantalla «Admin» (MASTER_PROMPT §10.2.11). El servidor autoriza; aquí solo se oculta. */
export function AdminScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const me = useProfileSummary();
  return (
    <section aria-labelledby="admin-title" className={shared["page"]}>
      <h1 id="admin-title">{t("admin.title")}</h1>
      <QueryState
        isLoading={me.isLoading}
        isError={me.isError}
        loadingLabel={t("admin.loading")}
        errorLabel={t("admin.error")}
      >
        {me.data?.role === "admin" ? (
          <>
            <SettingsSection />
            <UsersSection />
            <IngestSection />
          </>
        ) : (
          <p role="note">{t("admin.forbidden")}</p>
        )}
      </QueryState>
    </section>
  );
}

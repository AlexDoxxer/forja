import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import { i18next } from "../../i18n";
import { api } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import { applyTheme } from "../../lib/theme";
import { collectActiveProgramMedia, offlineSupported, requestPrecache } from "../../sw/library";
import { formatDate } from "../shared/format";
import shared from "../shared/ui.module.css";
import { useProfileSummary } from "../today/useProfileSummary";
import { reloadToHome } from "./navigation";
import { resolveTheme } from "./theme";
import { useAboutInfo } from "./useAboutInfo";
import {
  deleteAccount,
  fetchExport,
  importExport,
  toProfileFields,
  useAuthSessions,
  useProfile,
  useRevokeSession,
  useSaveProfile,
  type ProfileFields,
} from "./queries";
import "../auth/strings";
import "./strings";

type Schemas = components["schemas"];

function SettingsSection({ profile }: { profile: Schemas["Profile"] }): React.JSX.Element {
  const { t } = useTranslation();
  const save = useSaveProfile();
  const [form, setForm] = useState<ProfileFields>(() => toProfileFields(profile));
  const prefs = form.preferences;
  const setPref = <K extends keyof ProfileFields["preferences"]>(key: K, value: ProfileFields["preferences"][K]): void => {
    setForm((f) => ({ ...f, preferences: { ...f.preferences, [key]: value } }));
  };

  return (
    <section className={shared["card"]} aria-labelledby="settings-title">
      <h2 id="settings-title">{t("profileB.settings")}</h2>
      <form
        className={shared["stack"]}
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate(form, {
            onSuccess: () => {
              applyTheme(resolveTheme(form.preferences.theme));
              if (i18next.language !== form.locale) void i18next.changeLanguage(form.locale);
            },
          });
        }}
      >
        <div className={shared["grid"]}>
          <label className={shared["field"]}>
            {t("profileB.displayName")}
            <input value={form.display_name} onChange={(e) => { setForm({ ...form, display_name: e.target.value }); }} />
          </label>
          <label className={shared["field"]}>
            {t("profileB.units")}
            <select value={form.units} onChange={(e) => { setForm({ ...form, units: e.target.value as ProfileFields["units"] }); }}>
              <option value="metric">{t("profileB.units_metric")}</option>
              <option value="imperial">{t("profileB.units_imperial")}</option>
            </select>
          </label>
          <label className={shared["field"]}>
            {t("profileB.language")}
            <select value={form.locale} onChange={(e) => { setForm({ ...form, locale: e.target.value as ProfileFields["locale"] }); }}>
              <option value="es">{t("profileB.lang_es")}</option>
              <option value="en">{t("profileB.lang_en")}</option>
            </select>
          </label>
          <label className={shared["field"]}>
            {t("profileB.theme")}
            <select value={prefs.theme} onChange={(e) => { setPref("theme", e.target.value as Schemas["ThemePreference"]); }}>
              <option value="dark">{t("profileB.theme_dark")}</option>
              <option value="light">{t("profileB.theme_light")}</option>
              <option value="system">{t("profileB.theme_system")}</option>
            </select>
          </label>
          <label className={shared["field"]}>
            {t("profileB.defaultRest")}
            <input
              type="number"
              min={0}
              max={600}
              value={prefs.default_rest_s ?? ""}
              onChange={(e) => { setPref("default_rest_s", e.target.value === "" ? null : Number(e.target.value)); }}
            />
          </label>
        </div>
        <label className={shared["row"]}>
          <input type="checkbox" checked={prefs.sounds} onChange={(e) => { setPref("sounds", e.target.checked); }} />
          {t("profileB.sounds")}
        </label>
        <label className={shared["row"]}>
          <input type="checkbox" checked={prefs.vibration} onChange={(e) => { setPref("vibration", e.target.checked); }} />
          {t("profileB.vibration")}
        </label>
        <div>
          <button type="submit" className={shared["btn"]} disabled={save.isPending}>
            {t("profileB.save")}
          </button>
        </div>
        {save.isSuccess && <p role="status">{t("profileB.saved")}</p>}
        {save.isError && <p role="alert">{t("profileB.saveError")}</p>}
      </form>
    </section>
  );
}

/** Lee un archivo como texto (FileReader: disponible en todos los navegadores objetivo). */
function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve(typeof reader.result === "string" ? reader.result : "");
    };
    reader.onerror = () => {
      reject(new Error("No se pudo leer el archivo."));
    };
    reader.readAsText(file);
  });
}

function DataSection(): React.JSX.Element {
  const { t } = useTranslation();
  const [message, setMessage] = useState<{ kind: "status" | "alert"; text: string } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");

  const onExport = async (): Promise<void> => {
    try {
      const blob = await fetchExport();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `forja-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage(null);
    } catch {
      setMessage({ kind: "alert", text: t("profileB.exportError") });
    }
  };

  const onImport = async (file: File): Promise<void> => {
    let payload: Schemas["UserExport"];
    try {
      payload = JSON.parse(await readFileText(file)) as Schemas["UserExport"];
      if ((payload.format as string) !== "forja-export") throw new Error("formato");
    } catch {
      setMessage({ kind: "alert", text: t("profileB.importInvalid") });
      return;
    }
    try {
      const result = await importExport(payload);
      setMessage({
        kind: "status",
        text: t("profileB.importDone", {
          sessions: result.created.sessions,
          programs: result.created.programs,
          sets: result.created.sets,
        }),
      });
    } catch {
      setMessage({ kind: "alert", text: t("profileB.importError") });
    }
  };

  const onDelete = async (): Promise<void> => {
    try {
      await deleteAccount(password);
      reloadToHome();
    } catch {
      setMessage({ kind: "alert", text: t("profileB.deleteError") });
    }
  };

  return (
    <section className={shared["card"]} aria-labelledby="data-title">
      <h2 id="data-title">{t("profileB.data")}</h2>
      <div className={shared["stack"]}>
        <div className={shared["row"]}>
          <button type="button" className={shared["btn"]} onClick={() => void onExport()}>
            {t("profileB.export")}
          </button>
        </div>
        <label className={shared["field"]}>
          {t("profileB.importFile")}
          <input
            type="file"
            accept="application/json,.json"
            onChange={(e) => {
              const input = e.currentTarget;
              const file = input.files?.[0];
              if (file !== undefined) void onImport(file).finally(() => { input.value = ""; });
            }}
          />
        </label>
        {!confirming ? (
          <div>
            <button
              type="button"
              className={`${shared["btn"] ?? ""} ${shared["danger"] ?? ""}`}
              onClick={() => {
                setConfirming(true);
              }}
            >
              {t("profileB.delete")}
            </button>
          </div>
        ) : (
          <form
            className={shared["stack"]}
            role="group"
            aria-label={t("profileB.delete")}
            onSubmit={(event) => {
              event.preventDefault();
              void onDelete();
            }}
          >
            <p className={shared["notice"]} role="note">
              {t("profileB.deleteWarning")}
            </p>
            <label className={shared["field"]}>
              {t("profileB.deletePassword")}
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                }}
              />
            </label>
            <div className={shared["row"]}>
              <button type="submit" className={`${shared["btn"] ?? ""} ${shared["danger"] ?? ""}`} disabled={password === ""}>
                {t("profileB.deleteConfirm")}
              </button>
              <button
                type="button"
                className={shared["btn"]}
                onClick={() => {
                  setConfirming(false);
                  setPassword("");
                }}
              >
                {t("profileB.deleteCancel")}
              </button>
            </div>
          </form>
        )}
        {message !== null && <p role={message.kind}>{message.text}</p>}
      </div>
    </section>
  );
}

function SessionsSection(): React.JSX.Element {
  const { t } = useTranslation();
  const sessions = useAuthSessions();
  const revoke = useRevokeSession();
  return (
    <section className={shared["card"]} aria-labelledby="sessions-title">
      <h2 id="sessions-title">{t("profileB.sessions")}</h2>
      <QueryState
        isLoading={sessions.isLoading}
        isError={sessions.isError}
        loadingLabel={t("profile.loading")}
        errorLabel={t("profile.error")}
      >
        <ul className={shared["list"]}>
          {sessions.data?.items.map((s) => {
            const agent = s.user_agent ?? t("profileB.unknownAgent");
            return (
              <li key={s.id} className={`${shared["row"] ?? ""} ${shared["spread"] ?? ""}`}>
                <span>
                  <strong>{s.current ? t("profileB.thisDevice") : agent}</strong>
                  <br />
                  <small className={shared["muted"]}>
                    {t("profileB.lastSeen", { date: formatDate(s.last_seen_at, { dateStyle: "medium", timeStyle: "short" }) })}
                  </small>
                </span>
                {!s.current && (
                  <button
                    type="button"
                    className={shared["btn"]}
                    disabled={revoke.isPending}
                    onClick={() => { revoke.mutate(s.id); }}
                  >
                    {t("profileB.revoke", { agent })}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </QueryState>
    </section>
  );
}

function OfflineSection(): React.JSX.Element {
  const { t } = useTranslation();
  const [state, setState] = useState<{ kind: "idle" | "busy" | "done" | "none" | "error"; count?: number }>({ kind: "idle" });
  const supported = offlineSupported();

  const run = async (): Promise<void> => {
    setState({ kind: "busy" });
    try {
      const urls = await collectActiveProgramMedia();
      if (urls.length === 0) {
        setState({ kind: "none" });
        return;
      }
      setState({ kind: "done", count: await requestPrecache(urls) });
    } catch {
      setState({ kind: "error" });
    }
  };

  return (
    <section className={shared["card"]} aria-labelledby="offline-title">
      <h2 id="offline-title">{t("profileB.offline")}</h2>
      <div className={shared["stack"]}>
        <div>
          <button type="button" className={shared["btn"]} disabled={!supported || state.kind === "busy"} onClick={() => void run()}>
            {state.kind === "busy" ? t("profileB.downloading") : t("profileB.downloadLibrary")}
          </button>
        </div>
        {!supported && <p className={shared["muted"]}>{t("profileB.downloadUnsupported")}</p>}
        {state.kind === "done" && <p role="status">{t("profileB.downloadDone", { count: state.count ?? 0 })}</p>}
        {state.kind === "none" && <p role="status">{t("profileB.downloadNone")}</p>}
        {state.kind === "error" && <p role="alert">{t("profileB.downloadError")}</p>}
      </div>
    </section>
  );
}

function LogoutButton(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const logout = async (): Promise<void> => {
    try {
      const result = await api.POST("/auth/logout");
      if (!result.response.ok) throw new Error("logout");
      queryClient.clear();
      await navigate({ to: "/login", replace: true });
    } catch {
      setFailed(true);
    }
  };
  return (
    <div className={shared["row"]}>
      <button type="button" className={shared["btn"]} onClick={() => void logout()}>
        {t("auth.logout")}
      </button>
      {failed && <p role="alert">{t("auth.logoutError")}</p>}
    </div>
  );
}

function CreditsSection(): React.JSX.Element {
  const { t } = useTranslation();
  const about = useAboutInfo();
  return (
    <QueryState
      isLoading={about.isLoading}
      isError={about.isError}
      loadingLabel={t("profile.loading")}
      errorLabel={t("profile.error")}
    >
      {about.data && (
        <section className={shared["card"]} aria-label={t("profile.credits")}>
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
  );
}

/** Pantalla «Perfil y ajustes» (MASTER_PROMPT §10.2.10). */
export function ProfileScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const profile = useProfile();
  const me = useProfileSummary();

  return (
    <section aria-labelledby="profile-title" className={shared["page"]}>
      <h1 id="profile-title">{t("profile.title")}</h1>
      {(me.data?.diet_available === true || me.data?.role === "admin") && (
        <nav aria-label={t("profileB.links")} className={shared["row"]}>
          {me.data.diet_available && (
            <Link to="/nutricion" className={shared["btn"]}>
              {t("profileB.nutrition")}
            </Link>
          )}
          {me.data.role === "admin" && (
            <Link to="/admin" className={shared["btn"]}>
              {t("profileB.admin")}
            </Link>
          )}
        </nav>
      )}
      <QueryState
        isLoading={profile.isLoading}
        isError={profile.isError}
        loadingLabel={t("profile.loading")}
        errorLabel={t("profile.error")}
      >
        {profile.data && <SettingsSection profile={profile.data} />}
      </QueryState>
      <div className={shared["grid"]}>
        <DataSection />
        <SessionsSection />
        <OfflineSection />
      </div>
      <LogoutButton />
      <CreditsSection />
    </section>
  );
}

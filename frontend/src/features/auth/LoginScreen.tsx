import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, TextField } from "../../components/ui";
import { api } from "../../lib/api/client";
import shared from "../shared/ui.module.css";
import "./strings";

/** Pantalla de inicio de sesión (`POST /auth/login`, cookie de sesión: ADR 0003). */
export function LoginScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.POST("/auth/login", { body: { email, password } });
      if (result.response.ok) {
        // Datos de otra sesión anterior no deben quedar en caché.
        queryClient.clear();
        await navigate({ to: "/", replace: true });
        return;
      }
      const status = result.response.status;
      setError(status === 429 ? t("auth.tooMany") : status === 401 || status === 422 ? t("auth.invalid") : t("auth.failed"));
    } catch {
      setError(t("auth.failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="login-title" className={shared["page"]}>
      <h1 id="login-title">{t("auth.loginTitle")}</h1>
      <form
        className={shared["stack"]}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <TextField
          label={t("auth.email")}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
          }}
        />
        <TextField
          label={t("auth.password")}
          type="password"
          autoComplete="current-password"
          required
          value={password}
          error={error}
          onChange={(e) => {
            setPassword(e.target.value);
          }}
        />
        <div>
          <Button type="submit" variant="primary" disabled={busy || email === "" || password === ""}>
            {busy ? t("auth.submitting") : t("auth.submit")}
          </Button>
        </div>
      </form>
      <p>
        {t("auth.noAccount")} <Link to="/onboarding">{t("auth.createAccount")}</Link>
      </p>
    </section>
  );
}

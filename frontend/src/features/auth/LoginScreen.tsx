import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { motion, type Target, type TargetAndTransition, type Transition } from "framer-motion";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { IconDumbbell, IconEmber, IconServer, IconSettings } from "../../components/icons";
import { api } from "../../lib/api/client";
import { useReducedMotion } from "../../lib/useReducedMotion";
import styles from "./LoginScreen.module.css";
import "./strings";

/** Curva y ritmo de la coreografía de entrada (encargo F5-FE-01): easing fijo, ~1.05 s. */
const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const DURATION = 1.05;

interface Reveal {
  initial: boolean | Target;
  animate?: TargetAndTransition;
  transition?: Transition;
}

/**
 * Construye `initial`/`animate`/`transition` para un `motion.*`. Con movimiento reducido,
 * `initial: false` hace que Framer Motion monte el elemento directamente en el estado de
 * `animate` (reposo, sin animar nada) en vez de mantener dos ramas de JSX distintas.
 */
function reveal(
  reducedMotion: boolean,
  initial: Target,
  animate: TargetAndTransition,
  delay: number,
  duration: number = DURATION,
): Reveal {
  if (reducedMotion) return { initial: false };
  return { initial, animate, transition: { duration, delay, ease: EASE } };
}

interface GlassFieldProps {
  label: string;
  type: string;
  autoComplete: string;
  value: string;
  error?: string | null;
  onChange: (value: string) => void;
}

/** Campo con estética de vidrio esmerilado; misma semántica accesible que `ui/Field.tsx`. */
function GlassField({ label, type, autoComplete, value, error, onChange }: GlassFieldProps): React.JSX.Element {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={styles["field"]}>
      <label htmlFor={id} className={styles["fieldLabel"]}>
        {label}
      </label>
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        required
        className={styles["input"]}
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
      {error ? (
        <p id={errorId} role="alert" className={styles["fieldError"]}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Pantalla de inicio de sesión (`POST /auth/login`, cookie de sesión: ADR 0003) — y, a la vez,
 * la landing de Forja: la app es autoalojada y solo accesible tras iniciar sesión, así que no
 * hay un sitio de marketing aparte (encargo F5-FE-01, `docs/handoffs/f5-login-landing.md`).
 */
export function LoginScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();
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
    <section aria-labelledby="hero-title" className={styles["hero"]}>
      <div className={styles["glow"]} aria-hidden="true" />
      <div className={styles["scrim"]} aria-hidden="true" />
      <div className={styles["grain"]} aria-hidden="true" />

      <motion.div className={styles["topbar"]} {...reveal(reducedMotion, { opacity: 0, y: -10 }, { opacity: 1, y: 0 }, 0.08)}>
        <p className={styles["wordmark"]}>{t("app.name")}</p>
        <Link to="/onboarding" className={styles["ghostLink"]}>
          {t("auth.createAccount")}
        </Link>
      </motion.div>

      <div className={styles["heroMid"]}>
        <motion.p
          className={styles["badge"]}
          {...reveal(reducedMotion, { opacity: 0, scale: 0.82 }, { opacity: 1, scale: 1 }, 0.22)}
        >
          <IconEmber className={styles["badgeIcon"]} width={16} height={16} />
          {t("auth.landing.badge")}
        </motion.p>

        <h1 id="hero-title" className={styles["headline"]}>
          <span className={styles["lineMask"]}>
            <motion.span
              className={styles["line"]}
              {...reveal(reducedMotion, { y: "40%", opacity: 0 }, { y: "0%", opacity: 1 }, 0.42)}
            >
              <span className={styles["accent"]}>{t("app.name")}</span> {t("auth.landing.headlineRest")}
            </motion.span>
          </span>
          <span className={styles["lineMask"]}>
            <motion.span
              className={styles["line"]}
              {...reveal(reducedMotion, { y: "40%", opacity: 0 }, { y: "0%", opacity: 1 }, 0.62)}
            >
              {t("auth.landing.headlineLine2")}
            </motion.span>
          </span>
        </h1>

        <motion.p className={styles["lede"]} {...reveal(reducedMotion, { opacity: 0 }, { opacity: 1 }, 0.82, 1.25)}>
          {t("auth.landing.lede")}
        </motion.p>

        <h2 className={styles["srOnly"]}>{t("auth.loginTitle")}</h2>
        <motion.form
          className={styles["form"]}
          {...reveal(reducedMotion, { opacity: 0, y: 14 }, { opacity: 1, y: 0 }, 0.96)}
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <GlassField
            label={t("auth.email")}
            type="email"
            autoComplete="email"
            value={email}
            onChange={setEmail}
          />
          <GlassField
            label={t("auth.password")}
            type="password"
            autoComplete="current-password"
            value={password}
            error={error}
            onChange={setPassword}
          />
          <button type="submit" className={styles["submit"]} disabled={busy || email === "" || password === ""}>
            {busy ? t("auth.submitting") : t("auth.submit")}
          </button>
        </motion.form>

        <motion.p
          className={styles["secondary"]}
          {...reveal(reducedMotion, { opacity: 0, x: -12 }, { opacity: 1, x: 0 }, 1.1)}
        >
          {t("auth.noAccount")}{" "}
          <Link to="/onboarding" className={styles["secondaryLink"]}>
            {t("auth.createAccount")}
          </Link>
        </motion.p>
      </div>

      <footer className={styles["stats"]}>
        <motion.p className={styles["stat"]} {...reveal(reducedMotion, { opacity: 0, y: 10 }, { opacity: 1, y: 0 }, 1.12)}>
          <IconDumbbell className={styles["statIcon"]} width={16} height={16} />
          {t("auth.landing.stat1")}
        </motion.p>
        <motion.p className={styles["stat"]} {...reveal(reducedMotion, { opacity: 0, y: 10 }, { opacity: 1, y: 0 }, 1.28)}>
          <IconServer className={styles["statIcon"]} width={16} height={16} />
          {t("auth.landing.stat2")}
        </motion.p>
        <motion.p className={styles["stat"]} {...reveal(reducedMotion, { opacity: 0, y: 10 }, { opacity: 1, y: 0 }, 1.44)}>
          <IconSettings className={styles["statIcon"]} width={16} height={16} />
          {t("auth.landing.stat3")}
        </motion.p>
      </footer>
    </section>
  );
}

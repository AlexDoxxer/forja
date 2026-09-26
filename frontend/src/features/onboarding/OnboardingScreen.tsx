import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Chip, TextField } from "../../components/ui";
import { ChoiceCard } from "../../components/ui";
import { api, unwrapApi } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import {
  EQUIPMENT_CODES,
  EXPERIENCES,
  MUSCLE_CODES,
  PRESETS,
  SEXES,
  type EquipmentCode,
  type EquipmentPreset,
  type Experience,
  type MuscleCode,
  type Sex,
} from "../shared/enums";
import styles from "./Onboarding.module.css";

type ParqAnswers = components["schemas"]["ParqAnswers"];
type ParqKey = keyof ParqAnswers;

const PARQ_KEYS: readonly ParqKey[] = [
  "heart_condition",
  "chest_pain_activity",
  "chest_pain_rest",
  "dizziness_or_fainting",
  "bone_or_joint_problem",
  "blood_pressure_or_heart_medication",
  "other_reason",
];

const STEP_KEYS = ["account", "basics", "parq", "equipment"] as const;
const TOTAL_STEPS = STEP_KEYS.length;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Errors = Record<string, string | undefined>;

/**
 * Onboarding de 4 pasos (MASTER_PROMPT §10.2.1): cuenta → datos básicos → PAR-Q → equipamiento y
 * limitaciones. El perfil y el PAR-Q se guardan al terminar, en ese orden, para que un «sí» en el
 * PAR-Q fije el nivel a principiante después de la elección de experiencia (contrato `submitParq`).
 */
export function OnboardingScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [accountCreated, setAccountCreated] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  const [sex, setSex] = useState<Sex>("unspecified");
  const [birthDate, setBirthDate] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [experience, setExperience] = useState<Experience>("beginner");

  const [parq, setParq] = useState<Partial<Record<ParqKey, boolean>>>({});

  const [preset, setPreset] = useState<EquipmentPreset>("full_gym");
  const [items, setItems] = useState<readonly EquipmentCode[]>([]);
  const [avoidMuscles, setAvoidMuscles] = useState<readonly MuscleCode[]>([]);
  const [dietEnabled, setDietEnabled] = useState(false);

  const parqFlagged = PARQ_KEYS.some((key) => parq[key] === true);

  const toggle = <T extends string>(list: readonly T[], value: T): T[] =>
    list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

  const registerAccount = async (): Promise<boolean> => {
    const next: Errors = {};
    if (!EMAIL_PATTERN.test(email)) next["email"] = t("onboarding.account.errorEmail");
    if (password.length < 10) next["password"] = t("onboarding.account.errorPasswordShort");
    if (displayName.trim() === "") next["displayName"] = t("onboarding.account.errorName");
    setErrors(next);
    if (Object.keys(next).length > 0) return false;
    if (accountCreated) return true;

    setBusy(true);
    setFormError(null);
    const result = await api.POST("/auth/register", {
      body: { email, password, display_name: displayName.trim(), locale: "es" },
    });
    setBusy(false);
    if (result.error !== undefined) {
      const status = result.response.status;
      setFormError(
        status === 409
          ? t("onboarding.account.errorConflict")
          : status === 403
            ? t("onboarding.account.errorForbidden")
            : t("onboarding.account.errorGeneric"),
      );
      return false;
    }
    setAccountCreated(true);
    return true;
  };

  const validateBasics = (): boolean => {
    const next: Errors = {};
    const height = Number(heightCm);
    if (heightCm !== "" && (Number.isNaN(height) || height < 100 || height > 250)) {
      next["height"] = t("onboarding.basics.errorHeight");
    }
    const weight = Number(weightKg);
    if (weightKg !== "" && (Number.isNaN(weight) || weight < 20 || weight > 400)) {
      next["weight"] = t("onboarding.basics.errorWeight");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const validateEquipment = (): boolean => {
    const ok = preset !== "custom" || items.length > 0;
    setErrors(ok ? {} : { items: t("onboarding.equipment.itemsRequired") });
    return ok;
  };

  const saveAll = async (): Promise<void> => {
    setBusy(true);
    setFormError(null);
    try {
      const current = unwrapApi(await api.GET("/profile"));
      const height = heightCm === "" ? null : Number(heightCm);
      unwrapApi(
        await api.PUT("/profile", {
          body: {
            display_name: current.display_name,
            locale: current.locale,
            units: current.units,
            sex,
            birth_date: birthDate === "" ? null : birthDate,
            height_cm: height,
            experience,
            activity_level: current.activity_level,
            equipment: { preset, items: preset === "custom" ? [...items] : [] },
            limitations: { avoid_muscles: [...avoidMuscles], avoid_patterns: [], notes: null },
            diet_enabled: dietEnabled,
            preferences: current.preferences,
          },
        }),
      );
      const answers: ParqAnswers = {
        heart_condition: parq.heart_condition === true,
        chest_pain_activity: parq.chest_pain_activity === true,
        chest_pain_rest: parq.chest_pain_rest === true,
        dizziness_or_fainting: parq.dizziness_or_fainting === true,
        bone_or_joint_problem: parq.bone_or_joint_problem === true,
        blood_pressure_or_heart_medication: parq.blood_pressure_or_heart_medication === true,
        other_reason: parq.other_reason === true,
      };
      const parqResult = unwrapApi(await api.PUT("/profile/parq", { body: { answers } }));
      setRecommendation(parqResult.recommendation_es);
      if (weightKg !== "") {
        await api.POST("/body-metrics", {
          body: { date: new Date().toISOString().slice(0, 10), weight_kg: Number(weightKg) },
        });
      }
      setDone(true);
    } catch {
      setFormError(t("onboarding.errorSave"));
    } finally {
      setBusy(false);
    }
  };

  const goNext = async (): Promise<void> => {
    if (step === 0) {
      if (await registerAccount()) setStep(1);
    } else if (step === 1) {
      if (validateBasics()) setStep(2);
    } else if (step === 2) {
      setStep(3);
    } else if (validateEquipment()) {
      await saveAll();
    }
  };

  if (done) {
    return (
      <section aria-labelledby="onboarding-done" className={styles["root"]}>
        <h1 id="onboarding-done">{t("onboarding.done.heading")}</h1>
        <p>{t("onboarding.done.body")}</p>
        {recommendation !== null && (
          <p role="note" className={styles["notice"]}>
            <strong>{t("onboarding.done.recommendation")}: </strong>
            {recommendation}
          </p>
        )}
        <Link to="/rutinas/nueva" className={styles["cta"]}>
          {t("onboarding.done.cta")}
        </Link>
      </section>
    );
  }

  const currentKey = STEP_KEYS[step] ?? "account";

  return (
    <section aria-labelledby="onboarding-title" className={styles["root"]}>
      <h1 id="onboarding-title">{t("onboarding.title")}</h1>
      <p aria-live="polite" className={styles["progress"]}>
        {t("onboarding.stepOf", { current: step + 1, total: TOTAL_STEPS })} · {t(`onboarding.steps.${currentKey}`)}
      </p>
      <progress className={styles["bar"]} max={TOTAL_STEPS} value={step + 1} aria-label={t("onboarding.title")} />

      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void goNext();
        }}
      >
        {step === 0 && (
          <fieldset className={styles["step"]}>
            <legend>{t("onboarding.account.heading")}</legend>
            <TextField
              label={t("onboarding.account.email")}
              type="email"
              autoComplete="email"
              value={email}
              error={errors["email"] ?? null}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              disabled={accountCreated}
            />
            <TextField
              label={t("onboarding.account.password")}
              type="password"
              autoComplete="new-password"
              hint={t("onboarding.account.passwordHint")}
              value={password}
              error={errors["password"] ?? null}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
              disabled={accountCreated}
            />
            <TextField
              label={t("onboarding.account.displayName")}
              autoComplete="name"
              value={displayName}
              error={errors["displayName"] ?? null}
              onChange={(event) => {
                setDisplayName(event.target.value);
              }}
              disabled={accountCreated}
            />
          </fieldset>
        )}

        {step === 1 && (
          <fieldset className={styles["step"]}>
            <legend>{t("onboarding.basics.heading")}</legend>
            <p className={styles["label"]}>{t("onboarding.basics.sex")}</p>
            <div className={styles["chips"]} role="group" aria-label={t("onboarding.basics.sex")}>
              {SEXES.map((value) => (
                <Chip
                  key={value}
                  selected={sex === value}
                  onSelectedChange={() => {
                    setSex(value);
                  }}
                >
                  {t(`enums.sex.${value}`)}
                </Chip>
              ))}
            </div>
            <p className={styles["hint"]}>{t("onboarding.basics.sexHint")}</p>
            <TextField
              label={t("onboarding.basics.birthDate")}
              type="date"
              value={birthDate}
              onChange={(event) => {
                setBirthDate(event.target.value);
              }}
            />
            <TextField
              label={t("onboarding.basics.height")}
              type="number"
              inputMode="decimal"
              value={heightCm}
              error={errors["height"] ?? null}
              onChange={(event) => {
                setHeightCm(event.target.value);
              }}
            />
            <TextField
              label={t("onboarding.basics.weight")}
              type="number"
              inputMode="decimal"
              hint={t("onboarding.basics.weightHint")}
              value={weightKg}
              error={errors["weight"] ?? null}
              onChange={(event) => {
                setWeightKg(event.target.value);
              }}
            />
            <p className={styles["label"]}>{t("onboarding.basics.experience")}</p>
            <div className={styles["chips"]} role="group" aria-label={t("onboarding.basics.experience")}>
              {EXPERIENCES.map((value) => (
                <Chip
                  key={value}
                  selected={experience === value}
                  onSelectedChange={() => {
                    setExperience(value);
                  }}
                >
                  {t(`enums.experience.${value}`)}
                </Chip>
              ))}
            </div>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset className={styles["step"]}>
            <legend>{t("onboarding.parq.heading")}</legend>
            <p>{t("onboarding.parq.intro")}</p>
            {PARQ_KEYS.map((key) => (
              <div key={key} role="radiogroup" aria-label={t(`onboarding.parq.questions.${key}`)} className={styles["question"]}>
                <p>{t(`onboarding.parq.questions.${key}`)}</p>
                <div className={styles["chips"]}>
                  {[true, false].map((answer) => (
                    <label key={String(answer)} className={styles["radio"]}>
                      <input
                        type="radio"
                        name={key}
                        checked={parq[key] === answer}
                        onChange={() => {
                          setParq((current) => ({ ...current, [key]: answer }));
                        }}
                      />
                      {answer ? t("onboarding.parq.yes") : t("onboarding.parq.no")}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            {parqFlagged && (
              <p role="status" className={styles["notice"]}>
                {t("onboarding.parq.flagged")}
              </p>
            )}
            <p className={styles["hint"]}>{t("onboarding.parq.disclaimer")}</p>
          </fieldset>
        )}

        {step === 3 && (
          <fieldset className={styles["step"]}>
            <legend>{t("onboarding.equipment.heading")}</legend>
            <p className={styles["label"]}>{t("onboarding.equipment.preset")}</p>
            <div className={styles["cards"]}>
              {PRESETS.map((value) => (
                <ChoiceCard
                  key={value}
                  selected={preset === value}
                  title={t(`enums.preset.${value}`)}
                  onSelect={() => {
                    setPreset(value);
                  }}
                />
              ))}
            </div>
            {preset === "custom" && (
              <>
                <p className={styles["label"]}>{t("onboarding.equipment.items")}</p>
                <div className={styles["chips"]} role="group" aria-label={t("onboarding.equipment.items")}>
                  {EQUIPMENT_CODES.map((code) => (
                    <Chip
                      key={code}
                      selected={items.includes(code)}
                      onSelectedChange={() => {
                        setItems((current) => toggle(current, code));
                      }}
                    >
                      {t(`enums.equipment.${code}`)}
                    </Chip>
                  ))}
                </div>
                {errors["items"] !== undefined && (
                  <p role="alert" className={styles["error"]}>
                    {errors["items"]}
                  </p>
                )}
              </>
            )}
            <p className={styles["label"]}>{t("onboarding.equipment.avoidMuscles")}</p>
            <div className={styles["chips"]} role="group" aria-label={t("onboarding.equipment.avoidMuscles")}>
              {MUSCLE_CODES.filter((code) => code !== "cardio").map((code) => (
                <Chip
                  key={code}
                  selected={avoidMuscles.includes(code)}
                  onSelectedChange={() => {
                    setAvoidMuscles((current) => toggle(current, code));
                  }}
                >
                  {t(`enums.muscle.${code}`)}
                </Chip>
              ))}
            </div>
            <label className={styles["diet"]}>
              <input
                type="checkbox"
                checked={dietEnabled}
                onChange={(event) => {
                  setDietEnabled(event.target.checked);
                }}
              />
              <span>
                {t("onboarding.equipment.dietToggle")}
                <span className={styles["hint"]} style={{ display: "block" }}>
                  {t("onboarding.equipment.dietHint")}
                </span>
              </span>
            </label>
          </fieldset>
        )}

        {formError !== null && (
          <p role="alert" className={styles["error"]}>
            {formError}
          </p>
        )}

        <div className={styles["actions"]}>
          {step > 0 && (
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setStep(step - 1);
                setErrors({});
              }}
            >
              {t("onboarding.actions.back")}
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={busy || (step === 2 && PARQ_KEYS.some((key) => parq[key] === undefined))}>
            {busy ? t("onboarding.actions.saving") : step === TOTAL_STEPS - 1 ? t("onboarding.actions.finish") : t("onboarding.actions.next")}
          </Button>
        </div>
      </form>
    </section>
  );
}

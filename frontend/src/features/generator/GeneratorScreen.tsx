import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Chip, ChoiceCard, Slider, TextField, useToast } from "../../components/ui";
import {
  EMPHASES,
  EQUIPMENT_CODES,
  EXPERIENCES,
  GOALS,
  MUSCLE_CODES,
  PATTERN_CODES,
  PRESETS,
  SEXES,
  WEEKDAYS,
  type Emphasis,
  type EquipmentCode,
  type EquipmentPreset,
  type Experience,
  type Goal,
  type MovementPattern,
  type MuscleCode,
  type Sex,
  type Weekday,
} from "../shared/enums";
import { randomSeed } from "../shared/format";
import styles from "./Generator.module.css";
import { PreviewPanel } from "./PreviewPanel";
import {
  usePreviewProgram,
  useProfile,
  useSaveProgram,
  type GeneratorInput,
  type GeneratorPreview,
} from "./useGenerator";

const STEP_KEYS = ["goal", "days", "sex", "setup", "emphasis", "preview"] as const;
const LAST_STEP = STEP_KEYS.length - 1;

/** Énfasis que preselecciona el sexo (`specs/sex-modifiers.yaml`, §7.4); solo preselección editable. */
function emphasisForSex(sex: Sex): Emphasis {
  return sex === "female" ? "lower_glutes" : "balanced";
}

function toggle<T>(list: readonly T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

/**
 * Wizard del generador (§10.2.3): objetivo → días → sexo (preseleccionado del perfil, con
 * explicación) → nivel/duración/equipamiento → énfasis/limitaciones → vista previa → guardar.
 */
export function GeneratorScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { push } = useToast();
  const profile = useProfile();
  const previewMutation = usePreviewProgram();
  const saveMutation = useSaveProgram();

  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<Goal>("hypertrophy");
  const [days, setDays] = useState(3);
  const [preferredDays, setPreferredDays] = useState<readonly Weekday[]>([]);
  const [sex, setSex] = useState<Sex>("unspecified");
  const [experience, setExperience] = useState<Experience>("beginner");
  const [minutes, setMinutes] = useState(60);
  const [preset, setPreset] = useState<EquipmentPreset>("full_gym");
  const [items, setItems] = useState<readonly EquipmentCode[]>([]);
  const [emphasis, setEmphasis] = useState<Emphasis>("balanced");
  const [emphasisTouched, setEmphasisTouched] = useState(false);
  const [avoidMuscles, setAvoidMuscles] = useState<readonly MuscleCode[]>([]);
  const [avoidPatterns, setAvoidPatterns] = useState<readonly MovementPattern[]>([]);
  const [preview, setPreview] = useState<GeneratorPreview | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [prefilled, setPrefilled] = useState(false);

  // Preselección desde el perfil (una sola vez): sexo, nivel, equipamiento y limitaciones.
  const profileData = profile.data;
  useEffect(() => {
    if (prefilled || profileData === undefined) return;
    setSex(profileData.sex);
    setExperience(profileData.experience);
    setPreset(profileData.equipment.preset);
    setItems(profileData.equipment.items);
    setAvoidMuscles(profileData.limitations.avoid_muscles);
    setAvoidPatterns(profileData.limitations.avoid_patterns);
    setEmphasis(emphasisForSex(profileData.sex));
    setPrefilled(true);
  }, [profileData, prefilled]);

  const changeSex = (value: Sex): void => {
    setSex(value);
    if (!emphasisTouched) setEmphasis(emphasisForSex(value));
  };

  const buildInput = (seed: number | null): GeneratorInput => ({
    goal,
    days_per_week: days,
    sex,
    experience,
    session_minutes: minutes,
    equipment: { preset, items: preset === "custom" ? [...items] : [] },
    emphasis,
    avoid_muscles: [...avoidMuscles],
    avoid_patterns: [...avoidPatterns],
    preferred_days: [...preferredDays],
    weeks: 5,
    include_warmup: null,
    include_cooldown: null,
    include_cardio_finisher: null,
    favorite_exercise_ids: [],
    excluded_exercise_ids: [],
    seed,
  });

  const generate = (seed: number | null): void => {
    setError(null);
    previewMutation.mutate(
      { input: buildInput(seed) },
      {
        onSuccess: (result) => {
          setPreview(result);
          setName(t("generator.defaultName", { goal: t(`enums.goal.${goal}`), days }));
        },
        onError: () => {
          setError(t("generator.error"));
        },
      },
    );
  };

  const validateStep = (): string | null => {
    if (step === 1 && preferredDays.length > 0 && preferredDays.length !== days) {
      return t("generator.days.preferredMismatch", { count: days });
    }
    if (step === 3 && preset === "custom" && items.length === 0) {
      return t("generator.setup.itemsRequired");
    }
    return null;
  };

  const next = (): void => {
    const problem = validateStep();
    setError(problem);
    if (problem !== null) return;
    if (step === LAST_STEP - 1) {
      setStep(LAST_STEP);
      generate(null);
    } else {
      setStep(step + 1);
    }
  };

  const save = (activate: boolean): void => {
    if (preview === null) return;
    saveMutation.mutate(
      { name: name.trim() === "" ? t("generator.defaultName", { goal: t(`enums.goal.${goal}`), days }) : name.trim(), plan: preview.plan, activate },
      {
        onSuccess: () => {
          push({ title: t(activate ? "generator.savedActive" : "generator.saved"), tone: "success" });
          void navigate({ to: "/rutinas" });
        },
        onError: () => {
          setError(t("generator.saveError"));
        },
      },
    );
  };

  const stepKey = STEP_KEYS[step] ?? "goal";

  return (
    <section aria-labelledby="generator-title" className={styles["root"]}>
      <h1 id="generator-title">{t("generator.title")}</h1>
      <p aria-live="polite" className={styles["progress"]}>
        {t("generator.stepOf", { current: step + 1, total: STEP_KEYS.length })} · {t(`generator.steps.${stepKey}`)}
      </p>
      <progress className={styles["bar"]} max={STEP_KEYS.length} value={step + 1} aria-label={t("generator.title")} />

      {step === 0 && (
        <fieldset className={styles["step"]}>
          <legend>{t("generator.goal.heading")}</legend>
          <div className={styles["cards"]}>
            {GOALS.map((value) => (
              <ChoiceCard
                key={value}
                selected={goal === value}
                title={t(`enums.goal.${value}`)}
                description={t(`enums.goalHint.${value}`)}
                onSelect={() => {
                  setGoal(value);
                }}
              />
            ))}
          </div>
        </fieldset>
      )}

      {step === 1 && (
        <fieldset className={styles["step"]}>
          <legend>{t("generator.days.heading")}</legend>
          <Slider
            label={t("generator.days.perWeek")}
            value={days}
            min={1}
            max={7}
            valueText={t("generator.days.count", { count: days })}
            onValueChange={setDays}
          />
          {days === 7 && <p className={styles["hint"]}>{t("generator.days.sevenNote")}</p>}
          <p className={styles["label"]}>{t("generator.days.preferred")}</p>
          <div className={styles["chips"]} role="group" aria-label={t("generator.days.preferred")}>
            {WEEKDAYS.map((day) => (
              <Chip
                key={day}
                selected={preferredDays.includes(day)}
                onSelectedChange={() => {
                  setPreferredDays((current) => toggle(current, day));
                }}
              >
                {t(`enums.weekday.${day}`)}
              </Chip>
            ))}
          </div>
          <p className={styles["hint"]}>{t("generator.days.preferredHint")}</p>
        </fieldset>
      )}

      {step === 2 && (
        <fieldset className={styles["step"]}>
          <legend>{t("generator.sex.heading")}</legend>
          <div className={styles["chips"]} role="group" aria-label={t("generator.sex.heading")}>
            {SEXES.map((value) => (
              <Chip
                key={value}
                selected={sex === value}
                onSelectedChange={() => {
                  changeSex(value);
                }}
              >
                {t(`enums.sex.${value}`)}
              </Chip>
            ))}
          </div>
          <div role="note" className={styles["explain"]}>
            <p>
              {sex === profileData?.sex
                ? t("generator.sex.fromProfile")
                : t("generator.sex.changed")}
            </p>
            <p>{t(`generator.sex.explain.${sex}`, { emphasis: t(`enums.emphasis.${emphasisForSex(sex)}`) })}</p>
            <p>{t("generator.sex.never")}</p>
          </div>
        </fieldset>
      )}

      {step === 3 && (
        <fieldset className={styles["step"]}>
          <legend>{t("generator.setup.heading")}</legend>
          <p className={styles["label"]}>{t("generator.setup.level")}</p>
          <div className={styles["chips"]} role="group" aria-label={t("generator.setup.level")}>
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
          {profileData?.parq_flagged === true && <p className={styles["hint"]}>{t("generator.setup.parqNote")}</p>}
          <Slider
            label={t("generator.setup.duration")}
            value={minutes}
            min={20}
            max={120}
            step={5}
            valueText={t("generator.preview.minutes", { count: minutes })}
            onValueChange={setMinutes}
          />
          <p className={styles["label"]}>{t("generator.setup.equipment")}</p>
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
            <div className={styles["chips"]} role="group" aria-label={t("generator.setup.items")}>
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
          )}
        </fieldset>
      )}

      {step === 4 && (
        <fieldset className={styles["step"]}>
          <legend>{t("generator.emphasis.heading")}</legend>
          <div className={styles["chips"]} role="group" aria-label={t("generator.emphasis.heading")}>
            {EMPHASES.map((value) => (
              <Chip
                key={value}
                selected={emphasis === value}
                onSelectedChange={() => {
                  setEmphasis(value);
                  setEmphasisTouched(true);
                }}
              >
                {t(`enums.emphasis.${value}`)}
              </Chip>
            ))}
          </div>
          <p className={styles["label"]}>{t("generator.emphasis.avoidMuscles")}</p>
          <div className={styles["chips"]} role="group" aria-label={t("generator.emphasis.avoidMuscles")}>
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
          <p className={styles["label"]}>{t("generator.emphasis.avoidPatterns")}</p>
          <div className={styles["chips"]} role="group" aria-label={t("generator.emphasis.avoidPatterns")}>
            {PATTERN_CODES.filter((code) => code !== "cardio" && code !== "mobility" && code !== "other").map((code) => (
              <Chip
                key={code}
                selected={avoidPatterns.includes(code)}
                onSelectedChange={() => {
                  setAvoidPatterns((current) => toggle(current, code));
                }}
              >
                {t(`enums.pattern.${code}`)}
              </Chip>
            ))}
          </div>
        </fieldset>
      )}

      {step === LAST_STEP && (
        <div className={styles["step"]}>
          {previewMutation.isPending && preview === null && <p role="status">{t("generator.generating")}</p>}
          {preview !== null && (
            <>
              <PreviewPanel preview={preview} onChange={setPreview} />
              <div className={styles["saveBar"]}>
                <TextField
                  label={t("generator.programName")}
                  value={name}
                  maxLength={80}
                  onChange={(event) => {
                    setName(event.target.value);
                  }}
                />
                <div className={styles["actions"]}>
                  <Button
                    disabled={previewMutation.isPending}
                    onClick={() => {
                      generate(randomSeed());
                    }}
                  >
                    {t("generator.regenerate")}
                  </Button>
                  <Button
                    disabled={saveMutation.isPending}
                    onClick={() => {
                      save(false);
                    }}
                  >
                    {t("generator.save")}
                  </Button>
                  <Button
                    variant="primary"
                    disabled={saveMutation.isPending}
                    onClick={() => {
                      save(true);
                    }}
                  >
                    {t("generator.saveActivate")}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {error !== null && (
        <p role="alert" className={styles["error"]}>
          {error}
        </p>
      )}

      <div className={styles["actions"]}>
        {step > 0 && (
          <Button
            variant="ghost"
            onClick={() => {
              setError(null);
              setStep(step - 1);
            }}
          >
            {t("generator.back")}
          </Button>
        )}
        {step < LAST_STEP && (
          <Button variant="primary" onClick={next}>
            {step === LAST_STEP - 1 ? t("generator.preview.generate") : t("generator.next")}
          </Button>
        )}
      </div>
    </section>
  );
}

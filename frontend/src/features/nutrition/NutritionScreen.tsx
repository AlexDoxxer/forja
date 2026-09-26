import { useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import type { components } from "../../lib/api/schema";
import shared from "../shared/ui.module.css";
import { PlanView } from "./PlanView";
import {
  mondayOf,
  useGeneratePlan,
  useNutritionSettings,
  usePlan,
  usePlanList,
  useRecalculateTarget,
  useSaveSettings,
} from "./queries";
import { ShoppingList } from "./ShoppingList";
import { TargetRings } from "./TargetRings";
import styles from "./nutrition.module.css";
import "./strings";

type Schemas = components["schemas"];
type Fields = Schemas["NutritionSettingsFields"];

const GOALS: Schemas["NutritionGoal"][] = ["lose", "maintain", "gain", "recomp"];
const PACES: Schemas["NutritionPace"][] = ["gentle", "standard"];
const DIETS: Schemas["DietType"][] = ["omnivore", "pescatarian", "vegetarian", "vegan"];
const ALLERGENS: Schemas["Allergen"][] = [
  "gluten",
  "lactose",
  "tree_nuts",
  "egg",
  "fish",
  "shellfish",
  "soy",
  "peanuts",
];

function toFields(s: Schemas["NutritionSettings"]): Fields {
  return {
    diet_enabled: s.diet_enabled,
    goal: s.goal,
    pace: s.pace,
    diet_type: s.diet_type,
    meals_per_day: s.meals_per_day,
    allergens: s.allergens,
    excluded_food_ids: s.excluded_food_ids,
    disliked_food_ids: s.disliked_food_ids,
    pregnant: s.pregnant,
    breastfeeding: s.breastfeeding,
  };
}

function SafetyNotice(): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <aside className={shared["notice"]} role="note" aria-label={t("nutrition.safetyTitle")}>
      <strong>{t("nutrition.safetyTitle")}. </strong>
      {t("nutrition.safetyBody")}
    </aside>
  );
}

function SettingsForm({ settings }: { settings: Schemas["NutritionSettings"] }): React.JSX.Element {
  const { t } = useTranslation();
  const save = useSaveSettings();
  const [form, setForm] = useState<Fields>(() => toFields(settings));
  const set = <K extends keyof Fields>(key: K, value: Fields[K]): void => {
    setForm((f) => ({ ...f, [key]: value }));
  };
  return (
    <form
      className={shared["stack"]}
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate(form);
      }}
    >
      <div className={shared["grid"]}>
        <label className={shared["field"]}>
          {t("nutrition.goal")}
          <select value={form.goal} onChange={(e) => { set("goal", e.target.value as Fields["goal"]); }}>
            {GOALS.map((g) => (
              <option key={g} value={g}>{t(`nutrition.goal_${g}`)}</option>
            ))}
          </select>
        </label>
        <label className={shared["field"]}>
          {t("nutrition.pace")}
          <select value={form.pace} onChange={(e) => { set("pace", e.target.value as Fields["pace"]); }}>
            {PACES.map((p) => (
              <option key={p} value={p}>{t(`nutrition.pace_${p}`)}</option>
            ))}
          </select>
        </label>
        <label className={shared["field"]}>
          {t("nutrition.dietType")}
          <select value={form.diet_type} onChange={(e) => { set("diet_type", e.target.value as Fields["diet_type"]); }}>
            {DIETS.map((d) => (
              <option key={d} value={d}>{t(`nutrition.diet_${d}`)}</option>
            ))}
          </select>
        </label>
        <label className={shared["field"]}>
          {t("nutrition.mealsPerDay")}
          <select value={form.meals_per_day} onChange={(e) => { set("meals_per_day", Number(e.target.value)); }}>
            {[3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
      </div>
      <fieldset className={styles["allergens"]}>
        <legend>{t("nutrition.allergens")}</legend>
        {ALLERGENS.map((a) => (
          <label key={a} className={styles["checkRow"]}>
            <input
              type="checkbox"
              checked={form.allergens.includes(a)}
              onChange={(e) => {
                set("allergens", e.target.checked ? [...form.allergens, a] : form.allergens.filter((x) => x !== a));
              }}
            />
            {t(`nutrition.allergen_${a}`)}
          </label>
        ))}
      </fieldset>
      <label className={styles["checkRow"]}>
        <input type="checkbox" checked={form.pregnant} onChange={(e) => { set("pregnant", e.target.checked); }} />
        {t("nutrition.pregnant")}
      </label>
      <label className={styles["checkRow"]}>
        <input type="checkbox" checked={form.breastfeeding} onChange={(e) => { set("breastfeeding", e.target.checked); }} />
        {t("nutrition.breastfeeding")}
      </label>
      <div className={shared["row"]}>
        <button type="submit" className={shared["btn"]} disabled={save.isPending}>
          {t("nutrition.saveSettings")}
        </button>
      </div>
      {save.isSuccess && <p role="status">{t("nutrition.saved")}</p>}
      {save.isError && <p role="alert">{t("nutrition.settingsError")}</p>}
    </form>
  );
}

function PlanSection({ blocked }: { blocked: boolean }): React.JSX.Element {
  const { t } = useTranslation();
  const plans = usePlanList(true);
  const generate = useGeneratePlan();
  const [chosen, setChosen] = useState<string | null>(null);
  const planId = chosen ?? plans.data?.items[0]?.id ?? null;
  const plan = usePlan(planId);

  return (
    <section className={shared["card"]} aria-labelledby="plan-title">
      <h2 id="plan-title">{t("nutrition.planTitle")}</h2>
      <div className={shared["stack"]}>
        {!blocked && (
          <button
            type="button"
            className={shared["btn"]}
            disabled={generate.isPending}
            onClick={() => {
              generate.mutate(mondayOf(new Date()), { onSuccess: (data) => { setChosen(data.id); } });
            }}
          >
            {generate.isPending ? t("nutrition.generating") : t("nutrition.generate")}
          </button>
        )}
        {generate.isError && <p role="alert">{t("nutrition.generateError")}</p>}
        {plan.data ? (
          <PlanView resource={plan.data} />
        ) : (
          !plans.isLoading && <p className={shared["muted"]}>{t("nutrition.noPlan")}</p>
        )}
      </div>
      {plan.data && <ShoppingList planId={plan.data.id} />}
    </section>
  );
}

/** Pantalla «Nutrición» (MASTER_PROMPT §10.2.9). Solo se muestra si la dieta está activada. */
export function NutritionScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const settings = useNutritionSettings();
  const save = useSaveSettings();
  const recalc = useRecalculateTarget();
  const data = settings.data;
  const target = data?.current_target?.target ?? null;
  const usable = data?.feature_available === true && data.diet_enabled;

  return (
    <section aria-labelledby="nutrition-title" className={shared["page"]}>
      <h1 id="nutrition-title">{t("nutrition.title")}</h1>
      <SafetyNotice />
      <QueryState
        isLoading={settings.isLoading}
        isError={settings.isError}
        loadingLabel={t("nutrition.loading")}
        errorLabel={t("nutrition.error")}
      >
        {data?.feature_available === false && <p role="status">{t("nutrition.unavailable")}</p>}
        {data?.feature_available === true && !data.diet_enabled && (
          <div className={shared["stack"]}>
            <p>{t("nutrition.disabled")}</p>
            <button
              type="button"
              className={shared["btn"]}
              disabled={save.isPending}
              onClick={() => {
                save.mutate({ ...toFields(data), diet_enabled: true });
              }}
            >
              {t("nutrition.enable")}
            </button>
          </div>
        )}
        {usable && (
          <>
            <section className={shared["card"]} aria-labelledby="target-title">
              <h2 id="target-title">{t("nutrition.targetTitle")}</h2>
              {target === null ? (
                <p className={shared["muted"]}>{t("nutrition.noTarget")}</p>
              ) : target.blocked && target.block !== null ? (
                <div className={shared["notice"]} role="note">
                  <strong>{t("nutrition.blockedTitle")}. </strong>
                  {target.block.message_es}
                </div>
              ) : (
                <TargetRings target={target} />
              )}
              {target !== null && target.notices.length > 0 && (
                <ul className={shared["list"]}>
                  {target.notices.map((n) => (
                    <li key={n.code} className={shared["notice"]}>
                      {n.message_es}
                    </li>
                  ))}
                </ul>
              )}
              <div className={shared["row"]}>
                <button type="button" className={shared["btn"]} disabled={recalc.isPending} onClick={() => { recalc.mutate(); }}>
                  {t("nutrition.recalc")}
                </button>
              </div>
            </section>
            <PlanSection blocked={target?.blocked ?? false} />
            <section className={shared["card"]} aria-labelledby="nsettings-title">
              <h2 id="nsettings-title">{t("nutrition.settingsTitle")}</h2>
              <SettingsForm settings={data} />
            </section>
          </>
        )}
      </QueryState>
    </section>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../../lib/api/schema";
import { formatDate, formatNumber } from "../shared/format";
import shared from "../shared/ui.module.css";
import { useFoodSearch, useSwapFood } from "./queries";
import styles from "./nutrition.module.css";
import "./strings";

type Schemas = components["schemas"];

interface SwapPanelProps {
  planId: string;
  dayIndex: number;
  meal: Schemas["MealSlot"];
  item: Schemas["MealItem"];
  onClose: () => void;
}

function SwapPanel({ planId, dayIndex, meal, item, onClose }: SwapPanelProps): React.JSX.Element {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const swap = useSwapFood(planId);
  const foods = useFoodSearch(query, query.trim().length >= 2);
  const run = (replacement: string | null): void => {
    swap.mutate(
      { day_index: dayIndex, meal, food_id: item.food_id, replacement_food_id: replacement },
      { onSuccess: onClose },
    );
  };
  return (
    <div className={shared["card"]} role="group" aria-label={t("nutrition.swapTitle")}>
      <h4>{t("nutrition.swapTitle")}</h4>
      <div className={shared["stack"]}>
        <button type="button" className={shared["btn"]} onClick={() => { run(null); }} disabled={swap.isPending}>
          {t("nutrition.swapAuto")}
        </button>
        <label className={shared["field"]}>
          {t("nutrition.swapSearch")}
          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
          />
        </label>
        <ul className={shared["list"]}>
          {foods.data?.items.map((food) => (
            <li key={food.id}>
              <button type="button" className={shared["btn"]} onClick={() => { run(food.id); }} disabled={swap.isPending}>
                {t("nutrition.swapUse", { name: food.name_es })}
              </button>
            </li>
          ))}
        </ul>
        {swap.isError && <p role="alert">{t("nutrition.swapError")}</p>}
        <button type="button" className={shared["btn"]} onClick={onClose}>
          {t("nutrition.swapCancel")}
        </button>
      </div>
    </div>
  );
}

/** Plan semanal por días y comidas, con intercambio de alimentos. */
export function PlanView({ resource }: { resource: Schemas["MealPlanResource"] }): React.JSX.Element {
  const { t } = useTranslation();
  const plan = resource.plan;
  const [dayIdx, setDayIdx] = useState(0);
  const [swapping, setSwapping] = useState<string | null>(null);
  const day = plan.days[Math.min(dayIdx, plan.days.length - 1)];
  const notices = plan.notices.filter((n) => n.code !== "health_disclaimer");

  return (
    <div className={shared["stack"]}>
      <div className={styles["dayTabs"]} role="group" aria-label={t("nutrition.planTitle")}>
        {plan.days.map((d, i) => (
          <button
            key={d.date}
            type="button"
            className={styles["dayTab"]}
            aria-pressed={i === dayIdx}
            title={formatDate(d.date, { weekday: "long", day: "numeric", month: "long" })}
            onClick={() => {
              setDayIdx(i);
              setSwapping(null);
            }}
          >
            {t("nutrition.day", { n: d.day_index + 1 })}
          </button>
        ))}
      </div>
      {day !== undefined && (
        <div className={shared["stack"]}>
          <p>
            <strong>{formatDate(day.date, { weekday: "long", day: "numeric", month: "long" })}</strong>
          </p>
          {day.meals.map((meal) => (
            <section key={meal.slot} className={styles["meal"]} aria-label={t(`nutrition.slot_${meal.slot}`)}>
              <h3>{t(`nutrition.slot_${meal.slot}`)}</h3>
              <ul className={styles["items"]}>
                {meal.items.map((item) => {
                  const id = `${String(day.day_index)}:${meal.slot}:${item.food_id}`;
                  return (
                    <li key={id}>
                      <div className={styles["item"]}>
                        <span>
                          {t("nutrition.item", {
                            name: item.name_es,
                            grams: formatNumber(item.grams, 0),
                            kcal: formatNumber(item.nutrients.kcal, 0),
                          })}
                        </span>
                        <button
                          type="button"
                          className={shared["btn"]}
                          aria-label={t("nutrition.swap", { name: item.name_es })}
                          onClick={() => {
                            setSwapping(id);
                          }}
                        >
                          ⇄
                        </button>
                      </div>
                      {swapping === id && (
                        <SwapPanel
                          planId={resource.id}
                          dayIndex={day.day_index}
                          meal={meal.slot}
                          item={item}
                          onClose={() => {
                            setSwapping(null);
                          }}
                        />
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
          <p className={shared["muted"]}>
            {t("nutrition.dayTotals", {
              kcal: formatNumber(day.totals.kcal, 0),
              protein: formatNumber(day.totals.protein_g, 0),
              fat: formatNumber(day.totals.fat_g, 0),
              carbs: formatNumber(day.totals.carbs_g, 0),
            })}
          </p>
          <p className={shared["muted"]}>{t("nutrition.deviation", { kcal: formatNumber(day.deviation.kcal, 0) })}</p>
        </div>
      )}
      {notices.length > 0 && (
        <aside className={shared["notice"]} aria-label={t("nutrition.notices")}>
          <strong>{t("nutrition.notices")}</strong>
          <ul className={shared["list"]}>
            {notices.map((n) => (
              <li key={n.code}>
                {n.code === "tolerance_not_met" ? t("nutrition.notice_tolerance_not_met") : n.message_es}
              </li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  );
}

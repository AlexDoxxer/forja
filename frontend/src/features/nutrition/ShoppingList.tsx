import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatNumber } from "../shared/format";
import shared from "../shared/ui.module.css";
import { getMeta, setMeta } from "../session/storage";
import { useShoppingList } from "./queries";
import styles from "./nutrition.module.css";
import "./strings";

/** Lista de la compra marcable; lo marcado se guarda en IndexedDB para seguir en la tienda sin red. */
export function ShoppingList({ planId }: { planId: string }): React.JSX.Element {
  const { t } = useTranslation();
  const list = useShoppingList(planId);
  const [checked, setChecked] = useState<string[]>([]);
  const key = `shopping:${planId}`;

  useEffect(() => {
    let alive = true;
    void getMeta<string[]>(key).then((saved) => {
      if (alive) setChecked(saved ?? []);
    });
    return () => {
      alive = false;
    };
  }, [key]);

  const toggle = (foodId: string): void => {
    const next = checked.includes(foodId) ? checked.filter((id) => id !== foodId) : [...checked, foodId];
    setChecked(next);
    void setMeta(key, next);
  };

  return (
    <section className={shared["card"]} aria-labelledby="shop-title">
      <h2 id="shop-title">{t("nutrition.shoppingTitle")}</h2>
      {list.data?.categories.length === 0 && <p className={shared["muted"]}>{t("nutrition.shoppingEmpty")}</p>}
      {list.data?.categories.map((category) => (
        <div key={category.category}>
          <h3>{category.label_es}</h3>
          <ul className={shared["list"]}>
            {category.items.map((item) => {
              const done = checked.includes(item.food_id);
              return (
                <li key={item.food_id}>
                  <label className={styles["checkRow"]}>
                    <input
                      type="checkbox"
                      checked={done}
                      aria-label={t("nutrition.shoppingChecked", { name: item.name_es })}
                      onChange={() => {
                        toggle(item.food_id);
                      }}
                    />
                    <span className={done ? styles["checked"] : undefined}>
                      {t("nutrition.shoppingItem", { name: item.name_es, grams: formatNumber(item.total_grams, 0) })}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </section>
  );
}

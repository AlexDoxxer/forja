import { Link } from "@tanstack/react-router";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ExerciseMedia } from "../../components/ExerciseMedia";
import { Chip } from "../../components/ui";
import {
  BODY_PARTS,
  DIFFICULTIES,
  EQUIPMENT_CODES,
  foldText,
  PATTERN_CODES,
  type MuscleCode,
} from "../shared/enums";
import {
  EMPTY_FILTERS,
  flattenPages,
  useCatalogFacets,
  useExerciseSearch,
  type ExerciseSummary,
  type LibraryFilters,
} from "./useCatalog";
import styles from "./Library.module.css";
import { MuscleMap } from "./MuscleMap";

const CARD_MIN_WIDTH = 200;
const ROW_HEIGHT = 300;
const GAP = 16;

function toggleValue<T>(list: readonly T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function ExerciseCard({ exercise }: { exercise: ExerciseSummary }): React.JSX.Element {
  const { t } = useTranslation();
  const [previewing, setPreviewing] = useState(false);
  return (
    // La vista previa animada es una mejora al pasar el cursor; su equivalente accesible es el foco
    // del enlace del nombre (onFocus/onBlur burbujean desde él), por lo que el <li> no es interactivo.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <li
      className={styles["card"]}
      onMouseEnter={() => {
        setPreviewing(true);
      }}
      onMouseLeave={() => {
        setPreviewing(false);
      }}
      onFocus={() => {
        setPreviewing(true);
      }}
      onBlur={() => {
        setPreviewing(false);
      }}
    >
      {/* Miniatura en el listado; el GIF solo al pasar el cursor o al enfocar con teclado (§10.1). */}
      <ExerciseMedia media={exercise.media} alt={exercise.name_es} variant={previewing ? "animated" : "thumbnail"} />
      <Link to="/biblioteca/$exerciseId" params={{ exerciseId: exercise.id }} className={styles["name"]}>
        {exercise.name_es}
        {exercise.variant_label_es !== null && ` (${exercise.variant_label_es})`}
      </Link>
      <span className={styles["meta"]}>
        {t(`enums.equipment.${exercise.equipment_code}`)} · {t(`enums.muscle.${exercise.target_muscle}`)}
      </span>
    </li>
  );
}

/**
 * Biblioteca (MASTER_PROMPT §10.2.7): búsqueda instantánea tolerante a acentos, chips de filtro,
 * mapa muscular clicable y cuadrícula virtualizada (`@tanstack/react-virtual`) con paginación por
 * cursor infinita, de modo que 1.324 ejercicios se renderizan en ventanas de unas pocas filas.
 */
export function LibraryScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<LibraryFilters>(EMPTY_FILTERS);
  const [text, setText] = useState("");

  // Debounce breve; la consulta se normaliza (sin acentos ni mayúsculas) antes de enviarse.
  useEffect(() => {
    const handle = window.setTimeout(() => {
      setFilters((current) => ({ ...current, q: foldText(text) }));
    }, 150);
    return () => {
      window.clearTimeout(handle);
    };
  }, [text]);

  const search = useExerciseSearch(filters);
  const facets = useCatalogFacets(filters);
  const items = useMemo(() => flattenPages(search.data), [search.data]);
  const total = facets.data?.total ?? items.length;

  const facetCount = (key: "body_part" | "equipment" | "pattern" | "difficulty", value: string): number | null =>
    facets.data?.[key].find((facet) => facet.value === value)?.count ?? null;

  const scrollRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = scrollRef.current;
    if (element === null) return;
    const measure = (): void => {
      setWidth(element.clientWidth);
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);
  const columns = Math.max(1, Math.floor((width + GAP) / (CARD_MIN_WIDTH + GAP)) || 2);
  const rowCount = Math.ceil(items.length / columns);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT + GAP,
    overscan: 3,
    initialRect: { width: 800, height: 600 },
  });
  const virtualRows = virtualizer.getVirtualItems();

  const { hasNextPage, isFetchingNextPage, fetchNextPage } = search;
  const lastVisible = virtualRows[virtualRows.length - 1]?.index ?? -1;
  useEffect(() => {
    if (lastVisible >= rowCount - 2 && hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [lastVisible, rowCount, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const activeCount =
    filters.body_part.length +
    filters.muscle.length +
    filters.equipment.length +
    filters.pattern.length +
    filters.difficulty.length +
    (filters.favorites ? 1 : 0);

  return (
    <section aria-labelledby="library-title" className={styles["root"]}>
      <h1 id="library-title">{t("library.title")}</h1>

      <div className={styles["toolbar"]}>
        <label className={styles["searchLabel"]}>
          <span className={styles["visuallyHidden"]}>{t("library.search")}</span>
          <input
            type="search"
            className={styles["search"]}
            placeholder={t("library.searchPlaceholder")}
            value={text}
            onChange={(event) => {
              setText(event.target.value);
            }}
          />
        </label>
        <Chip
          selected={filters.favorites}
          onSelectedChange={(selected) => {
            setFilters((current) => ({ ...current, favorites: selected }));
          }}
        >
          {t("library.favorites")}
        </Chip>
        {activeCount > 0 && (
          <button
            type="button"
            className={styles["clear"]}
            onClick={() => {
              setFilters((current) => ({ ...EMPTY_FILTERS, q: current.q }));
            }}
          >
            {t("library.clearFilters", { count: activeCount })}
          </button>
        )}
      </div>

      <div className={styles["layout"]}>
        <aside className={styles["filters"]} aria-label={t("library.filters")}>
          <details open>
            <summary>{t("library.map.title")}</summary>
            <MuscleMap
              selected={filters.muscle}
              onToggle={(muscle: MuscleCode) => {
                setFilters((current) => ({ ...current, muscle: toggleValue(current.muscle, muscle) }));
              }}
            />
            {filters.muscle.length > 0 && (
              <p className={styles["selectedMuscles"]} aria-live="polite">
                {t("library.map.selected")}: {filters.muscle.map((muscle) => t(`enums.muscle.${muscle}`)).join(", ")}
              </p>
            )}
          </details>
          <details>
            <summary>{t("library.bodyPart")}</summary>
            <div className={styles["chips"]}>
              {BODY_PARTS.map((value) => (
                <Chip
                  key={value}
                  selected={filters.body_part.includes(value)}
                  onSelectedChange={() => {
                    setFilters((current) => ({ ...current, body_part: toggleValue(current.body_part, value) }));
                  }}
                >
                  {t(`enums.bodyPart.${value}`)} {facetCount("body_part", value) ?? ""}
                </Chip>
              ))}
            </div>
          </details>
          <details>
            <summary>{t("library.equipment")}</summary>
            <div className={styles["chips"]}>
              {EQUIPMENT_CODES.map((value) => (
                <Chip
                  key={value}
                  selected={filters.equipment.includes(value)}
                  onSelectedChange={() => {
                    setFilters((current) => ({ ...current, equipment: toggleValue(current.equipment, value) }));
                  }}
                >
                  {t(`enums.equipment.${value}`)}
                </Chip>
              ))}
            </div>
          </details>
          <details>
            <summary>{t("library.pattern")}</summary>
            <div className={styles["chips"]}>
              {PATTERN_CODES.map((value) => (
                <Chip
                  key={value}
                  selected={filters.pattern.includes(value)}
                  onSelectedChange={() => {
                    setFilters((current) => ({ ...current, pattern: toggleValue(current.pattern, value) }));
                  }}
                >
                  {t(`enums.pattern.${value}`)}
                </Chip>
              ))}
            </div>
          </details>
          <details>
            <summary>{t("library.difficulty")}</summary>
            <div className={styles["chips"]}>
              {DIFFICULTIES.map((value) => (
                <Chip
                  key={value}
                  selected={filters.difficulty.includes(value)}
                  onSelectedChange={() => {
                    setFilters((current) => ({ ...current, difficulty: toggleValue(current.difficulty, value) }));
                  }}
                >
                  {t(`enums.difficulty.${String(value)}`)} {facetCount("difficulty", String(value)) ?? ""}
                </Chip>
              ))}
            </div>
          </details>
        </aside>

        <div className={styles["results"]}>
          <p role="status" aria-live="polite" className={styles["count"]}>
            {search.isLoading
              ? t("library.loading")
              : search.isError
                ? t("library.error")
                : t("library.resultCount", { count: total })}
          </p>
          {/* Región desplazable enfocable: permite recorrerla con el teclado (WCAG 2.1.1). */}
          {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
          <div ref={scrollRef} className={styles["scroller"]} tabIndex={0} aria-label={t("library.gridLabel")} role="region">
            <ul className={styles["grid"]} style={{ height: virtualizer.getTotalSize() }}>
              {virtualRows.map((row) => {
                const start = row.index * columns;
                const rowItems = items.slice(start, start + columns);
                return (
                  <li
                    key={row.key}
                    className={styles["row"]}
                    style={{ transform: `translateY(${String(row.start)}px)`, height: ROW_HEIGHT }}
                  >
                    <ul className={styles["rowList"]} style={{ gridTemplateColumns: `repeat(${String(columns)}, minmax(0, 1fr))` }}>
                      {rowItems.map((exercise) => (
                        <ExerciseCard key={exercise.id} exercise={exercise} />
                      ))}
                    </ul>
                  </li>
                );
              })}
            </ul>
            {isFetchingNextPage && <p role="status">{t("library.loadingMore")}</p>}
          </div>
          {!search.isLoading && items.length === 0 && !search.isError && (
            <p>{t("library.empty")}</p>
          )}
        </div>
      </div>
    </section>
  );
}

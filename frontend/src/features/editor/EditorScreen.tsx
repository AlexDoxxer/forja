import { useParams } from "@tanstack/react-router";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { QueryState } from "../../components/QueryState";
import { Button, Chip, CheckField, Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui";
import type { components } from "../../lib/api/schema";
import { BODY_PARTS, type BodyPart } from "../shared/enums";
import { EMPTY_FILTERS, flattenPages, useExerciseSearch } from "../library/useCatalog";
import { DayEditor } from "./DayEditor";
import styles from "./Editor.module.css";
import { dayHasErrors, editorReducer, initialEditorState, toDayEdit, type DayDraft } from "./editorState";
import { useProgram, useSaveDay, violationsOf, type PlanWarning, type ProgramDetail } from "./useEditor";

type ExerciseSummary = components["schemas"]["ExerciseSummary"];

/** Pausa tras la última edición antes de validar/guardar en el servidor (validación «en vivo»). */
export const AUTOSAVE_DELAY_MS = 700;

type SaveStatus = "idle" | "saving" | "saved" | "error";

export interface EditorScreenProps {
  /** Permite usar la pantalla sin parámetros de ruta (tests). */
  programId?: string;
}

/**
 * Editor de rutina (§10.2.4). Reordenación accesible con dnd-kit, superseries/circuitos, campos por
 * ejercicio con validación de forma en cliente y validación del motor en vivo (guardado diferido
 * de `PUT /programs/{id}/days/{day_id}`, que ejecuta `rebalance_after_edit` + `validate_plan`),
 * deshacer/rehacer y buscador lateral de ejercicios.
 */
export function EditorScreen({ programId }: EditorScreenProps): React.JSX.Element {
  const params: { programId?: string } = useParams({ strict: false });
  const id = programId ?? params.programId ?? "";
  const program = useProgram(id);
  const { t } = useTranslation();

  return (
    <section aria-labelledby="editor-title" className={styles["root"]}>
      <QueryState
        isLoading={program.isLoading}
        isError={program.isError}
        loadingLabel={t("editor.loading")}
        errorLabel={t("editor.error")}
      >
        {program.data && <EditorBody key={program.data.id} program={program.data} />}
      </QueryState>
    </section>
  );
}

function warningsForDay(warnings: readonly PlanWarning[], day: DayDraft): PlanWarning[] {
  return warnings.filter((warning) => warning.day_index === null || warning.day_index === day.index);
}

function EditorBody({ program }: { program: ProgramDetail }): React.JSX.Element {
  const { t } = useTranslation();
  const firstWeek = program.weeks[0];
  const [state, dispatch] = useReducer(editorReducer, firstWeek?.days ?? [], initialEditorState);
  const [applyToAll, setApplyToAll] = useState(true);
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [warnings, setWarnings] = useState<PlanWarning[]>(program.warnings);
  const [violations, setViolations] = useState<PlanWarning[]>([]);
  const [known, setKnown] = useState<ReadonlyMap<string, ExerciseSummary>>(
    () => new Map(program.exercises.map((exercise) => [exercise.id, exercise])),
  );
  const [activeDay, setActiveDay] = useState(state.days[0]?.key ?? "");
  const saveDay = useSaveDay(program.id);

  // Última versión guardada de cada día (JSON del cuerpo del PUT) para no repetir peticiones.
  const saved = useRef(new Map<string, string>());
  const initialised = useRef(false);
  if (!initialised.current) {
    for (const day of state.days) saved.current.set(day.key, JSON.stringify(toDayEdit(day, true)));
    initialised.current = true;
  }

  const stateRef = useRef(state);
  stateRef.current = state;
  const applyRef = useRef(applyToAll);
  applyRef.current = applyToAll;

  const flush = async (): Promise<void> => {
    const pending = stateRef.current.days.filter(
      (day) => !dayHasErrors(day) && saved.current.get(day.key) !== JSON.stringify(toDayEdit(day, applyRef.current)),
    );
    if (pending.length === 0) return;
    setStatus("saving");
    setViolations([]);
    try {
      let latest: ProgramDetail | null = null;
      for (const day of pending) {
        const edit = toDayEdit(day, applyRef.current);
        latest = await saveDay.mutateAsync({ dayId: day.dayId, edit });
        saved.current.set(day.key, JSON.stringify(edit));
      }
      if (latest !== null) {
        setWarnings(latest.warnings);
        const fresh = latest.exercises;
        setKnown((current) => new Map([...current, ...fresh.map((exercise): [string, ExerciseSummary] => [exercise.id, exercise])]));
      }
      setStatus("saved");
    } catch (error) {
      setViolations(violationsOf(error));
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.revision === 0) return;
    const handle = window.setTimeout(() => {
      void flush();
    }, AUTOSAVE_DELAY_MS);
    return () => {
      window.clearTimeout(handle);
    };
    // `flush` lee siempre el estado vigente desde refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.revision, applyToAll]);

  const current: DayDraft | undefined = state.days.find((day) => day.key === activeDay) ?? state.days[0];

  // Buscador lateral de ejercicios.
  const [query, setQuery] = useState("");
  const [bodyPart, setBodyPart] = useState<BodyPart | null>(null);
  const search = useExerciseSearch({
    ...EMPTY_FILTERS,
    q: query.trim(),
    body_part: bodyPart === null ? [] : [bodyPart],
  });
  const results = useMemo(() => flattenPages(search.data).slice(0, 30), [search.data]);

  const add = (exercise: ExerciseSummary): void => {
    if (current === undefined) return;
    setKnown((existing) => new Map(existing).set(exercise.id, exercise));
    dispatch({ type: "add", dayKey: current.key, exerciseId: exercise.id });
  };

  const statusText: Record<SaveStatus, string> = {
    idle: t("editor.status.idle"),
    saving: t("editor.status.saving"),
    saved: t("editor.status.saved"),
    error: t("editor.status.error"),
  };

  return (
    <>
      <div className={styles["topbar"]}>
        <h1 id="editor-title">{t("editor.title", { name: program.name })}</h1>
        <div className={styles["toolbar"]} role="toolbar" aria-label={t("editor.toolbar")}>
          <Button
            disabled={state.past.length === 0}
            onClick={() => {
              dispatch({ type: "undo" });
            }}
          >
            {t("editor.undo")}
          </Button>
          <Button
            disabled={state.future.length === 0}
            onClick={() => {
              dispatch({ type: "redo" });
            }}
          >
            {t("editor.redo")}
          </Button>
          <Button
            variant="primary"
            disabled={status === "saving"}
            onClick={() => {
              void flush();
            }}
          >
            {t("editor.saveNow")}
          </Button>
          <span role="status" aria-live="polite" className={styles["status"]}>
            {statusText[status]}
          </span>
        </div>
      </div>
      <CheckField
        label={t("editor.applyAll")}
        checked={applyToAll}
        onChange={(event) => {
          setApplyToAll(event.target.checked);
        }}
      />

      <div className={styles["layout"]}>
        <div>
          {current !== undefined && (
            <Tabs value={current.key} onValueChange={setActiveDay}>
              <TabsList aria-label={t("editor.days")}>
                {state.days.map((day) => (
                  <TabsTrigger key={day.key} value={day.key}>
                    {day.name}
                  </TabsTrigger>
                ))}
              </TabsList>
              {state.days.map((day) => (
                <TabsContent key={day.key} value={day.key}>
                  <DayEditor day={day} exercises={known} dispatch={dispatch} />
                  <div className={styles["feedback"]} aria-live="polite">
                    {dayHasErrors(day) && <p role="alert">{t("editor.localInvalid")}</p>}
                    {violations.length > 0 && (
                      <div role="alert" className={styles["violations"]}>
                        <h2>{t("editor.violations")}</h2>
                        <ul>
                          {violations.map((violation, index) => (
                            <li key={`${violation.code}-${String(index)}`}>{violation.message_es}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {warningsForDay(warnings, day).length > 0 && (
                      <div className={styles["warnings"]}>
                        <h2>{t("editor.warnings")}</h2>
                        <ul>
                          {warningsForDay(warnings, day).map((warning, index) => (
                            <li key={`${warning.code}-${String(index)}`}>{warning.message_es}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          )}
        </div>

        <aside className={styles["search"]} aria-label={t("editor.search.title")}>
          <h2>{t("editor.search.title")}</h2>
          <label className={styles["mini"]}>
            <span>{t("editor.search.label")}</span>
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
              }}
            />
          </label>
          <div className={styles["chips"]}>
            {BODY_PARTS.map((part) => (
              <Chip
                key={part}
                selected={bodyPart === part}
                onSelectedChange={(selected) => {
                  setBodyPart(selected ? part : null);
                }}
              >
                {t(`enums.bodyPart.${part}`)}
              </Chip>
            ))}
          </div>
          <ul className={styles["results"]}>
            {results.map((exercise) => (
              <li key={exercise.id}>
                <span>
                  {exercise.name_es}
                  <small> · {t(`enums.equipment.${exercise.equipment_code}`)}</small>
                </span>
                <Button
                  size="sm"
                  aria-label={t("editor.search.add", { name: exercise.name_es })}
                  onClick={() => {
                    add(exercise);
                  }}
                >
                  {t("editor.search.addShort")}
                </Button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </>
  );
}

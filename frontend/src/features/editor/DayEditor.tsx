import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type ScreenReaderInstructions,
} from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useState, type Dispatch } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui";
import { cx } from "../../lib/cx";
import type { components } from "../../lib/api/schema";
import styles from "./Editor.module.css";
import {
  validateExercise,
  type BlockDraft,
  type DayDraft,
  type EditorAction,
  type ExerciseDraft,
} from "./editorState";

type ExerciseSummary = components["schemas"]["ExerciseSummary"];

interface NumberFieldProps {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  error?: string | undefined;
  min?: number;
  max?: number;
  nullable?: boolean;
}

function NumberField({ label, value, onChange, error, min, max, nullable = false }: NumberFieldProps): React.JSX.Element {
  // Texto en edición: permite vaciar el campo mientras se teclea sin forzar un valor.
  const [draft, setDraft] = useState(value === null ? "" : String(value));
  useEffect(() => {
    setDraft((current) => (current !== "" && Number(current) === value ? current : value === null ? "" : String(value)));
  }, [value]);
  return (
    <label className={styles["mini"]}>
      <span>{label}</span>
      <input
        type="number"
        inputMode="numeric"
        value={draft}
        min={min}
        max={max}
        aria-invalid={error === undefined ? undefined : true}
        title={error}
        onChange={(event) => {
          const raw = event.target.value;
          setDraft(raw);
          if (raw === "") {
            if (nullable) onChange(null);
            return;
          }
          onChange(Number(raw));
        }}
        onBlur={() => {
          setDraft(value === null ? "" : String(value));
        }}
      />
      {error !== undefined && (
        <span role="alert" className={styles["fieldError"]}>
          {error}
        </span>
      )}
    </label>
  );
}

interface SortableExerciseProps {
  dayKey: string;
  exercise: ExerciseDraft;
  summary: ExerciseSummary | undefined;
  dispatch: Dispatch<EditorAction>;
}

function SortableExercise({ dayKey, exercise, summary, dispatch }: SortableExerciseProps): React.JSX.Element {
  const { t } = useTranslation();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: exercise.key });
  const errors = validateExercise(exercise);
  const name = summary?.name_es ?? exercise.exercise_id;
  const update = (patch: Partial<ExerciseDraft>): void => {
    dispatch({ type: "update", dayKey, exerciseKey: exercise.key, patch });
  };
  const err = (key: keyof typeof errors): string | undefined => {
    const message = errors[key];
    return message === undefined ? undefined : t(message);
  };
  const timed = exercise.duration_s !== null;

  return (
    <li
      ref={setNodeRef}
      className={cx(styles["exercise"], isDragging && styles["dragging"])}
      style={{ transform: CSS.Transform.toString(transform), transition }}
    >
      <div className={styles["exerciseHead"]}>
        <button
          type="button"
          className={styles["handle"]}
          aria-label={t("editor.drag", { name })}
          {...attributes}
          {...listeners}
        >
          ⠿
        </button>
        <strong className={styles["exerciseName"]}>{name}</strong>
        <Button
          size="sm"
          variant="ghost"
          aria-label={t("editor.moveUp", { name })}
          onClick={() => {
            dispatch({ type: "moveStep", dayKey, exerciseKey: exercise.key, delta: -1 });
          }}
        >
          ↑
        </Button>
        <Button
          size="sm"
          variant="ghost"
          aria-label={t("editor.moveDown", { name })}
          onClick={() => {
            dispatch({ type: "moveStep", dayKey, exerciseKey: exercise.key, delta: 1 });
          }}
        >
          ↓
        </Button>
        <Button
          size="sm"
          variant="danger"
          aria-label={t("editor.remove", { name })}
          onClick={() => {
            dispatch({ type: "remove", dayKey, exerciseKey: exercise.key });
          }}
        >
          ✕
        </Button>
      </div>
      <div className={styles["fields"]}>
        <NumberField label={t("editor.sets")} value={exercise.sets} min={1} max={10} error={err("sets")} onChange={(v) => { update({ sets: v ?? 1 }); }} />
        {timed ? (
          <NumberField label={t("editor.duration")} value={exercise.duration_s} min={5} max={3600} error={err("duration")} onChange={(v) => { update({ duration_s: v }); }} />
        ) : (
          <>
            <NumberField label={t("editor.repMin")} value={exercise.rep_min} min={1} max={100} nullable error={err("reps")} onChange={(v) => { update({ rep_min: v }); }} />
            <NumberField label={t("editor.repMax")} value={exercise.rep_max} min={1} max={100} nullable onChange={(v) => { update({ rep_max: v }); }} />
          </>
        )}
        <NumberField label="RIR" value={exercise.target_rir} min={0} max={5} nullable error={err("rir")} onChange={(v) => { update({ target_rir: v }); }} />
        <NumberField label={t("editor.rest")} value={exercise.rest_s} min={0} max={600} error={err("rest")} onChange={(v) => { update({ rest_s: v ?? 0 }); }} />
        <label className={styles["mini"]}>
          <span>{t("editor.tempo")}</span>
          <input
            type="text"
            value={exercise.tempo ?? ""}
            placeholder="3-0-1-0"
            aria-invalid={errors.tempo === undefined ? undefined : true}
            onChange={(event) => {
              update({ tempo: event.target.value === "" ? null : event.target.value });
            }}
          />
          {errors.tempo !== undefined && (
            <span role="alert" className={styles["fieldError"]}>
              {t(errors.tempo)}
            </span>
          )}
        </label>
        <label className={styles["mini"]}>
          <span>{t("editor.notes")}</span>
          <input
            type="text"
            value={exercise.notes_es ?? ""}
            maxLength={500}
            onChange={(event) => {
              update({ notes_es: event.target.value === "" ? null : event.target.value });
            }}
          />
        </label>
        <label className={styles["check"]}>
          <input
            type="checkbox"
            checked={exercise.per_side}
            onChange={(event) => {
              update({ per_side: event.target.checked });
            }}
          />
          {t("editor.perSide")}
        </label>
      </div>
    </li>
  );
}

interface BlockViewProps {
  day: DayDraft;
  block: BlockDraft;
  isLast: boolean;
  exercises: ReadonlyMap<string, ExerciseSummary>;
  dispatch: Dispatch<EditorAction>;
}

function BlockView({ day, block, isLast, exercises, dispatch }: BlockViewProps): React.JSX.Element {
  const { t } = useTranslation();
  const grouped = block.exercises.length > 1;
  return (
    <div className={styles["block"]} role="group" aria-label={t(`enums.blockKind.${block.kind}`)}>
      <div className={styles["blockHead"]}>
        <h2>{t(`enums.blockKind.${block.kind}`)}</h2>
        {grouped && (
          <>
            <NumberField
              label={t("editor.rounds")}
              value={block.rounds}
              min={1}
              max={10}
              onChange={(v) => {
                dispatch({ type: "block", dayKey: day.key, blockKey: block.key, patch: { rounds: v ?? 1 } });
              }}
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                dispatch({ type: "split", dayKey: day.key, blockKey: block.key });
              }}
            >
              {t("editor.split")}
            </Button>
          </>
        )}
        {!isLast && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              dispatch({ type: "mergeNext", dayKey: day.key, blockKey: block.key });
            }}
          >
            {t("editor.mergeNext")}
          </Button>
        )}
      </div>
      <SortableContext items={block.exercises.map((exercise) => exercise.key)} strategy={verticalListSortingStrategy}>
        <ul className={styles["list"]}>
          {block.exercises.map((exercise) => (
            <SortableExercise
              key={exercise.key}
              dayKey={day.key}
              exercise={exercise}
              summary={exercises.get(exercise.exercise_id)}
              dispatch={dispatch}
            />
          ))}
        </ul>
      </SortableContext>
    </div>
  );
}

export interface DayEditorProps {
  day: DayDraft;
  exercises: ReadonlyMap<string, ExerciseSummary>;
  dispatch: Dispatch<EditorAction>;
}

/** Un día del programa: bloques y ejercicios reordenables con dnd-kit (puntero y teclado). */
export function DayEditor({ day, exercises, dispatch }: DayEditorProps): React.JSX.Element {
  const { t } = useTranslation();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const nameOf = (id: string | number): string => {
    for (const block of day.blocks) {
      const found = block.exercises.find((exercise) => exercise.key === id);
      if (found !== undefined) return exercises.get(found.exercise_id)?.name_es ?? found.exercise_id;
    }
    return String(id);
  };

  const announcements: Announcements = {
    onDragStart: ({ active }) => t("editor.announce.start", { name: nameOf(active.id) }),
    onDragOver: ({ active, over }) =>
      over === null ? t("editor.announce.none", { name: nameOf(active.id) }) : t("editor.announce.over", { name: nameOf(active.id), over: nameOf(over.id) }),
    onDragEnd: ({ active, over }) =>
      over === null ? t("editor.announce.cancel", { name: nameOf(active.id) }) : t("editor.announce.drop", { name: nameOf(active.id), over: nameOf(over.id) }),
    onDragCancel: ({ active }) => t("editor.announce.cancel", { name: nameOf(active.id) }),
  };
  const screenReaderInstructions: ScreenReaderInstructions = { draggable: t("editor.announce.instructions") };

  const onDragEnd = ({ active, over }: DragEndEvent): void => {
    if (over === null) return;
    dispatch({ type: "move", dayKey: day.key, activeKey: String(active.id), overKey: String(over.id) });
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={onDragEnd}
      accessibility={{ announcements, screenReaderInstructions }}
    >
      <div className={styles["dayFields"]}>
        <label className={styles["mini"]}>
          <span>{t("editor.dayName")}</span>
          <input
            type="text"
            value={day.name}
            maxLength={80}
            onChange={(event) => {
              dispatch({ type: "day", dayKey: day.key, patch: { name: event.target.value } });
            }}
          />
        </label>
      </div>
      {day.blocks.map((block, index) => (
        <BlockView key={block.key} day={day} block={block} isLast={index === day.blocks.length - 1} exercises={exercises} dispatch={dispatch} />
      ))}
      {day.blocks.length === 0 && <p role="alert">{t("editor.emptyDay")}</p>}
    </DndContext>
  );
}

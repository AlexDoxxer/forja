import { useCallback, useEffect, useRef, useState } from "react";

import {
  createInitialState,
  playerReducer,
  toSetCreate,
  type NextSession,
  type PlayerAction,
  type PlayerState,
} from "./playerMachine";
import {
  enqueueOperation,
  loadActiveState,
  loadPlayerState,
  savePlayerState,
  type SyncOperation,
} from "./storage";
import { restoreClockSkew, syncedNow } from "./syncQueue";
import { scheduler } from "./scheduler";
import { uuidv7 } from "../shared/uuid";

function sessionOp(state: PlayerState, updatedAt: number): SyncOperation {
  return {
    op: "session_upsert",
    client_uuid: state.sessionUuid,
    program_day_id: state.programDayId,
    name: state.name,
    started_at: state.startedAt,
    finished_at: state.finishedAt,
    status: state.phase === "completed" ? "completed" : "in_progress",
    perceived_effort: state.perceivedEffort,
    notes: null,
    updated_at: new Date(updatedAt).toISOString(),
  };
}

/** Empieza una sesión: guarda el estado en IndexedDB y encola su alta (ADR 0006). */
export async function startSession(next: NextSession): Promise<PlayerState> {
  await restoreClockSkew();
  const now = syncedNow();
  const state = createInitialState({ sessionUuid: uuidv7(now), now, next });
  await savePlayerState(state);
  await enqueueOperation(sessionOp(state, now));
  void scheduler.trigger();
  return state;
}

export interface PlayerApi {
  state: PlayerState | null;
  loading: boolean;
  dispatch: (action: PlayerAction) => void;
  logSet: (input: { weightKg: number | null; reps: number | null; rir: number | null; isWarmup?: boolean }) => void;
  undoLast: () => void;
  finish: (perceivedEffort: number | null) => void;
}

/**
 * Estado del reproductor con persistencia en IndexedDB. Recupera la sesión indicada (o la
 * activa) tras una recarga; cada cambio se guarda y las escrituras se encolan para `/sync`.
 */
export function usePlayer(sessionUuid?: string): PlayerApi {
  const [state, setState] = useState<PlayerState | null>(null);
  const [loading, setLoading] = useState(true);
  const ref = useRef<PlayerState | null>(null);

  useEffect(() => {
    const alive = { current: true };
    void (async () => {
      const loaded =
        sessionUuid === undefined ? await loadActiveState() : await loadPlayerState(sessionUuid);
      if (!alive.current) return;
      ref.current = loaded ?? null;
      setState(loaded ?? null);
      setLoading(false);
    })();
    return () => {
      alive.current = false;
    };
  }, [sessionUuid]);

  const commit = useCallback((next: PlayerState) => {
    ref.current = next;
    setState(next);
    void savePlayerState(next);
  }, []);

  const dispatch = useCallback(
    (action: PlayerAction) => {
      if (ref.current !== null) commit(playerReducer(ref.current, action));
    },
    [commit],
  );

  const logSet = useCallback<PlayerApi["logSet"]>(
    (input) => {
      const current = ref.current;
      if (current === null) return;
      const now = syncedNow();
      const next = playerReducer(current, { type: "LOG_SET", now, uuid: uuidv7(now), ...input });
      const logged = next.sets[next.sets.length - 1];
      commit(next);
      if (logged !== undefined && next.sets.length > current.sets.length) {
        void enqueueOperation({
          op: "set_upsert",
          session_client_uuid: next.sessionUuid,
          set: toSetCreate(logged),
          updated_at: new Date(now).toISOString(),
        }).then(() => scheduler.trigger());
      }
    },
    [commit],
  );

  const undoLast = useCallback(() => {
    const current = ref.current;
    const last = current?.sets[current.sets.length - 1];
    if (current === null || last === undefined) return;
    commit(playerReducer(current, { type: "UNDO_LAST" }));
    void enqueueOperation({
      op: "set_delete",
      client_uuid: last.clientUuid,
      deleted_at: new Date(syncedNow()).toISOString(),
    }).then(() => scheduler.trigger());
  }, [commit]);

  const finish = useCallback(
    (perceivedEffort: number | null) => {
      const current = ref.current;
      if (current === null) return;
      const now = syncedNow();
      const next = playerReducer(current, { type: "FINISH", now, perceivedEffort });
      commit(next);
      void enqueueOperation(sessionOp(next, now)).then(() => scheduler.trigger());
    },
    [commit],
  );

  return { state, loading, dispatch, logSet, undoLast, finish };
}

import { useNavigate, useParams } from "@tanstack/react-router";

import { SessionPlayer } from "./SessionPlayer";
import { SessionSummary } from "./SessionSummary";

/** Ruta `/sesion`: reproductor de la sesión activa (recuperada de IndexedDB tras una recarga). */
export function SessionRoute(): React.JSX.Element {
  const navigate = useNavigate();
  return (
    <SessionPlayer
      onFinished={(uuid) => {
        void navigate({ to: "/sesion/resumen/$uuid", params: { uuid } });
      }}
      onExit={() => {
        void navigate({ to: "/" });
      }}
    />
  );
}

/** Ruta `/sesion/resumen/$uuid`. */
export function SessionSummaryRoute(): React.JSX.Element {
  const navigate = useNavigate();
  const { uuid } = useParams({ strict: false });
  return (
    <SessionSummary
      sessionUuid={uuid ?? ""}
      onExit={() => {
        void navigate({ to: "/" });
      }}
    />
  );
}

import { setupWorker } from "msw/browser";

import { handlers } from "./handlers";

/**
 * Worker MSW para el navegador. Se arranca solo en desarrollo (`main.tsx`) mientras
 * `backend-api` no está integrado (Fase 2, F2-FE-16 cambia a la API real).
 */
export const worker = setupWorker(...handlers);

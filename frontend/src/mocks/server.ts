import { setupServer } from "msw/node";

import { handlers } from "./handlers";

/** Servidor MSW para Node (Vitest). Ver `tests/setup.ts`. */
export const server = setupServer(...handlers);

import { generatedHandlers } from "./handlers.generated";

/**
 * Handlers de MSW usados por la app en desarrollo y por los tests de componentes.
 * Los handlers generados cubren las 71 operaciones del contrato (`npm run gen:mocks`);
 * aquí se pueden anteponer variantes manuales para un caso concreto de un test con
 * `server.use(...)`, sin tocar el fichero generado.
 */
export const handlers = [...generatedHandlers];

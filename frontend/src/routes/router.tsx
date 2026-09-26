import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";

import { SessionRoute, SessionSummaryRoute } from "../features/session/SessionRoute";
import { LibraryRoute } from "./LibraryRoute";
import { NutritionRoute } from "./NutritionRoute";
import { ProfileRoute } from "./ProfileRoute";
import { ProgramsRoute } from "./ProgramsRoute";
import { ProgressRoute } from "./ProgressRoute";
import { RootLayout } from "./RootLayout";
import { TodayRoute } from "./TodayRoute";

/**
 * Rutas del shell (MASTER_PROMPT §10.1): Hoy · Rutinas · Biblioteca · Progreso · Perfil.
 * Definidas por código (sin generación de fichero de rutas) para mantener la Fase 1 simple;
 * la Fase 2 añade las subrutas de cada sección (detalle, editor, reproductor…).
 */
const rootRoute = createRootRoute({ component: RootLayout });

const todayRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: TodayRoute,
});

const programsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/rutinas",
  component: ProgramsRoute,
});

const libraryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/biblioteca",
  component: LibraryRoute,
});

const progressRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/progreso",
  component: ProgressRoute,
});

const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/perfil",
  component: ProfileRoute,
});

// Parte B (F2): reproductor de sesión, resumen, nutrición y administración.
const sessionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sesion",
  component: SessionRoute,
});

const sessionSummaryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sesion/resumen/$uuid",
  component: SessionSummaryRoute,
});

const nutritionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/nutricion",
  component: NutritionRoute,
});

const routeTree = rootRoute.addChildren([
  nutritionRoute,
  sessionRoute,
  sessionSummaryRoute,
  todayRoute,
  programsRoute,
  libraryRoute,
  progressRoute,
  profileRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

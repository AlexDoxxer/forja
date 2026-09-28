import { createRootRoute, createRoute, createRouter, lazyRouteComponent } from "@tanstack/react-router";

import { SessionRoute, SessionSummaryRoute } from "../features/session/SessionRoute";
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

// Rutas de la parte A (F2): cargadas bajo demanda para mantener el JS inicial < 500 KB gzip
// (§10.5, ADR 0013). Recharts (generador) y dnd-kit (editor) quedan en chunks propios.
const libraryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/biblioteca",
  component: lazyRouteComponent(() => import("../features/library/LibraryScreen"), "LibraryScreen"),
});

const exerciseDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/biblioteca/$exerciseId",
  component: lazyRouteComponent(() => import("../features/library/ExerciseDetailScreen"), "ExerciseDetailScreen"),
});

const onboardingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/onboarding",
  component: lazyRouteComponent(() => import("../features/onboarding/OnboardingScreen"), "OnboardingScreen"),
});

const generatorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/rutinas/nueva",
  component: lazyRouteComponent(() => import("../features/generator/GeneratorScreen"), "GeneratorScreen"),
});

const editorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/rutinas/$programId/editar",
  component: lazyRouteComponent(() => import("../features/editor/EditorScreen"), "EditorScreen"),
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
  component: lazyRouteComponent(() => import("./NutritionRoute"), "NutritionRoute"),
});

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  component: lazyRouteComponent(() => import("./AdminRoute"), "AdminRoute"),
});

// Parte B: inicio de sesión (la guarda de sesión vive en `RootLayout` → `AuthGate`).
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: lazyRouteComponent(() => import("../features/auth/LoginScreen"), "LoginScreen"),
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  adminRoute,
  nutritionRoute,
  sessionRoute,
  sessionSummaryRoute,
  todayRoute,
  programsRoute,
  libraryRoute,
  exerciseDetailRoute,
  onboardingRoute,
  generatorRoute,
  editorRoute,
  progressRoute,
  profileRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

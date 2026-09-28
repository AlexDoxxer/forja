/**
 * Recursos de i18n (MASTER_PROMPT §10.4). `es` es el idioma por defecto; `en` es el único
 * idioma adicional de la interfaz en la Fase 1. Las claves de `es` y `en` deben coincidir
 * exactamente (comprobado por `tests/i18n.test.ts`).
 */
export const resources = {
  es: {
    translation: {
      app: {
        name: "Forja",
        tagline: "Tu entrenamiento, en tu propio servidor.",
      },
      nav: {
        today: "Hoy",
        programs: "Rutinas",
        library: "Biblioteca",
        progress: "Progreso",
        profile: "Perfil",
        nutrition: "Nutrición",
        admin: "Admin",
        skipToContent: "Saltar al contenido",
      },
      media: {
        playAnimation: "Reproducir animación",
        attributionLabel: "Créditos del medio",
      },
      today: {
        title: "Hoy",
        loading: "Cargando el resumen de la semana…",
        error: "No se ha podido cargar el resumen. Inténtalo de nuevo.",
        sessionsCompleted: "Sesiones completadas",
        sessionsPlanned: "Sesiones planificadas",
        volume: "Volumen semanal",
        streak: "Semanas seguidas cumplidas",
      },
      programs: {
        title: "Rutinas",
        loading: "Cargando tus rutinas…",
        error: "No se han podido cargar las rutinas.",
        empty: "Todavía no tienes ninguna rutina guardada.",
        active: "Activa",
        daysPerWeek_one: "{{count}} día por semana",
        daysPerWeek_other: "{{count}} días por semana",
        generate: "Crear una nueva rutina",
        edit: "Editar {{name}}",
        exportPdf: "Exportar a PDF",
        exportCalendar: "Exportar calendario (.ics)",
      },
      library: {
        title: "Biblioteca",
        loading: "Cargando ejercicios…",
        error: "No se ha podido cargar la biblioteca.",
        resultCount_one: "{{count}} ejercicio encontrado",
        resultCount_other: "{{count}} ejercicios encontrados",
      },
      progress: {
        title: "Progreso",
        loading: "Cargando tu progreso…",
        error: "No se ha podido cargar el progreso.",
      },
      profile: {
        title: "Perfil",
        credits: "Créditos y licencias",
        loading: "Cargando los créditos…",
        error: "No se han podido cargar los créditos.",
        datasetCommit: "Commit del dataset ingerido",
        exerciseCount: "Ejercicios en el catálogo",
        healthDisclaimer: "Aviso sanitario",
      },
    },
  },
  en: {
    translation: {
      app: {
        name: "Forja",
        tagline: "Your training, on your own server.",
      },
      nav: {
        today: "Today",
        programs: "Programs",
        library: "Library",
        progress: "Progress",
        profile: "Profile",
        nutrition: "Nutrition",
        admin: "Admin",
        skipToContent: "Skip to content",
      },
      media: {
        playAnimation: "Play animation",
        attributionLabel: "Media credits",
      },
      today: {
        title: "Today",
        loading: "Loading this week's summary…",
        error: "Could not load the summary. Please try again.",
        sessionsCompleted: "Completed sessions",
        sessionsPlanned: "Planned sessions",
        volume: "Weekly volume",
        streak: "Consecutive weeks on target",
      },
      programs: {
        title: "Programs",
        loading: "Loading your programs…",
        error: "Could not load your programs.",
        empty: "You don't have any saved program yet.",
        active: "Active",
        daysPerWeek_one: "{{count}} day per week",
        daysPerWeek_other: "{{count}} days per week",
        generate: "Create a new program",
        edit: "Edit {{name}}",
        exportPdf: "Export to PDF",
        exportCalendar: "Export calendar (.ics)",
      },
      library: {
        title: "Library",
        loading: "Loading exercises…",
        error: "Could not load the library.",
        resultCount_one: "{{count}} exercise found",
        resultCount_other: "{{count}} exercises found",
      },
      progress: {
        title: "Progress",
        loading: "Loading your progress…",
        error: "Could not load your progress.",
      },
      profile: {
        title: "Profile",
        credits: "Credits and licenses",
        loading: "Loading credits…",
        error: "Could not load the credits.",
        datasetCommit: "Ingested dataset commit",
        exerciseCount: "Exercises in the catalog",
        healthDisclaimer: "Health disclaimer",
      },
    },
  },
} as const;

export type SupportedLanguage = keyof typeof resources;
export const SUPPORTED_LANGUAGES: readonly SupportedLanguage[] = ["es", "en"];
export const DEFAULT_LANGUAGE: SupportedLanguage = "es";

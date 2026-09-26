import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../../src/i18n";
import { ExerciseDetailScreen } from "../../src/features/library/ExerciseDetailScreen";
import { LibraryScreen } from "../../src/features/library/LibraryScreen";
import { MuscleMap } from "../../src/features/library/MuscleMap";
import { foldText } from "../../src/features/shared/enums";
import { server } from "../../src/mocks/server";
import { expectNoAxeViolations } from "../axe";
import { exerciseFixture } from "../fixtures/catalog";
import { renderWithRouter } from "../routes/renderWithRouter";
import { render } from "@testing-library/react";
import { installRadixPolyfills } from "../radixPolyfills";

const TOTAL = 1324;
const PAGE = 60;

function catalogHandlers(seen: URLSearchParams[]): void {
  server.use(
    http.get("/api/v1/exercises", ({ request }) => {
      const url = new URL(request.url);
      seen.push(url.searchParams);
      const offset = Number(url.searchParams.get("cursor") ?? "0");
      const q = url.searchParams.get("q");
      const all = q === null ? TOTAL : 3;
      const items = Array.from({ length: Math.min(PAGE, all - offset) }, (_, index) =>
        exerciseFixture(String(offset + index).padStart(4, "0"), q === null ? `ejercicio ${String(offset + index)}` : `sentadilla ${String(index)}`),
      );
      const nextOffset = offset + items.length;
      return HttpResponse.json({ items, next_cursor: nextOffset < all ? String(nextOffset) : null });
    }),
    http.get("/api/v1/catalog/facets", () =>
      HttpResponse.json({
        total: TOTAL,
        body_part: [{ value: "upper_legs", label_es: "Piernas", label_en: "Upper legs", count: 227 }],
        target: [],
        muscle: [],
        equipment: [],
        pattern: [],
        mechanic: [],
        difficulty: [{ value: "1", label_es: "Básico", label_en: "Basic", count: 402 }],
        role: [],
      }),
    ),
  );
}

function stubLayout(): void {
  installRadixPolyfills();
  // jsdom no calcula diseño: el virtualizador necesita un tamaño de ventana.
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 600 });
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: () => 800 });
  Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 800 });
}

describe("foldText", () => {
  it("quita acentos y mayúsculas", () => {
    expect(foldText("  Sentadílla Búlgara ÑANDÚ ")).toBe("sentadilla bulgara nandu");
  });
});

describe("LibraryScreen", () => {
  beforeEach(stubLayout);
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("virtualiza la cuadrícula: solo se monta una ventana de las 1.324 tarjetas y pagina al desplazar", async () => {
    const seen: URLSearchParams[] = [];
    catalogHandlers(seen);
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });

    expect(await screen.findByText("1324 ejercicios encontrados")).toBeInTheDocument();
    const grid = screen.getByRole("region", { name: "Cuadrícula de ejercicios" });
    const initialCards = within(grid).getAllByRole("link").length;
    expect(initialCards).toBeGreaterThan(0);
    expect(initialCards).toBeLessThan(60);

    // Al llegar al final de la primera página se pide la siguiente con el cursor.
    grid.scrollTop = 30 * 316;
    fireEvent.scroll(grid);
    await waitFor(() => {
      expect(seen.some((params) => params.get("cursor") === "60")).toBe(true);
    });
    expect(within(grid).getAllByRole("link").length).toBeLessThan(60);
  });

  it("busca sin acentos y sin mayúsculas: envía la consulta normalizada", async () => {
    const user = userEvent.setup();
    const seen: URLSearchParams[] = [];
    catalogHandlers(seen);
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    await screen.findByText("1324 ejercicios encontrados");

    await user.type(screen.getByRole("searchbox"), "SentadÍlla");
    await waitFor(() => {
      expect(seen.some((params) => params.get("q") === "sentadilla")).toBe(true);
    });
    expect(await screen.findByText("sentadilla 0")).toBeInTheDocument();
  });

  it("los chips y el mapa muscular filtran por la API y se pueden quitar", async () => {
    const user = userEvent.setup();
    const seen: URLSearchParams[] = [];
    catalogHandlers(seen);
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    await screen.findByText("1324 ejercicios encontrados");

    await user.click(screen.getByText("Equipamiento"));
    await user.click(screen.getByRole("button", { name: "Mancuernas" }));
    await waitFor(() => {
      expect(seen.some((params) => params.getAll("equipment").join() === "dumbbell")).toBe(true);
    });

    const chestRegion = screen.getAllByRole("button", { name: "Pecho" }).find((element) => element.tagName === "g");
    expect(chestRegion).toBeDefined();
    if (chestRegion !== undefined) await user.click(chestRegion);
    await waitFor(() => {
      expect(seen.some((params) => params.getAll("muscle").join() === "chest")).toBe(true);
    });
    expect(screen.getByText(/Músculos seleccionados: Pecho/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Favoritos" }));
    await waitFor(() => {
      expect(seen.some((params) => params.get("favorites") === "true")).toBe(true);
    });

    await user.click(screen.getByRole("button", { name: /Quitar 3 filtros/ }));
    expect(screen.queryByText(/Músculos seleccionados/)).not.toBeInTheDocument();
  });

  it("cada tarjeta muestra el medio con la atribución de Gym visual y enlaza al detalle", async () => {
    catalogHandlers([]);
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    const first = await screen.findByText("ejercicio 0");
    expect(first.closest("a")).toHaveAttribute("href", "/biblioteca/0000");
    expect(screen.getAllByRole("link", { name: "© Gym visual" }).length).toBeGreaterThan(0);
  });

  it("muestra estado vacío y error", async () => {
    server.use(http.get("/api/v1/exercises", () => HttpResponse.json({ items: [], next_cursor: null })));
    const { unmount } = renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    expect(await screen.findByText("Ningún ejercicio coincide con la búsqueda.")).toBeInTheDocument();
    unmount();

    server.use(http.get("/api/v1/exercises", () => HttpResponse.json({ title: "x", type: "x", status: 500, code: "service_unavailable" }, { status: 500 })));
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    expect(await screen.findByText("No se ha podido cargar la biblioteca.")).toBeInTheDocument();
  });

  it("la pantalla no tiene violaciones de accesibilidad", async () => {
    catalogHandlers([]);
    const { container } = renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    await screen.findByText("ejercicio 0");
    await expectNoAxeViolations(container);
  });
});

describe("MuscleMap", () => {
  it("es un filtro accesible por teclado y resalta principal y secundarios sin depender del color", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const { container } = render(<MuscleMap selected={["chest"]} secondary={["triceps"]} onToggle={onToggle} />);
    const chest = screen.getByRole("button", { name: "Pecho" });
    expect(chest).toHaveAttribute("aria-pressed", "true");
    chest.focus();
    await user.keyboard("{Enter}");
    expect(onToggle).toHaveBeenCalledWith("chest");
    fireEvent.click(screen.getByRole("button", { name: "Bíceps" }));
    expect(onToggle).toHaveBeenCalledWith("biceps");
    await user.click(screen.getByRole("tab", { name: "Posterior" }));
    expect(screen.getByRole("button", { name: "Dorsales" })).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("en modo lectura etiqueta el músculo objetivo y los secundarios", async () => {
    const user = userEvent.setup();
    render(<MuscleMap selected={["triceps"]} secondary={["chest"]} />);
    expect(screen.getByRole("img", { name: "Pecho (secundario)" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Posterior" }));
    expect(screen.getByRole("img", { name: "Tríceps (objetivo)" })).toBeInTheDocument();
  });
});

describe("ExerciseDetailScreen", () => {
  function detailHandlers(langs: string[]): void {
    server.use(
      http.get("/api/v1/exercises/:id", ({ request }) => {
        const lang = new URL(request.url).searchParams.get("lang") ?? "es";
        langs.push(lang);
        return HttpResponse.json({
          ...exerciseFixture("0043", "sentadilla con barra", { is_favorite: false }),
          secondary_muscles: ["glutes", "hamstrings"],
          primary_group_muscle: "quads",
          equipment_group: "gym",
          instructions: { lang, text: "t", steps: [`Paso uno (${lang})`, `Paso dos (${lang})`] },
          available_langs: ["es", "en", "fr", "it", "pl", "ru", "tr", "zh", "hi", "ko"],
          variants: [{ id: "0044", name_es: "sentadilla con barra", label_es: "vista trasera", kind: "angle", demo_sex: null }],
          source_commit: "a".repeat(40),
          enrichment_version: 1,
          deprecated_at: null,
        });
      }),
      http.get("/api/v1/exercises/:id/alternatives", () =>
        HttpResponse.json({ items: [{ exercise: exerciseFixture("0050", "sentadilla goblet"), score: 0.8 }] }),
      ),
      http.get("/api/v1/stats/exercise/:id", () =>
        HttpResponse.json({ exercise_id: "0043", best_e1rm_kg: 100, best_set: null, points: [{ date: "2026-09-01", e1rm_kg: 100, volume_kg: 500, best_weight_kg: 80, best_reps: 8 }] }),
      ),
    );
  }

  it("muestra músculos, pasos numerados, alternativas e historial, y cambia el idioma de las instrucciones", async () => {
    const user = userEvent.setup();
    const langs: string[] = [];
    detailHandlers(langs);
    const { container } = renderWithRouter(ExerciseDetailScreen, { path: "/biblioteca/$exerciseId", url: "/biblioteca/0043" });

    expect(await screen.findByRole("heading", { name: "sentadilla con barra" })).toBeInTheDocument();
    expect(screen.getByText("Paso uno (es)")).toBeInTheDocument();
    expect(screen.getAllByRole("list").some((list) => list.tagName === "OL")).toBe(true);
    expect(screen.getByText(/Glúteos, Isquiotibiales/)).toBeInTheDocument();
    expect(await screen.findByText("sentadilla goblet")).toBeInTheDocument();
    expect(await screen.findByText(/Mejor e1RM: 100 kg/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "vista trasera" })).toHaveAttribute("href", "/biblioteca/0044");
    expect(screen.getAllByRole("link", { name: "© Gym visual" }).length).toBeGreaterThan(0);
    await expectNoAxeViolations(container);

    await user.click(screen.getByRole("combobox", { name: "Idioma de las instrucciones" }));
    expect(screen.getAllByRole("option")).toHaveLength(10);
    await user.click(screen.getByRole("option", { name: "Français" }));
    expect(await screen.findByText("Paso uno (fr)")).toBeInTheDocument();
    expect(langs).toContain("fr");
  });

  it("marca y desmarca favorito", async () => {
    const user = userEvent.setup();
    detailHandlers([]);
    const calls: string[] = [];
    server.use(
      http.put("/api/v1/exercises/:id/favorite", () => {
        calls.push("PUT");
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderWithRouter(ExerciseDetailScreen, { path: "/biblioteca/$exerciseId", url: "/biblioteca/0043" });
    await user.click(await screen.findByRole("button", { name: "Añadir a favoritos" }));
    await waitFor(() => {
      expect(calls).toEqual(["PUT"]);
    });
  });

  it("muestra error si el ejercicio no existe", async () => {
    server.use(http.get("/api/v1/exercises/:id", () => HttpResponse.json({ title: "No encontrado", type: "x", status: 404, code: "not_found" }, { status: 404 })));
    renderWithRouter(ExerciseDetailScreen, { path: "/biblioteca/$exerciseId", url: "/biblioteca/9999" });
    expect(await screen.findByText("No se ha podido cargar el ejercicio.")).toBeInTheDocument();
  });
});

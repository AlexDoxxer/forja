import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { useState } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import "../../src/i18n";
import { first } from "../../src/features/shared/enums";
import { formatPrescription } from "../../src/features/shared/format";
import { MuscleMap } from "../../src/features/library/MuscleMap";
import { Button, Dialog, NumberPad, Slider, ToastProvider, useToast } from "../../src/components/ui";
import { PreviewPanel } from "../../src/features/generator/PreviewPanel";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EditorScreen } from "../../src/features/editor/EditorScreen";
import { violationsOf } from "../../src/features/editor/useEditor";
import { LibraryScreen } from "../../src/features/library/LibraryScreen";
import { ApiError } from "../../src/lib/api/client";
import { server } from "../../src/mocks/server";
import { exerciseFixture, prescriptionFixture, previewFixture, programFixture } from "../fixtures/catalog";
import { installRadixPolyfills } from "../radixPolyfills";
import { renderWithRouter } from "../routes/renderWithRouter";

beforeEach(installRadixPolyfills);

describe("editor: ejercicios por tiempo, por lado y notas", () => {
  it("edita duración, RIR vacío, notas y por lado", async () => {
    const user = userEvent.setup();
    const program = programFixture();
    const block = program.weeks[0]?.days[0]?.blocks[0];
    if (block === undefined) throw new Error("fixture");
    block.exercises[0] = {
      ...block.exercises[0],
      ...prescriptionFixture("0043", { rep_min: null, rep_max: null, duration_s: 45, per_side: true, target_rir: null }),
      id: "0192f09e-0000-7c2d-8e4f-0000000000e1",
      order: 0,
    };
    server.use(http.get("/api/v1/programs/:id", () => HttpResponse.json(program)));
    renderWithRouter(EditorScreen, { path: "/rutinas/$programId/editar", url: "/rutinas/x/editar" });
    const duration = await screen.findByLabelText("Duración (s)");
    await user.clear(duration);
    await user.type(duration, "2");
    expect(await screen.findByText("Entre 5 y 3600 segundos.")).toBeInTheDocument();
    await user.type(duration, "0");
    expect(screen.queryByText("Entre 5 y 3600 segundos.")).not.toBeInTheDocument();
    const rir = first(screen.getAllByLabelText("RIR"));
    await user.type(rir, "9");
    expect(await screen.findByText("RIR entre 0 y 5.")).toBeInTheDocument();
    await user.clear(rir);
    await user.type(first(screen.getAllByLabelText("Notas")), "ojo");
    await user.click(first(screen.getAllByRole("checkbox", { name: "Por lado" })));
    await user.click(first(screen.getAllByRole("checkbox", { name: "Por lado" })));
    await user.type(first(screen.getAllByLabelText("Nombre del día")), "!");
    expect(screen.getByDisplayValue("Cuerpo completo A!")).toBeInTheDocument();
  });

  it("violationsOf tolera errores sin violaciones", () => {
    expect(violationsOf(new Error("x"))).toEqual([]);
    expect(violationsOf(new ApiError("texto"))).toEqual([]);
    expect(violationsOf(new ApiError({ violations: "no" }))).toEqual([]);
    expect(violationsOf(new ApiError({ violations: [{ code: "empty_day" }] }))).toHaveLength(1);
  });
});

describe("ui: aviso de error y teclado numérico", () => {
  it("toast de error y de información", async () => {
    const user = userEvent.setup();
    function Trigger(): React.JSX.Element {
      const { push } = useToast();
      return (
        <Button
          onClick={() => {
            push({ title: "Fallo", tone: "error" });
            push({ title: "Nota" });
          }}
        >
          Ir
        </Button>
      );
    }
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Ir" }));
    expect(await screen.findByText("Fallo")).toBeInTheDocument();
    expect(screen.getByText("Nota")).toBeInTheDocument();
  });

  it("respeta la longitud máxima, sin decimales y el cero inicial", async () => {
    const user = userEvent.setup();
    function Demo(): React.JSX.Element {
      const [value, setValue] = useState("0");
      return (
        <div>
          <output aria-label="v">{value}</output>
          <NumberPad value={value} onChange={setValue} maxLength={3} />
        </div>
      );
    }
    render(<Demo />);
    expect(screen.getByRole("button", { name: "Coma decimal" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "5" }));
    expect(screen.getByLabelText("v")).toHaveTextContent("5");
    await user.click(screen.getByRole("button", { name: "1" }));
    await user.click(screen.getByRole("button", { name: "2" }));
    await user.click(screen.getByRole("button", { name: "3" }));
    expect(screen.getByLabelText("v")).toHaveTextContent("512");
  });
});

describe("biblioteca: vista previa animada", () => {
  it("al pasar el cursor o enfocar la tarjeta se muestra el GIF", async () => {
    server.use(
      http.get("/api/v1/exercises", () =>
        HttpResponse.json({ items: [exerciseFixture("0001", "remo")], next_cursor: null }),
      ),
    );
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 600 });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: () => 800 });
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    const card = (await screen.findByText("remo")).closest("li") as HTMLElement;
    const img = (): string => card.querySelector("img")?.getAttribute("src") ?? "";
    expect(img()).toContain("thumbs");
    fireEvent.mouseEnter(card);
    await waitFor(() => {
      expect(img()).toContain("gifs");
    });
    fireEvent.mouseLeave(card);
    fireEvent.focus(card);
    fireEvent.blur(card);
    expect(img()).toContain("thumbs");
  });
});

describe("ui: variantes sin descripción ni texto de valor", () => {
  it("Dialog sin descripción y Slider sin valueText", () => {
    render(
      <div>
        <Dialog open onOpenChange={() => undefined} title="Solo título">
          <p>x</p>
        </Dialog>
        <Slider label="Nivel" value={2} min={1} max={5} onValueChange={() => undefined} />
      </div>,
    );
    expect(screen.getByRole("dialog", { name: "Solo título" })).not.toHaveAttribute("aria-describedby");
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});

describe("generador: casos límite de la vista previa", () => {
  it("muestra el id si falta el ejercicio, día de recuperación y error al cambiar", async () => {
    const user = userEvent.setup();
    const preview = previewFixture();
    const day = preview.plan.weeks[0]?.days[0];
    if (day === undefined) throw new Error("fixture");
    day.is_recovery = true;
    preview.plan.warnings = [];
    preview.exercises = [];
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <PreviewPanel preview={preview} onChange={() => undefined} />
        </ToastProvider>
      </QueryClientProvider>,
    );
    expect(screen.getByText("0043")).toBeInTheDocument();
    expect(screen.getByText(/día de recuperación/)).toBeInTheDocument();
    server.use(
      http.post("/api/v1/generator/preview/regenerate-day", () => HttpResponse.json({ title: "x", type: "x", status: 500, code: "service_unavailable" }, { status: 500 })),
    );
    await user.click(screen.getByRole("button", { name: "Regenerar este día" }));
    expect(await screen.findByText("No se ha podido regenerar el día.")).toBeInTheDocument();
  });
});

describe("utilidades compartidas", () => {
  it("formatPrescription cubre todas las ramas y first() falla con listas vacías", () => {
    expect(formatPrescription({ sets: 3, rep_min: null, rep_max: 12, duration_s: null, per_side: false }, "x")).toBe("3×12");
    expect(formatPrescription({ sets: 3, rep_min: null, rep_max: null, duration_s: null, per_side: false }, "x")).toBe("3×");
    expect(() => first([])).toThrow("Lista vacía");
    expect(first([1])).toBe(1);
  });

  it("MuscleMap sin selección ni secundarios", () => {
    render(<MuscleMap selected={[]} />);
    expect(screen.getAllByRole("img").length).toBeGreaterThan(5);
  });
});

describe("biblioteca: todos los grupos de filtros", () => {
  it("zona, patrón y dificultad se envían a la API y se pueden quitar", async () => {
    const user = userEvent.setup();
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 600 });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: () => 800 });
    const seen: URLSearchParams[] = [];
    server.use(
      http.get("/api/v1/exercises", ({ request }) => {
        seen.push(new URL(request.url).searchParams);
        return HttpResponse.json({ items: [exerciseFixture("0001", "remo")], next_cursor: null });
      }),
    );
    renderWithRouter(LibraryScreen, { path: "/biblioteca" });
    await screen.findByText("remo");
    for (const summary of ["Zona", "Patrón", "Dificultad"]) await user.click(screen.getByText(summary));
    await user.click(screen.getByRole("button", { name: /^Muslos/ }));
    await user.click(screen.getByRole("button", { name: "Sentadilla" }));
    await user.click(screen.getByRole("button", { name: /^Estándar/ }));
    await waitFor(() => {
      expect(seen.some((p) => p.getAll("body_part").length === 1 && p.getAll("pattern").length === 1 && p.getAll("difficulty").join() === "2")).toBe(true);
    });
    await user.click(screen.getByRole("button", { name: /^Estándar/ }));
    await user.click(screen.getByRole("button", { name: "Sentadilla" }));
    await user.click(screen.getByRole("button", { name: /^Muslos/ }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Quitar/ })).not.toBeInTheDocument();
    });
  });
});

import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import "../../../src/i18n";
import {
  Button,
  Card,
  CheckField,
  Chip,
  ChoiceCard,
  Dialog,
  NumberPad,
  Select,
  Sheet,
  Slider,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  TextField,
  ToastProvider,
  useToast,
} from "../../../src/components/ui";
import { expectNoAxeViolations } from "../../axe";

beforeAll(() => {
  // Radix (Select/Slider) usa APIs de puntero que jsdom no implementa.
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => undefined;
  Element.prototype.releasePointerCapture = () => undefined;
  class ResizeObserverStub {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
});

describe("Button y Chip", () => {
  it("el botón dispara onClick y el chip conmuta aria-pressed", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    function Demo(): React.JSX.Element {
      const [on, setOn] = useState(false);
      return (
        <div>
          <Button variant="primary" onClick={onClick}>
            Guardar
          </Button>
          <Chip selected={on} onSelectedChange={setOn}>
            Mancuernas
          </Chip>
        </div>
      );
    }
    const { container } = render(<Demo />);
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    const chip = screen.getByRole("button", { name: "Mancuernas" });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await user.click(chip);
    expect(chip).toHaveAttribute("aria-pressed", "true");
    await expectNoAxeViolations(container);
  });
});

describe("Dialog y Sheet", () => {
  it("Dialog: título accesible, cierra con Esc", async () => {
    const user = userEvent.setup();
    function Demo(): React.JSX.Element {
      const [open, setOpen] = useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen} title="Confirmar" description="¿Seguro?">
          <p>Contenido</p>
        </Dialog>
      );
    }
    render(<Demo />);
    const dialog = screen.getByRole("dialog", { name: "Confirmar" });
    expect(dialog).toHaveAccessibleDescription("¿Seguro?");
    await expectNoAxeViolations(dialog);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Sheet: se puede cerrar con el botón Cerrar", async () => {
    const user = userEvent.setup();
    function Demo(): React.JSX.Element {
      const [open, setOpen] = useState(true);
      return (
        <Sheet open={open} onOpenChange={setOpen} title="Alternativas">
          <p>Lista</p>
        </Sheet>
      );
    }
    render(<Demo />);
    const sheet = screen.getByRole("dialog", { name: "Alternativas" });
    await expectNoAxeViolations(sheet);
    await user.click(within(sheet).getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Tabs", () => {
  it("navega con flechas y muestra el panel activo", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList aria-label="Días">
          <TabsTrigger value="a">Día A</TabsTrigger>
          <TabsTrigger value="b">Día B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Panel A</TabsContent>
        <TabsContent value="b">Panel B</TabsContent>
      </Tabs>,
    );
    await user.click(screen.getByRole("tab", { name: "Día A" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Día B" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Panel B")).toBeVisible();
    await expectNoAxeViolations(container);
  });
});

describe("Select, Slider, campos", () => {
  it("Select elige una opción con teclado", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    const { container } = render(
      <Select
        label="Nivel"
        value="beginner"
        onValueChange={onValueChange}
        options={[
          { value: "beginner", label: "Principiante" },
          { value: "advanced", label: "Avanzado" },
        ]}
      />,
    );
    const trigger = screen.getByRole("combobox", { name: "Nivel" });
    expect(trigger).toHaveTextContent("Principiante");
    await expectNoAxeViolations(container);
    trigger.focus();
    await user.keyboard("{Enter}");
    await user.click(await screen.findByRole("option", { name: "Avanzado" }));
    expect(onValueChange).toHaveBeenCalledWith("advanced");
  });

  it("Slider responde a las flechas del teclado", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    const { container } = render(
      <Slider label="Duración" value={60} min={20} max={120} step={5} valueText="60 min" onValueChange={onValueChange} />,
    );
    const thumb = screen.getByRole("slider", { name: /Duración/ });
    thumb.focus();
    await user.keyboard("{ArrowRight}");
    expect(onValueChange).toHaveBeenCalledWith(65);
    await expectNoAxeViolations(container);
  });

  it("TextField asocia etiqueta, pista y error; CheckField y tarjetas son accesibles", async () => {
    const onSelect = vi.fn();
    const { container } = render(
      <div>
        <TextField label="Correo" hint="Lo usarás para entrar" error="Formato no válido" defaultValue="x" />
        <CheckField label="Acepto" />
        <ChoiceCard selected title="Fuerza" description="Cargas altas" onSelect={onSelect} />
        <Card>Neutra</Card>
      </div>,
    );
    const input = screen.getByLabelText("Correo");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription(/Lo usarás.*Formato/);
    fireEvent.click(screen.getByRole("button", { name: /Fuerza/ }));
    expect(onSelect).toHaveBeenCalled();
    await expectNoAxeViolations(container);
  });
});

describe("Toast y NumberPad", () => {
  it("publica un aviso accesible", async () => {
    const user = userEvent.setup();
    function Trigger(): React.JSX.Element {
      const { push } = useToast();
      return (
        <Button
          onClick={() => {
            push({ title: "Rutina guardada", description: "Ya está activa", tone: "success" });
          }}
        >
          Lanzar
        </Button>
      );
    }
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Lanzar" }));
    expect(await screen.findByText("Rutina guardada")).toBeInTheDocument();
  });

  it("el teclado numérico compone valores con decimal y borra", async () => {
    const user = userEvent.setup();
    function Demo(): React.JSX.Element {
      const [value, setValue] = useState("");
      return (
        <div>
          <output aria-label="valor">{value}</output>
          <NumberPad value={value} onChange={setValue} allowDecimal />
        </div>
      );
    }
    const { container } = render(<Demo />);
    await user.click(screen.getByRole("button", { name: "Coma decimal" }));
    await user.click(screen.getByRole("button", { name: "7" }));
    await user.click(screen.getByRole("button", { name: "5" }));
    expect(screen.getByLabelText("valor")).toHaveTextContent("0.75");
    expect(screen.getByRole("button", { name: "Coma decimal" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Borrar último dígito" }));
    expect(screen.getByLabelText("valor")).toHaveTextContent("0.7");
    await expectNoAxeViolations(container);
  });
});

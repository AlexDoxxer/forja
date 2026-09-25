import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../../src/i18n";
import { ExerciseMedia } from "../../src/components/ExerciseMedia";
import type { ExerciseMediaValue } from "../../src/components/ExerciseMedia";

const validMedia: ExerciseMediaValue = {
  thumb_url: "/media/thumbs/0043-qXTaZnJ.jpg",
  gif_url: "/media/gifs/0043-qXTaZnJ.gif",
  width: 180,
  height: 180,
  attribution: { text: "© Gym visual", url: "https://gymvisual.com/" },
};

function mockMatchMedia(reducedMotion: boolean): void {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("prefers-reduced-motion") ? reducedMotion : false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

describe("ExerciseMedia", () => {
  beforeEach(() => {
    mockMatchMedia(false);
  });

  it("muestra siempre la atribución obligatoria de Gym visual con enlace seguro", () => {
    render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" />);

    const link = screen.getByRole("link", { name: "© Gym visual" });
    expect(link).toHaveAttribute("href", "https://gymvisual.com/");
    expect(link).toHaveAttribute("rel", "noopener");
  });

  it("nunca renderiza un medio sin la atribución exacta: falla en vez de omitirla", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const mediaWithoutAttribution = {
      ...validMedia,
      attribution: { text: "", url: "" },
    } as unknown as ExerciseMediaValue;

    expect(() => render(<ExerciseMedia media={mediaWithoutAttribution} alt="Sentadilla" />)).toThrow(
      /atribución/,
    );

    consoleError.mockRestore();
  });

  it("limita el medio a 180 px CSS y expone ancho/alto explícitos", () => {
    render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" />);

    const img = screen.getByAltText("Sentadilla con barra");
    expect(img).toHaveAttribute("width", "180");
    expect(img).toHaveAttribute("height", "180");
    expect(img).toHaveStyle({ maxWidth: "180px", maxHeight: "180px" });
  });

  it("usa carga diferida y decodificación asíncrona", () => {
    render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" />);

    const img = screen.getByAltText("Sentadilla con barra");
    expect(img).toHaveAttribute("loading", "lazy");
    expect(img).toHaveAttribute("decoding", "async");
  });

  it("por defecto (miniatura) muestra el JPG, no el GIF", () => {
    render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" />);

    const img = screen.getByAltText("Sentadilla con barra");
    expect(img).toHaveAttribute("src", validMedia.thumb_url);
  });

  it("en variante animada sin reduced-motion reproduce el GIF directamente", () => {
    render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" variant="animated" />);

    const img = screen.getByAltText("Sentadilla con barra");
    expect(img).toHaveAttribute("src", validMedia.gif_url);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  describe("prefers-reduced-motion", () => {
    beforeEach(() => {
      mockMatchMedia(true);
    });

    it("fuerza la miniatura estática incluso en variante animada y ofrece un botón para reproducir", () => {
      render(<ExerciseMedia media={validMedia} alt="Sentadilla con barra" variant="animated" />);

      const img = screen.getByAltText("Sentadilla con barra");
      expect(img).toHaveAttribute("src", validMedia.thumb_url);

      const playButton = screen.getByRole("button", { name: /reproducir animación/i });
      fireEvent.click(playButton);

      expect(screen.getByAltText("Sentadilla con barra")).toHaveAttribute("src", validMedia.gif_url);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});

import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoginScreen } from "../../src/features/auth/LoginScreen";
import { renderRoute } from "./renderRoute";

/**
 * Pantalla de acceso / landing (F5-FE-01): insignia, titular en dos líneas con acento, bajada,
 * pie de estadísticas y coreografía de entrada de Framer Motion. La lógica de envío del
 * formulario (errores por estado HTTP, redirección tras iniciar sesión…) ya está cubierta en
 * `tests/features/auth.test.tsx`; este fichero cubre el contenido y el maquetado nuevos de la
 * landing, incluida la rama de `prefers-reduced-motion` de `reveal()`.
 */
function mockReducedMotion(reduced: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion") ? reduced : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
}

function renderLogin(): void {
  renderRoute(<LoginScreen />, "/login", ["/onboarding"]);
}

describe("LoginScreen — landing", () => {
  it("muestra la insignia, el titular con el acento en Forja, la bajada y las tres estadísticas", async () => {
    mockReducedMotion(false);
    renderLogin();

    expect(await screen.findByText("Entrenamiento autoalojado")).toBeInTheDocument();

    const headline = screen.getByRole("heading", { level: 1 });
    expect(headline.textContent).toContain("Forja");
    expect(headline.textContent).toContain("tu rutina");
    expect(headline.textContent).toContain("con datos, no con suposiciones.");

    expect(screen.getByText(/motor determinista/)).toBeInTheDocument();
    expect(screen.getByText("1.324 ejercicios con GIF de demostración")).toBeInTheDocument();
    expect(screen.getByText("Tus datos no salen de tu servidor")).toBeInTheDocument();
    expect(screen.getByText("Rutinas generadas sin IA generativa")).toBeInTheDocument();

    // El antiguo `<h1>«Iniciar sesión»` sigue existiendo como nombre accesible del formulario,
    // solo que visualmente oculto (el `<h1>` visible ahora es el titular de la landing).
    expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("con movimiento reducido, el contenido se muestra igual (sin animar la entrada)", async () => {
    mockReducedMotion(true);
    renderLogin();

    expect(await screen.findByText("Entrenamiento autoalojado")).toBeInTheDocument();
    const headline = screen.getByRole("heading", { level: 1 });
    expect(headline.textContent).toContain("con datos, no con suposiciones.");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("«Crear una cuenta» aparece una sola vez (el enlace contextual bajo el formulario) y lleva a /onboarding", async () => {
    mockReducedMotion(false);
    renderLogin();

    const links = await screen.findAllByRole("link", { name: "Crear una cuenta" });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/onboarding");
  });

  it("los campos de correo y contraseña son accesibles por su etiqueta", async () => {
    mockReducedMotion(false);
    renderLogin();

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
  });

  it("«Entrar» no se deshabilita por tener los campos vacíos (F5-FE-02: solo `busy` lo deshabilita)", async () => {
    mockReducedMotion(false);
    renderLogin();

    expect(await screen.findByRole("button", { name: "Entrar" })).not.toBeDisabled();
  });
});

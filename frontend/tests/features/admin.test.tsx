import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../src/mocks/server";
import { AdminRoute } from "../../src/routes/AdminRoute";
import { renderRoute } from "./renderRoute";

const me = (role: string): object => ({
  id: "u1", email: "a@x.com", display_name: "A", role, locale: "es", units: "metric",
  created_at: "", last_login_at: null, onboarding_completed: true, diet_available: true,
});

const run = {
  id: "r1",
  status: "succeeded",
  dry_run: true,
  commit: "7455efae41b330c265e7cd4b78dfa848e7ce5ebd",
  started_at: "2026-09-25T10:00:00Z",
  finished_at: "2026-09-25T10:01:00Z",
  triggered_by: "a@x.com",
  counts: { exercises_total: 1324, added: 2, updated: 3, deprecated: 1, unchanged: 1318, media_verified: 2648 },
  diff: { added: ["0001", "0002"], updated: ["0003"], deprecated: [] },
  errors: [],
  warnings: ["Aviso de prueba"],
};

function useAdmin(): void {
  server.use(
    http.get("/api/v1/auth/me", () => HttpResponse.json(me("admin"))),
    http.get("/api/v1/admin/settings", () =>
      HttpResponse.json({ registration_open: true, diet_feature_enabled: false, media_require_auth: true, dataset_commit: "abc123" }),
    ),
    http.get("/api/v1/admin/users", () =>
      HttpResponse.json({
        items: [
          { id: "u2", email: "b@x.com", display_name: "B", role: "user", is_active: true, created_at: "", last_login_at: null },
        ],
        next_cursor: null,
      }),
    ),
    http.get("/api/v1/admin/ingest/runs", () => HttpResponse.json({ items: [run], next_cursor: null })),
  );
}

describe("AdminRoute", () => {
  it("una persona sin rol de administración no ve los paneles", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(me("user"))));
    renderRoute(<AdminRoute />);
    expect(await screen.findByText(/Solo las personas administradoras/)).toBeInTheDocument();
    expect(screen.queryByText("Usuarios")).not.toBeInTheDocument();
  });

  it("cambia el registro y la dieta global", async () => {
    useAdmin();
    let body: unknown = null;
    server.use(
      http.put("/api/v1/admin/settings", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...(body as object), media_require_auth: true, dataset_commit: "abc123" });
      }),
    );
    const user = userEvent.setup();
    renderRoute(<AdminRoute />);
    await user.click(await screen.findByLabelText("Función de nutrición disponible"));
    await waitFor(() => {
      expect(body).toEqual({ registration_open: true, diet_feature_enabled: true });
    });
    await user.click(screen.getByLabelText("Registro abierto a nuevas cuentas"));
    await waitFor(() => {
      expect(body).toEqual({ registration_open: false, diet_feature_enabled: true });
    });
  });

  it("gestiona usuarios: rol y activación", async () => {
    useAdmin();
    const patches: unknown[] = [];
    server.use(
      http.patch("/api/v1/admin/users/:id", async ({ request }) => {
        patches.push(await request.json());
        return HttpResponse.json({ id: "u2", email: "b@x.com", display_name: "B", role: "admin", is_active: false, created_at: "", last_login_at: null });
      }),
    );
    const user = userEvent.setup();
    renderRoute(<AdminRoute />);
    await user.selectOptions(await screen.findByLabelText("Rol de b@x.com"), "admin");
    await user.click(screen.getByLabelText("Cuenta activa de b@x.com"));
    await waitFor(() => {
      expect(patches).toEqual([{ role: "admin" }, { is_active: false }]);
    });
  });

  it("lanza la ingesta (simulación) y muestra ejecuciones con diff", async () => {
    useAdmin();
    let dry: unknown = null;
    server.use(
      http.post("/api/v1/admin/ingest", async ({ request }) => {
        dry = await request.json();
        return HttpResponse.json({ ...run, status: "queued" }, { status: 202 });
      }),
    );
    const user = userEvent.setup();
    renderRoute(<AdminRoute />);
    const item = await screen.findByText("Correcta · 7455efa");
    const card = item.closest("li");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText(/2 nuevos · 3 actualizados · 1 retirados/)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(/Diff: 2 añadidos, 1 actualizados, 0 retirados/)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("Aviso de prueba")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Simular ingesta" }));
    await waitFor(() => {
      expect(dry).toEqual({ dry_run: true });
    });
    expect(await screen.findByText("Ingesta en cola.")).toBeInTheDocument();
  });
});

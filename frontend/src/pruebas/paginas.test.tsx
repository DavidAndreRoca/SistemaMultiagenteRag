import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ProveedorSesion } from "../sesion/sesion";

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

function montar(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rutas protegidas", () => {
  it("sin sesión, el panel lleva al inicio de sesión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respuestaJson({ codigo: "no_autenticado", mensaje: "x" }, 401)),
    );
    montar("/panel");
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("una cuenta con contraseña inicial debe cambiarla primero", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuestaJson({
          cuenta: "CASO-01-A",
          rol: "A1",
          debe_cambiar_contrasena: true,
          expira_en: "2026-11-20T00:00:00Z",
          csrf: "t",
        }),
      ),
    );
    montar("/panel");
    expect(
      await screen.findByRole("heading", { name: "Cambiar la contraseña" }),
    ).toBeInTheDocument();
  });
});

describe("inicio de sesión", () => {
  it("muestra el motivo del rechazo y el identificador de incidencia", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((peticion: Request) => {
        llamadas.push(peticion);
        if (peticion.method === "GET") {
          return Promise.resolve(respuestaJson({ codigo: "no_autenticado", mensaje: "x" }, 401));
        }
        return Promise.resolve(
          respuestaJson(
            {
              codigo: "credenciales_invalidas",
              mensaje: "El código o la contraseña no son correctos.",
              incidencia_id: "inc-001",
            },
            401,
          ),
        );
      }),
    );
    const usuario = userEvent.setup();
    montar("/entrar");
    await usuario.type(await screen.findByLabelText("Código de cuenta"), "CASO-01-A");
    await usuario.type(screen.getByLabelText("Contraseña"), "incorrecta");
    await usuario.click(screen.getByRole("button", { name: "Ingresar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("El código o la contraseña no son correctos.");
    expect(alerta).toHaveTextContent("inc-001");
    const envio = llamadas.find((p) => p.method === "POST");
    expect(envio?.url).toMatch(/\/api\/sesion$/);
    expect(screen.getByLabelText("Contraseña")).toHaveValue(""); // no queda la contraseña
  });
});

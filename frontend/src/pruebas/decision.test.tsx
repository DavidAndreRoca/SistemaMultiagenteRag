import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DecisionSobreResultado } from "../componentes/Decision";

const SOLICITUD = "66666666-6666-4666-8666-666666666666";
const RUTA = `/api/caso/solicitudes/${SOLICITUD}/decision`;

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

function decision(id: string, opcion: string, reemplaza: string | null = null) {
  return { id, opcion, decidida_en: "2026-11-27T15:00:00Z", reemplaza_a: reemplaza };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

function simular(vistas: unknown[]) {
  const pedidos: { metodo: string; cuerpo: unknown }[] = [];
  let lecturas = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (pedido: Request) => {
      const url = new URL(pedido.url);
      expect(url.pathname).toBe(RUTA);
      if (pedido.method === "POST") {
        pedidos.push({ metodo: "POST", cuerpo: await pedido.json() });
        return respuestaJson(decision("d2", "rechazar", "d1"), 201);
      }
      const vista = vistas[Math.min(lecturas, vistas.length - 1)];
      lecturas += 1;
      return respuestaJson(vista);
    }),
  );
  return pedidos;
}

describe("decisión sobre un resultado", () => {
  it("registra la decisión, muestra la vigente y conserva la anterior", async () => {
    const pedidos = simular([
      {
        solicitud_id: SOLICITUD,
        opciones: ["aceptar", "modificar", "rechazar"],
        vigente: decision("d1", "aceptar"),
        historial: [decision("d1", "aceptar")],
      },
      {
        solicitud_id: SOLICITUD,
        opciones: ["aceptar", "modificar", "rechazar"],
        vigente: decision("d2", "rechazar", "d1"),
        historial: [decision("d1", "aceptar"), decision("d2", "rechazar", "d1")],
      },
    ]);
    const usuario = userEvent.setup();
    render(<DecisionSobreResultado solicitud={SOLICITUD} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Decidió: La acepto");
    expect(screen.getByRole("button", { name: "La acepto" })).toBeDisabled();

    await usuario.click(screen.getByRole("button", { name: "No la usaré" }));
    await vi.waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Decidió: No la usaré");
    });
    expect(pedidos).toEqual([{ metodo: "POST", cuerpo: { opcion: "rechazar" } }]);
    expect(screen.getByText("Decisiones anteriores (1)")).toBeVisible();
  });

  it("tras una abstención ofrece continuar y deja aportar como pendiente", async () => {
    simular([
      { solicitud_id: SOLICITUD, opciones: ["continuar", "aportar"], vigente: null, historial: [] },
    ]);
    render(<DecisionSobreResultado solicitud={SOLICITUD} />);
    expect(
      await screen.findByRole("button", { name: "Continuar sin aportar una fuente" }),
    ).toBeEnabled();
    expect(screen.getByRole("button", { name: "Aportar una fuente" })).toBeDisabled();
    expect(screen.getByText("Pendiente")).toBeVisible();
    expect(screen.queryByRole("button", { name: "La acepto" })).toBeNull();
  });

  it("no muestra nada si todavía no hay resultado que decidir", async () => {
    simular([{ solicitud_id: SOLICITUD, opciones: [], vigente: null, historial: [] }]);
    const { container } = render(<DecisionSobreResultado solicitud={SOLICITUD} />);
    await vi.waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });
    expect(container).toBeEmptyDOMElement();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AporteDeFuente } from "../componentes/Aporte";

const SOLICITUD = "77777777-7777-4777-8777-777777777777";
const NUEVA = "88888888-8888-4888-8888-888888888888";

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

function aporte(cambios: Record<string, unknown> = {}) {
  return {
    id: "a1",
    titulo: "Efectos de la política monetaria",
    anio: 2024,
    doi: "10.5555/monetaria.2024",
    con_pdf: false,
    existencia: "confirmada",
    metodo_existencia: "doi",
    coherencia: "coherente",
    explicacion_coherencia: "Trata la inflación.",
    indexacion: "indexada",
    motivo_indexacion: null,
    texto_indexado: "resumen",
    cita_propuesta: "Ficticia, A. (2024). Efectos de la política monetaria.",
    nueva_solicitud_id: NUEVA,
    aportada_en: "2026-11-27T15:00:00Z",
    ...cambios,
  };
}

function simular(respuesta: unknown, estado = 201) {
  const enviados: FormData[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (pedido: Request) => {
      const url = new URL(pedido.url);
      if (pedido.method === "POST") {
        expect(url.pathname).toBe(`/api/caso/solicitudes/${SOLICITUD}/aporte`);
        enviados.push(await pedido.formData());
        return respuestaJson(respuesta, estado);
      }
      expect(url.pathname).toBe(`/api/caso/solicitudes/${SOLICITUD}/aportes`);
      return respuestaJson([]);
    }),
  );
  return enviados;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

async function llenar(usuario: ReturnType<typeof userEvent.setup>, doi = "") {
  await usuario.type(screen.getByLabelText("Título"), "Efectos de la política monetaria");
  await usuario.type(screen.getByLabelText("Autores"), "Ficticia{Enter}Prueba");
  await usuario.type(screen.getByLabelText("Año"), "2024");
  if (doi) await usuario.type(screen.getByLabelText("DOI (opcional)"), doi);
  await usuario.click(screen.getByRole("button", { name: "Aportar la fuente" }));
}

describe("aporte de una fuente", () => {
  it("envía los datos, muestra el desenlace y lleva a la nueva búsqueda", async () => {
    const enviados = simular(aporte());
    const alNuevaBusqueda = vi.fn();
    const alAportado = vi.fn();
    const usuario = userEvent.setup();
    render(
      <AporteDeFuente
        solicitud={SOLICITUD}
        abierto
        alAportado={alAportado}
        alNuevaBusqueda={alNuevaBusqueda}
      />,
    );
    await llenar(usuario, "10.5555/monetaria.2024");
    expect(await screen.findByText(/su DOI se confirmó/)).toBeVisible();
    expect(screen.getByText(/Ficticia, A. \(2024\)/)).toBeVisible();
    expect(
      screen.getByText(/Se guardó el resumen de la obra en su colección personal/),
    ).toBeVisible();
    const datos = enviados[0];
    expect(datos?.get("autores")).toMatch(/^Ficticia\r?\nPrueba$/); // FormData usa CRLF
    expect(datos?.get("doi")).toBe("10.5555/monetaria.2024");
    expect(datos?.has("archivo")).toBe(false);
    expect(alAportado).toHaveBeenCalledOnce();
    await usuario.click(
      screen.getByRole("button", { name: "Ver la nueva búsqueda con su fuente" }),
    );
    expect(alNuevaBusqueda).toHaveBeenCalledWith(NUEVA);
  });

  it("si la existencia no se confirma lo dice y no ofrece una nueva búsqueda", async () => {
    simular(
      aporte({
        existencia: "no_localizada",
        metodo_existencia: null,
        indexacion: "no_indexada",
        motivo_indexacion: "existencia_no_confirmada",
        cita_propuesta: null,
        nueva_solicitud_id: null,
      }),
    );
    const usuario = userEvent.setup();
    render(<AporteDeFuente solicitud={SOLICITUD} abierto alNuevaBusqueda={vi.fn()} />);
    await llenar(usuario);
    expect(await screen.findByText(/No se confirmó que la obra exista/)).toBeVisible();
    expect(screen.queryByRole("button", { name: /nueva búsqueda/ })).toBeNull();
  });

  it("pide los datos mínimos antes de enviar", async () => {
    const enviados = simular(aporte());
    const usuario = userEvent.setup();
    render(<AporteDeFuente solicitud={SOLICITUD} abierto alNuevaBusqueda={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Título"), "Solo el título");
    await usuario.click(screen.getByRole("button", { name: "Aportar la fuente" }));
    expect(enviados).toEqual([]);
  });
});

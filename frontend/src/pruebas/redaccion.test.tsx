import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { compararPalabras } from "../diferencias";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "99999999-9999-4999-8999-999999999999";
const ORIGINAL = "En este estudio se hizo una medición de la ansiedad de 84 estudiantes.";
const PROPUESTA = "En este estudio se midió la ansiedad de 84 estudiantes.";

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

const sesion = {
  cuenta: "CASO-01-A",
  rol: "A1",
  debe_cambiar_contrasena: false,
  expira_en: "2026-11-30T00:00:00Z",
  csrf: "t",
};

const vista = {
  id: SOLICITUD,
  estado: "entregada",
  motivo: null,
  creada_en: "2026-11-26T10:00:00Z",
  entregada_en: "2026-11-26T10:01:00Z",
  parrafo_id: "p4",
  abstencion: false,
  aviso: null,
  etiqueta: null,
  original: ORIGINAL,
  propuesta: PROPUESTA,
  palabras_original: 13,
  palabras_propuesta: 10,
  limite_palabras_propuesta: 15,
  cambios: [
    {
      tipo: "fluidez_y_precision_lexica",
      tipo_nombre: "Fluidez y precisión léxica",
      antes: "se hizo una medición de",
      despues: "se midió",
      razon: "Un verbo preciso en lugar de uno genérico.",
      citas: [
        {
          identificador: "F1",
          texto: "Se prefieren verbos precisos a verbos genéricos.",
          guia: "Guía de redacción académica",
          apartado: "Fluidez y precisión léxica",
        },
      ],
    },
  ],
  notas_para_el_estudiante: [],
  advertencias: [],
  comprobaciones: [],
};

function apiFicticia(llamadas: Request[], rechazar = false) {
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/redaccion/parrafos") {
      return Promise.resolve(
        respuestaJson({
          limite_palabras: 250,
          parrafos: [
            {
              id: "p4",
              seccion: "2. Método",
              texto: ORIGINAL,
              palabras: 13,
              dentro_del_limite: true,
            },
            {
              id: "p9",
              seccion: "4. Discusión",
              texto: "Un párrafo muy largo.",
              palabras: 310,
              dentro_del_limite: false,
            },
          ],
        }),
      );
    }
    if (ruta === "/caso/redaccion" && peticion.method === "POST") {
      if (rechazar) {
        return Promise.resolve(
          respuestaJson(
            {
              codigo: "alcance_demasiado_largo",
              mensaje:
                "El párrafo tiene 310 palabras y la propuesta de redacción admite hasta 250." +
                " Seleccione un fragmento más corto.",
              incidencia_id: "x",
            },
            422,
          ),
        );
      }
      return Promise.resolve(
        respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: vista.creada_en }, 202),
      );
    }
    if (ruta === `/caso/redaccion/${SOLICITUD}`) return Promise.resolve(respuestaJson(vista));
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

function abrir() {
  render(
    <MemoryRouter initialEntries={["/panel/redaccion"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("comparación palabra por palabra", () => {
  it("marca lo quitado en el original y lo agregado en la propuesta", () => {
    const { original, propuesta } = compararPalabras(ORIGINAL, PROPUESTA);
    expect(original.filter((t) => t.tipo === "quitado").map((t) => t.texto)).toEqual([
      "hizo una medición de",
    ]);
    expect(propuesta.filter((t) => t.tipo === "agregado").map((t) => t.texto)).toEqual(["midió"]);
    expect(propuesta.map((t) => t.texto).join(" ")).toBe(PROPUESTA);
  });

  it("textos iguales no tienen cambios", () => {
    const { original } = compararPalabras("Uno dos tres.", "Uno  dos tres.");
    expect(original).toEqual([{ tipo: "igual", texto: "Uno dos tres." }]);
  });
});

describe("propuesta de redacción", () => {
  it("muestra el original y la propuesta lado a lado con cada cambio y su pauta", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(llamadas));
    const usuario = userEvent.setup();
    abrir();
    await usuario.click(await screen.findByRole("button", { name: /Párrafo/ }));
    await usuario.click(await screen.findByRole("option", { name: /2\. Método/ }));
    expect(screen.getByText("Párrafo elegido (13 palabras)")).toBeVisible();
    await usuario.click(screen.getByRole("button", { name: "Proponer una redacción" }));

    expect(
      await screen.findByRole("heading", { name: "Propuesta de redacción" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    const original = screen.getByRole("region", { name: "Original (13 palabras)" });
    expect(within(original).getByText("hizo una medición de").tagName).toBe("DEL");
    const propuesta = screen.getByRole("region", {
      name: "Propuesta (10 palabras, hasta 15)",
    });
    expect(within(propuesta).getByText("midió").tagName).toBe("INS");
    const cambios = screen.getByRole("list", { name: "Cambios propuestos" });
    expect(within(cambios).getByText("Fluidez y precisión léxica")).toBeVisible();
    const pauta = within(cambios).getByText(/Pauta F1: Guía de redacción académica/);
    await usuario.click(pauta);
    expect(pauta.closest("details")).toHaveAttribute("open");
    const envio = llamadas.find((p) => p.method === "POST");
    expect(await envio?.json()).toEqual({ parrafo_id: "p4" });
  }, 10000);

  it("CP-09: un párrafo que excede el límite muestra el motivo y no se procesa", async () => {
    vi.stubGlobal("fetch", apiFicticia([], true));
    const usuario = userEvent.setup();
    abrir();
    await usuario.click(await screen.findByRole("button", { name: /Párrafo/ }));
    await usuario.click(await screen.findByRole("option", { name: /excede el límite/ }));
    await usuario.click(screen.getByRole("button", { name: "Proponer una redacción" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Seleccione un fragmento más corto");
    expect(screen.queryByRole("heading", { name: "Propuesta de redacción" })).toBeNull();
  });
});

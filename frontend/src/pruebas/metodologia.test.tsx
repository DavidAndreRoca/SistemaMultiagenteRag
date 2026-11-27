import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "77777777-7777-4777-8777-777777777777";

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
  seccion_id: "s3",
  seccion_titulo: "2. Método",
  diseno: "correlacional",
  abstencion: false,
  aviso: null,
  etiqueta: null,
  hallazgos: [
    {
      indicador: "justificacion_del_diseno",
      indicador_nombre: "Justificación del diseño",
      ubicacion: "p9",
      descripcion: "Se afirma causalidad con un diseño correlacional (COR-6).",
      severidad: "alta",
      recomendacion: "Hable de asociación entre variables, no de efecto.",
      citas: [
        {
          identificador: "F1",
          texto: "COR-6. La interpretación no afirma causalidad.",
          guia: "Listas de comprobación por tipo de diseño de investigación",
          apartado: "Diseño correlacional",
        },
      ],
    },
  ],
  preguntas_al_estudiante: ["¿Cómo se seleccionó la muestra?"],
  notas_para_el_estudiante: [],
  advertencias: [],
  comprobaciones: [],
};

function apiFicticia(llamadas: Request[]) {
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/metodologia/secciones") {
      return Promise.resolve(
        respuestaJson([
          { id: "s2", titulo: "1. Introducción", palabras: 300, diseno: null },
          { id: "s3", titulo: "2. Método", palabras: 180, diseno: "correlacional" },
        ]),
      );
    }
    if (ruta === "/caso/metodologia" && peticion.method === "POST") {
      return Promise.resolve(
        respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: vista.creada_en }, 202),
      );
    }
    if (ruta === `/caso/metodologia/${SOLICITUD}`) return Promise.resolve(respuestaJson(vista));
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("diagnóstico metodológico", () => {
  it("propone la sección de método y muestra preguntas y hallazgos con su criterio", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(llamadas));
    const usuario = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/panel/metodologia"]}>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("button", {
        name: /2\. Método \(180 palabras, diseño correlacional\)/,
      }),
    ).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Revisar la metodología" }));

    expect(
      await screen.findByRole(
        "heading",
        { name: "Diagnóstico metodológico: 2. Método" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Diseño declarado: correlacional/)).toBeVisible();
    const preguntas = screen.getByRole("list", { name: "Preguntas sobre lo que falta" });
    expect(within(preguntas).getByText("¿Cómo se seleccionó la muestra?")).toBeVisible();
    const lista = screen.getByRole("list", { name: "Hallazgos, de mayor a menor severidad" });
    expect(within(lista).getByText("Severidad Alta")).toBeVisible();
    const criterio = within(lista).getByText(/Criterio F1: Listas de comprobación/);
    await usuario.click(criterio);
    expect(criterio.closest("details")).toHaveAttribute("open");
    const envio = llamadas.find((p) => p.method === "POST");
    expect(await envio?.json()).toEqual({ seccion_id: "s3" });
  }, 10000);
});

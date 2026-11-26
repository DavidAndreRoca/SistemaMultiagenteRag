import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "88888888-8888-4888-8888-888888888888";

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
  seccion_id: "s2",
  seccion_titulo: "1. Introducción",
  abstencion: false,
  aviso: null,
  etiqueta: null,
  hallazgos: [
    {
      indicador: "alineacion_problema_objetivos_hipotesis",
      indicador_nombre: "Alineación entre problema, objetivos e hipótesis",
      ubicacion: "p5",
      descripcion: "El objetivo no retoma la variable del problema.",
      severidad: "alta",
      recomendacion: "Revise que el objetivo nombre las mismas variables que el problema.",
      citas: [
        {
          identificador: "F1",
          texto:
            "El problema, los objetivos y las hipótesis deben referirse a las mismas variables.",
          guia: "Guía de estructura y coherencia",
          apartado: "Alineación entre problema, objetivos e hipótesis",
        },
      ],
    },
  ],
  fortalezas: ["El problema se apoya en antecedentes."],
  notas_para_el_estudiante: ["Para el diseño, pida la revisión metodológica."],
  advertencias: [],
  comprobaciones: [],
};

function apiFicticia(llamadas: Request[]) {
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/estructura/secciones") {
      return Promise.resolve(
        respuestaJson([
          { id: "s1", titulo: "Resumen", palabras: 120 },
          { id: "s2", titulo: "1. Introducción", palabras: 480 },
        ]),
      );
    }
    if (ruta === "/caso/estructura" && peticion.method === "POST") {
      return Promise.resolve(
        respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: vista.creada_en }, 202),
      );
    }
    if (ruta === `/caso/estructura/${SOLICITUD}`) return Promise.resolve(respuestaJson(vista));
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("estructura y coherencia", () => {
  it("revisa la sección elegida y muestra los hallazgos con sus criterios", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(llamadas));
    const usuario = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/panel/estructura"]}>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </MemoryRouter>,
    );
    await usuario.click(await screen.findByRole("button", { name: /Sección/ }));
    await usuario.click(await screen.findByRole("option", { name: /1\. Introducción/ }));
    await usuario.click(screen.getByRole("button", { name: "Revisar la sección" }));

    expect(
      await screen.findByRole(
        "heading",
        { name: "Diagnóstico: 1. Introducción" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    const lista = screen.getByRole("list", { name: "Hallazgos, de mayor a menor severidad" });
    expect(within(lista).getByText("Severidad Alta")).toBeVisible();
    expect(
      within(lista).getByText(/Revise que el objetivo nombre las mismas variables/),
    ).toBeVisible();
    const criterio = within(lista).getByText(/Criterio F1: Guía de estructura y coherencia/);
    await usuario.click(criterio);
    expect(criterio.closest("details")).toHaveAttribute("open");
    expect(screen.getByText("El problema se apoya en antecedentes.")).toBeVisible();
    const envio = llamadas.find((p) => p.method === "POST");
    expect(await envio?.json()).toEqual({ seccion_id: "s2" });
  }, 10000);
});

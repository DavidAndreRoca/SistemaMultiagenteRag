import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { planEnTexto } from "../paginas/Plan";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "66666666-6666-4666-8666-666666666666";

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
  estado: "entregada" as const,
  motivo: null,
  creada_en: "2026-11-26T10:00:00Z",
  entregada_en: "2026-11-26T10:01:00Z",
  hito: "Avance 1: Planteamiento",
  abstencion: false,
  aviso: null,
  motivo_abstencion: null,
  etiqueta: "verificada" as const,
  tareas: [
    {
      orden: 1,
      tarea: "Redactar la formulación del problema general.",
      criterio_de_logro: "El problema nombra las variables y la población.",
      citas: [
        {
          identificador: "F1",
          texto: "El estudiante entrega el título provisional y el problema.",
          guia: "Instrucciones del programa por hito",
          apartado: "Avance 1: Planteamiento",
        },
      ],
    },
    {
      orden: 2,
      tarea: "Redactar los objetivos general y específicos.",
      criterio_de_logro: "Cada objetivo empieza con un verbo en infinitivo.",
      citas: [],
    },
  ],
  notas_para_el_estudiante: ["Para el método, pida la revisión metodológica."],
  advertencias: [],
  comprobaciones: [],
};

const abstencion = {
  ...vista,
  abstencion: true,
  aviso: "Sin evidencia suficiente",
  motivo_abstencion: "El corpus de guías no tiene instrucciones del hito Avance 1: Planteamiento.",
  tareas: [],
  notas_para_el_estudiante: [],
};

function apiFicticia(llamadas: Request[], resultado: unknown) {
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/plan/hitos") {
      return Promise.resolve(
        respuestaJson([
          {
            codigo: "avance_1",
            nombre: "Avance 1: Planteamiento",
            version_cargada_en: "2026-11-26T09:00:00Z",
          },
          { codigo: "avance_2", nombre: "Avance 2: Metodología", version_cargada_en: null },
        ]),
      );
    }
    if (ruta === "/caso/plan" && peticion.method === "POST") {
      return Promise.resolve(
        respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: vista.creada_en }, 202),
      );
    }
    if (ruta === `/caso/plan/${SOLICITUD}`) return Promise.resolve(respuestaJson(resultado));
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

function abrir() {
  render(
    <MemoryRouter initialEntries={["/panel/plan"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("plan de tarea", () => {
  it("prepara el plan del hito con versión y muestra las tareas en orden", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(llamadas, vista));
    const usuario = userEvent.setup();
    abrir();
    // Solo se ofrecen los hitos con versión cargada, y viene elegido el último.
    expect(await screen.findByRole("button", { name: /Avance 1: Planteamiento/ })).toBeVisible();
    await usuario.click(screen.getByRole("button", { name: "Preparar el plan" }));
    expect(
      await screen.findByRole(
        "heading",
        { name: "Plan de tarea: Avance 1: Planteamiento" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    const tareas = screen.getByRole("list", { name: "Tareas, en orden" });
    expect(within(tareas).getAllByRole("listitem")).toHaveLength(2);
    expect(within(tareas).getByText(/Redactar la formulación del problema/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Descargar en texto" })).toBeVisible();
    expect(screen.getByText("Verificada")).toBeVisible();
    const envio = llamadas.find((p) => p.method === "POST");
    expect(await envio?.json()).toEqual({ hito: "avance_1" });
  }, 10000);

  it("sin instrucciones del hito explica la abstención", async () => {
    vi.stubGlobal("fetch", apiFicticia([], abstencion));
    const usuario = userEvent.setup();
    abrir();
    await usuario.click(await screen.findByRole("button", { name: "Preparar el plan" }));
    expect(
      await screen.findByRole("heading", { name: "Sin evidencia suficiente" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/no tiene instrucciones del hito/)).toBeVisible();
  }, 10000);

  it("el plan en texto lleva cada tarea con su criterio y las notas", () => {
    expect(planEnTexto(vista)).toBe(
      "Plan de tarea: Avance 1: Planteamiento\n\n" +
        "1. Redactar la formulación del problema general.\n" +
        "   Criterio de logro: El problema nombra las variables y la población.\n" +
        "2. Redactar los objetivos general y específicos.\n" +
        "   Criterio de logro: Cada objetivo empieza con un verbo en infinitivo.\n\n" +
        "Notas:\n- Para el método, pida la revisión metodológica.\n",
    );
  });
});

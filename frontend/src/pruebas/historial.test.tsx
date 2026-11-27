import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "99999999-9999-4999-8999-999999999999";

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

const caso = {
  codigo: "CASO-01",
  tema: "TEMA-01",
  tipo_autoria: "individual",
  norma_citacion: "apa",
  hitos: [
    { orden: 1, codigo: "avance_1", nombre: "Avance 1", contenido: "Planteamiento" },
    { orden: 2, codigo: "avance_2", nombre: "Avance 2", contenido: "Metodología" },
  ],
};

function evento(cambios: Record<string, unknown>) {
  return {
    momento: "2026-11-27T15:00:00Z",
    clase: "version",
    descripcion: "Cargó una versión de su borrador (500 palabras).",
    hito: "avance_1",
    nombre_hito: "Avance 1",
    solicitud_id: null,
    tipo: null,
    estado: null,
    etiqueta: null,
    opcion: null,
    vigente: true,
    ...cambios,
  };
}

const eventos = [
  evento({}),
  evento({
    clase: "resultado",
    descripcion: "Recibió el resultado: Verificada.",
    solicitud_id: SOLICITUD,
    tipo: "revision_estructura",
    estado: "entregada",
    etiqueta: "verificada",
    vigente: null,
  }),
  evento({
    clase: "decision",
    descripcion: "Decidió sobre el resultado: la aceptó.",
    solicitud_id: SOLICITUD,
    tipo: "revision_estructura",
    opcion: "aceptar",
    vigente: false,
  }),
];

function apiFicticia(consultas: URLSearchParams[]) {
  return vi.fn((peticion: Request) => {
    const url = new URL(peticion.url);
    const ruta = url.pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso") return Promise.resolve(respuestaJson(caso));
    if (ruta === "/caso/historial") {
      consultas.push(url.searchParams);
      const filtrado = url.searchParams.get("hito") === "avance_2";
      return Promise.resolve(respuestaJson({ eventos: filtrado ? [] : eventos }));
    }
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

function abrir() {
  render(
    <MemoryRouter initialEntries={["/panel/historial"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("historial del caso", () => {
  it("muestra la trayectoria con su etiqueta y el enlace al detalle", async () => {
    vi.stubGlobal("fetch", apiFicticia([]));
    abrir();
    const tabla = await screen.findByRole("table", { name: /Historial del caso/ });
    const filas = within(tabla).getAllByRole("row");
    expect(filas).toHaveLength(4); // encabezado y tres eventos
    expect(filas[2]).toHaveTextContent("Verificada");
    expect(filas[3]).toHaveTextContent("Reemplazada");
    expect(within(filas[2] as HTMLElement).getByRole("link", { name: /Ver/ })).toHaveAttribute(
      "href",
      `/panel/estructura?solicitud=${SOLICITUD}`,
    );
    expect(
      screen.getByRole("link", {
        name: "Descargar el resumen para su declaración de herramientas",
      }),
    ).toHaveAttribute("href", "/api/caso/historial/resumen?");
  });

  it("filtra por hito y periodo, y lo aplica también a la descarga", async () => {
    const consultas: URLSearchParams[] = [];
    vi.stubGlobal("fetch", apiFicticia(consultas));
    const usuario = userEvent.setup();
    abrir();
    await screen.findByRole("table", { name: /Historial del caso/ });
    await usuario.click(screen.getByRole("button", { name: /Hito/ }));
    await usuario.click(await screen.findByRole("option", { name: /Avance 2/ }));
    await usuario.type(screen.getByLabelText("Desde"), "2026-11-01");
    await usuario.click(screen.getByRole("button", { name: "Aplicar el filtro" }));
    expect(await screen.findByText("No hay registros con este filtro.")).toBeVisible();
    const ultima = consultas.at(-1);
    expect(ultima?.get("hito")).toBe("avance_2");
    expect(ultima?.get("desde")).toBe("2026-11-01");
    expect(ultima?.has("hasta")).toBe(false);
    expect(
      screen.getByRole("link", {
        name: "Descargar el resumen para su declaración de herramientas",
      }),
    ).toHaveAttribute("href", "/api/caso/historial/resumen?hito=avance_2&desde=2026-11-01");
  });

  it("avisa de una fecha mal escrita sin consultar", async () => {
    const consultas: URLSearchParams[] = [];
    vi.stubGlobal("fetch", apiFicticia(consultas));
    const usuario = userEvent.setup();
    abrir();
    await screen.findByRole("table", { name: /Historial del caso/ });
    await usuario.type(screen.getByLabelText("Hasta"), "27/11/2026");
    await usuario.click(screen.getByRole("button", { name: "Aplicar el filtro" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("AAAA-MM-DD");
    expect(consultas).toHaveLength(1);
  });
});

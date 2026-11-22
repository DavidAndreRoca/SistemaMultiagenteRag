// Las validaciones de la propia interfaz se muestran con su mensaje, no como un error
// inesperado (pendiente de T11 y T13, corregido antes de T17).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { errorDeValidacion } from "../api/cliente";
import { App } from "../App";
import { AvisoError } from "../componentes/controles";
import { ProveedorSesion } from "../sesion/sesion";

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AvisoError", () => {
  it("muestra tal cual el mensaje de una validación de la interfaz", () => {
    render(<AvisoError error={errorDeValidacion("Elija el hito y el archivo .docx.")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Elija el hito y el archivo .docx.");
    expect(screen.queryByText(/Identificador de incidencia/)).toBeNull();
  });

  it("no muestra el texto técnico de un error imprevisto", () => {
    render(<AvisoError error={new TypeError("x is undefined")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Ocurrió un error inesperado.");
  });
});

describe("panel del caso", () => {
  it("sin archivo, pide el hito y el archivo con su mensaje y no llama a la API", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((peticion: Request) => {
        llamadas.push(peticion);
        const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
        if (ruta === "/sesion") {
          return Promise.resolve(
            respuestaJson({
              cuenta: "CASO-01-A",
              rol: "A1",
              debe_cambiar_contrasena: false,
              expira_en: "2026-11-30T00:00:00Z",
              csrf: "t",
            }),
          );
        }
        if (ruta === "/caso") {
          return Promise.resolve(
            respuestaJson({
              codigo: "CASO-01",
              tema: "TEMA-01",
              tipo_autoria: "individual",
              norma_citacion: "apa",
              hitos: [
                { codigo: "avance_1", nombre: "Avance 1", contenido: "Planteamiento", orden: 1 },
              ],
            }),
          );
        }
        if (ruta === "/caso/versiones") return Promise.resolve(respuestaJson([]));
        return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
      }),
    );
    const usuario = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/panel"]}>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </MemoryRouter>,
    );
    await usuario.click(await screen.findByRole("button", { name: /Hito/ }));
    await usuario.click(await screen.findByRole("option", { name: /Avance 1/ }));
    await usuario.click(screen.getByRole("button", { name: "Cargar la versión" }));

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("Elija el hito y el archivo .docx de su borrador.");
    expect(aviso).not.toHaveTextContent("Ocurrió un error inesperado.");
    expect(llamadas.some((p) => p.method === "POST")).toBe(false);
  });
});

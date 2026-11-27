import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AvanceSolicitud, NoAtendida, OtraRevision } from "../componentes/Seguimiento";

const SOLICITUD = "55555555-5555-4555-8555-555555555555";
const NUEVA = "44444444-4444-4444-8444-444444444444";

class FuenteFicticia {
  static ultima: FuenteFicticia | null = null;
  url: string;
  cerrada = false;
  private oyentes: ((evento: MessageEvent<string>) => void)[] = [];

  constructor(url: string) {
    this.url = url;
    FuenteFicticia.ultima = this;
  }

  addEventListener(_tipo: string, oyente: (evento: MessageEvent<string>) => void) {
    this.oyentes.push(oyente);
  }

  close() {
    this.cerrada = true;
  }

  emitir(estado: string, intentos = 0) {
    const datos = JSON.stringify({ estado, motivo: null, intentos_tecnicos: intentos });
    for (const oyente of this.oyentes) oyente(new MessageEvent("estado", { data: datos }));
  }
}

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  FuenteFicticia.ultima = null;
});

describe("avance de una solicitud", () => {
  it("muestra cada estado que llega por el canal y avisa al terminar", () => {
    vi.stubGlobal("EventSource", FuenteFicticia);
    const alTerminar = vi.fn();
    render(
      <AvanceSolicitud
        solicitud={SOLICITUD}
        mensaje="Revisando la sección."
        alTerminar={alTerminar}
      />,
    );
    const fuente = FuenteFicticia.ultima;
    expect(fuente?.url).toBe(`/api/caso/solicitudes/${SOLICITUD}/eventos`);
    act(() => fuente?.emitir("recuperando"));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Revisando la sección. Estado: Buscando en las guías y fuentes.",
    );
    const pasos = screen.getByRole("list", { name: "Avance de la solicitud" });
    expect(within(pasos).getByText("Buscando en las guías y fuentes")).toHaveAttribute(
      "aria-current",
      "step",
    );
    expect(within(pasos).getByText("En cola")).toHaveTextContent("(hecho)");
    act(() => fuente?.emitir("entregada"));
    expect(alTerminar).toHaveBeenCalledOnce();
    expect(fuente?.cerrada).toBe(true);
  });

  it("avisa cuando el servicio del modelo no respondió y se reintentará", () => {
    vi.stubGlobal("EventSource", FuenteFicticia);
    render(<AvanceSolicitud solicitud={SOLICITUD} mensaje="Buscando evidencia." />);
    act(() => FuenteFicticia.ultima?.emitir("recibida", 1));
    expect(screen.getByText(/lo intentará de nuevo \(intento 2 de 4\)/)).toBeVisible();
  });

  it("sin EventSource muestra el mensaje y la pantalla sigue consultando", () => {
    vi.stubGlobal("EventSource", undefined);
    render(<AvanceSolicitud solicitud={SOLICITUD} mensaje="Revisando la sección." />);
    expect(screen.getByRole("status")).toHaveTextContent("Revisando la sección.");
    expect(screen.queryByRole("list")).toBeNull();
  });
});

describe("reenvío y mismo alcance", () => {
  it("vuelve a pedir una solicitud no atendida y sigue a la nueva", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((peticion: Request) => {
        llamadas.push(peticion);
        return Promise.resolve(
          respuestaJson(
            {
              id: NUEVA,
              tipo: "busqueda_evidencia",
              estado: "recibida",
              creada_en: "2026-11-27T10:00:00Z",
              solicitud_origen_id: SOLICITUD,
            },
            202,
          ),
        );
      }),
    );
    const alReenviar = vi.fn();
    render(
      <NoAtendida solicitud={SOLICITUD} mensaje="No pudo atenderse." alReenviar={alReenviar} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No pudo atenderse.");
    await userEvent.setup().click(screen.getByRole("button", { name: "Volver a pedir" }));
    expect(alReenviar).toHaveBeenCalledWith(NUEVA);
    expect(new URL(llamadas[0]?.url ?? "").pathname).toBe(
      `/api/caso/solicitudes/${SOLICITUD}/reenvio`,
    );
  });

  it("pide la otra revisión de la misma sección y abre su pantalla", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((peticion: Request) => {
        llamadas.push(peticion);
        return Promise.resolve(
          respuestaJson(
            {
              id: NUEVA,
              tipo: "revision_metodologica",
              estado: "recibida",
              creada_en: "2026-11-27T10:00:00Z",
              solicitud_origen_id: null,
            },
            202,
          ),
        );
      }),
    );
    render(
      <MemoryRouter initialEntries={["/panel/estructura"]}>
        <Routes>
          <Route
            path="/panel/estructura"
            element={
              <OtraRevision
                solicitud={SOLICITUD}
                tipo="revision_metodologica"
                ruta="/panel/metodologia"
                texto="Revisar también la metodología de esta sección"
              />
            }
          />
          <Route path="/panel/metodologia" element={<p>Pantalla de metodología</p>} />
        </Routes>
      </MemoryRouter>,
    );
    await userEvent
      .setup()
      .click(
        screen.getByRole("button", { name: "Revisar también la metodología de esta sección" }),
      );
    expect(await screen.findByText("Pantalla de metodología")).toBeVisible();
    expect(await llamadas[0]?.json()).toEqual({ tipo: "revision_metodologica" });
  });
});

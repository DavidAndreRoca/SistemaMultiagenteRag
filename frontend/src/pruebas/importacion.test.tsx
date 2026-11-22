import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/cliente";
import { App } from "../App";
import { motivo } from "../paginas/Importacion";
import { ProveedorSesion } from "../sesion/sesion";

const COLECCION = "11111111-1111-4111-8111-111111111111";
const IMPORTACION = "22222222-2222-4222-8222-222222222222";
const REFERENCIA = "33333333-3333-4333-8333-333333333333";

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

const sesion = {
  cuenta: "INV-01",
  rol: "A2",
  debe_cambiar_contrasena: false,
  expira_en: "2026-11-30T00:00:00Z",
  csrf: "t",
};
const coleccion = {
  id: COLECCION,
  tipo: "cientifica",
  tema: "TEMA-01",
  n_incluidas: 9,
  n_excluidas: 8,
  n_pendientes: 1,
};
function importacion(estado: string, procesadas = 0) {
  return {
    id: IMPORTACION,
    coleccion_id: COLECCION,
    origen: "doi",
    estado,
    total: 2,
    procesadas,
    error: null,
    creada_en: "2026-11-22T10:00:00Z",
    iniciada_en: null,
    terminada_en: null,
  };
}
const informe = {
  coleccion_id: COLECCION,
  tema: "TEMA-01",
  referencias: 24,
  de_acceso_abierto: 15,
  incluidas: 9,
  pendientes_pdf: 5,
  no_comprobables: 2,
  excluidas: 8,
  excluidas_por_motivo: { sin_acceso_abierto: 4, sin_doi: 1 },
  documentos_recuperables: 9,
  exclusiones_del_corpus: 8,
};
function referencia(estado: string, motivoDeEstado: string | null) {
  return {
    id: REFERENCIA,
    texto: "Cárdenas, D. (2019). Ansiedad matemática y elección de carrera. Revista Ficticia.",
    doi: "10.5555/sma.o1.10",
    titulo: "Ansiedad matemática y elección de carrera",
    autores: ["Cárdenas"],
    anio: 2019,
    estado,
    motivo: motivoDeEstado,
    estado_oa: "gold",
    url_acceso_abierto: "https://repositorio.example/10.5555/sma.o1.10",
    url_pdf: null,
    licencia: "cc-by",
    documento_id: estado === "incluida" ? "44444444-4444-4444-8444-444444444444" : null,
    actualizada_en: "2026-11-22T10:00:00Z",
  };
}

/** Responde como la API según el método y la ruta, y guarda cada petición. */
function apiFicticia(llamadas: Request[], estado = { subido: false }) {
  let consultas = 0;
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    const metodo = peticion.method;
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/investigador/colecciones") return Promise.resolve(respuestaJson([coleccion]));
    if (ruta.endsWith("/importaciones") && metodo === "POST") {
      return Promise.resolve(respuestaJson(importacion("en_cola"), 202));
    }
    if (ruta === `/investigador/importaciones/${IMPORTACION}`) {
      consultas += 1;
      return Promise.resolve(
        respuestaJson(consultas === 1 ? importacion("en_proceso", 1) : importacion("terminada", 2)),
      );
    }
    if (ruta.endsWith("/informe")) return Promise.resolve(respuestaJson(informe));
    if (ruta.endsWith("/referencias")) {
      return Promise.resolve(
        respuestaJson(estado.subido ? [] : [referencia("pendiente_pdf", "sin_enlace_directo")]),
      );
    }
    if (ruta === `/investigador/referencias/${REFERENCIA}/pdf`) {
      estado.subido = true;
      return Promise.resolve(respuestaJson(referencia("incluida", null)));
    }
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

async function elegirTema(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.click(await screen.findByRole("button", { name: /Tema/ }));
  await usuario.click(await screen.findByRole("option", { name: "TEMA-01" }));
}

function entradaDeArchivo(raiz: Element): HTMLInputElement {
  const entrada = raiz.querySelector<HTMLInputElement>('input[type="file"]');
  if (entrada === null) throw new Error("falta el selector de archivo");
  return entrada;
}

function montar() {
  return render(
    <MemoryRouter initialEntries={["/investigador/importacion"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("importación de referencias", () => {
  it("importa una lista de DOI y sigue el avance hasta terminar", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(llamadas));
    const usuario = userEvent.setup();
    montar();
    expect(
      await screen.findByRole("heading", { name: "Importar referencias del artículo O1" }),
    ).toBeInTheDocument();
    await elegirTema(usuario);

    await usuario.type(
      screen.getByRole("textbox", { name: "O pegue la lista de DOI" }),
      "10.5555/sma.o1.01",
    );
    await usuario.click(screen.getByRole("button", { name: "Importar las referencias" }));
    expect(await screen.findByText("La importación está en cola.")).toBeInTheDocument();
    expect(
      await screen.findByText(/Importación terminada/, undefined, { timeout: 6000 }),
    ).toBeInTheDocument();

    const envio = llamadas.find((p) => p.method === "POST");
    expect(envio?.url).toContain(`/investigador/colecciones/${COLECCION}/importaciones`);
    const formulario = await envio?.formData();
    expect(formulario?.get("dois")).toBe("10.5555/sma.o1.01");
    expect(formulario?.get("archivo")).toBeNull();
  }, 10000);

  it("pide el artículo o los DOI, pero no ambos", async () => {
    vi.stubGlobal("fetch", apiFicticia([]));
    const usuario = userEvent.setup();
    const { container } = montar();
    await elegirTema(usuario);
    const selector = entradaDeArchivo(container);
    await usuario.upload(
      selector,
      new File(["%PDF-1.4"], "articulo.pdf", { type: "application/pdf" }),
    );
    await usuario.type(screen.getByRole("textbox", { name: "O pegue la lista de DOI" }), "10.1/x");
    await usuario.click(screen.getByRole("button", { name: "Importar las referencias" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Suba el artículo o pegue la lista de DOI, pero no ambos.",
    );
  });

  it("muestra el informe y deja subir el PDF de una pendiente", async () => {
    const estado = { subido: false };
    vi.stubGlobal("fetch", apiFicticia([], estado));
    // En jsdom, fetch no acepta un File dentro de un FormData: se sustituye el envío.
    const envio = vi.spyOn(api, "POST").mockImplementation(() => {
      estado.subido = true;
      return Promise.resolve({
        data: referencia("incluida", null),
        response: new Response(null, { status: 200 }),
      }) as never;
    });
    const usuario = userEvent.setup();
    montar();
    await elegirTema(usuario);

    const tabla = await screen.findByRole("table", { name: "Referencias del tema por estado" });
    expect(within(tabla).getByRole("row", { name: "Incluidas en la colección 9" })).toBeVisible();
    expect(within(tabla).getByRole("row", { name: "Pendientes de PDF 5" })).toBeVisible();
    const motivos = screen.getByRole("table", { name: "Excluidas por motivo" });
    expect(within(motivos).getByRole("row", { name: "Sin acceso abierto 4" })).toBeVisible();

    const enlace = await screen.findByRole("link", { name: /Abrir la página de acceso abierto/ });
    expect(enlace).toHaveAttribute("href", "https://repositorio.example/10.5555/sma.o1.10");
    expect(enlace).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/Sin enlace directo al PDF\. Licencia: cc-by/)).toBeInTheDocument();

    const pendiente = screen.getByRole("listitem");
    const selector = entradaDeArchivo(pendiente);
    await usuario.upload(
      selector,
      new File(["%PDF-1.4"], "bajado.pdf", { type: "application/pdf" }),
    );
    await usuario.click(within(pendiente).getByRole("button", { name: "Subir el PDF" }));
    expect(
      await screen.findByText("PDF indexado: la referencia quedó incluida."),
    ).toBeInTheDocument();
    expect(await screen.findByText("No hay referencias pendientes de PDF.")).toBeInTheDocument();
    expect(envio).toHaveBeenCalledOnce();
    const [ruta, opciones] = envio.mock.calls[0] as unknown as [
      string,
      { params: { path: { referencia_id: string } }; body: FormData },
    ];
    expect(ruta).toBe("/investigador/referencias/{referencia_id}/pdf");
    expect(opciones.params.path.referencia_id).toBe(REFERENCIA);
    expect((opciones.body.get("archivo") as File).name).toBe("bajado.pdf");
  });
});

describe("motivos", () => {
  it("traduce cada motivo y agrupa las caídas de servicios", () => {
    expect(motivo("sin_doi")).toBe("Sin DOI");
    expect(motivo("crossref_error_del_servicio")).toBe("Crossref u OpenAlex no respondieron");
    expect(motivo("unpaywall_tiempo_agotado")).toBe("Unpaywall no respondió");
    expect(motivo("otro_motivo")).toBe("otro_motivo");
    expect(motivo(null)).toBe("");
  });
});

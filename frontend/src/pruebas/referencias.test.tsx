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

const referencia = (indice: number, estado: string, cambios: Record<string, unknown> = {}) => ({
  indice,
  texto_original: `[${String(indice)}] Referencia ficticia ${String(indice)}.`,
  estado,
  metodo: "doi",
  discrepancias: [],
  doi_encontrado: null,
  url_doi: null,
  explicacion: null,
  citada: true,
  ...cambios,
});

function vista(cambios: Record<string, unknown>) {
  return {
    id: SOLICITUD,
    estado: "entregada",
    motivo: null,
    creada_en: "2026-11-25T10:00:00Z",
    entregada_en: "2026-11-25T10:02:00Z",
    norma: "ieee",
    norma_nombre: "IEEE",
    progreso: null,
    resumen: { verificada: 1, con_discrepancias: 1, no_localizada: 1, no_comprobable: 1 },
    referencias: [
      referencia(1, "verificada", {
        doi_encontrado: "10.5555/t20.quispe.2021",
        url_doi: "https://doi.org/10.5555/t20.quispe.2021",
      }),
      referencia(2, "con_discrepancias", {
        discrepancias: [
          { campo: "anio", etiqueta: "Año", valor_borrador: "2022", valor_fuente: "2021" },
        ],
        explicacion: "Revise si cita la fecha impresa o la de publicación en línea.",
      }),
      referencia(3, "no_localizada", { metodo: "metadatos", citada: false }),
      referencia(4, "no_comprobable"),
    ],
    citas_sin_entrada: ["[12]"],
    entradas_no_citadas: [{ indice: 3, texto: "[3] Referencia ficticia 3." }],
    avisos: [
      "La verificación no pudo completarse para 1 de las referencias porque un servicio bibliográfico no respondió.",
    ],
    etiqueta: null,
    advertencias: [],
    comprobaciones: [],
    ...cambios,
  };
}

function apiFicticia(post: Response, gets: unknown[], llamadas: Request[] = []) {
  let consultas = 0;
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/referencias" && peticion.method === "POST") {
      return Promise.resolve(post.clone());
    }
    if (ruta === `/caso/referencias/${SOLICITUD}`) {
      const actual = gets[Math.min(consultas, gets.length - 1)];
      consultas += 1;
      return Promise.resolve(respuestaJson(actual));
    }
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

const aceptada = () =>
  respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: "2026-11-25T10:00:00Z" }, 202);

async function verificar() {
  const usuario = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/panel/referencias"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
  await usuario.click(await screen.findByRole("button", { name: "Verificar las referencias" }));
  return usuario;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("verificación de referencias", () => {
  it("muestra el mensaje de la API cuando no se detectó la lista", async () => {
    const rechazo = respuestaJson(
      {
        codigo: "lista_no_detectada",
        mensaje:
          "No se detectó la lista de referencias de su versión. Póngale un título con estilo de título (por ejemplo, «Referencias» con el estilo Título 1), vuelva a cargar la versión y pida otra vez la verificación.",
      },
      422,
    );
    vi.stubGlobal("fetch", apiFicticia(rechazo, []));
    await verificar();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se detectó la lista de referencias de su versión. Póngale un título con estilo",
    );
  });

  it("informa el avance y después el estado de cada referencia", async () => {
    const enCurso = vista({ estado: "recuperando", progreso: { hechas: 4, total: 11 } });
    vi.stubGlobal("fetch", apiFicticia(aceptada(), [enCurso, vista({})]));
    await verificar();
    expect(
      await screen.findByText(/Verificando referencias: 4 de 11/, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Informe de referencias" }, { timeout: 5000 }),
    ).toBeInTheDocument();

    const lista = screen.getByRole("list", { name: "Estado de cada referencia" });
    const filas = Array.from(lista.children) as HTMLElement[];
    expect(filas).toHaveLength(4);
    const [primera, segunda, tercera, cuarta] = filas as [
      HTMLElement,
      HTMLElement,
      HTMLElement,
      HTMLElement,
    ];
    expect(primera).toHaveTextContent("Verificada");
    expect(within(primera).getByRole("link", { name: /Ver la obra en doi.org/ })).toHaveAttribute(
      "href",
      "https://doi.org/10.5555/t20.quispe.2021",
    );
    expect(segunda).toHaveTextContent("Con discrepancias");
    expect(segunda).toHaveTextContent("Año: en su referencia, 2022; en la fuente, 2021.");
    expect(segunda).toHaveTextContent("Revise si cita la fecha impresa");
    expect(tercera).toHaveTextContent("No localizada. No se cita en el texto");
    expect(cuarta).toHaveTextContent("No significa que la obra no exista.");

    expect(screen.getByText(/no pudo completarse para 1 de las referencias/)).toBeVisible();
    expect(
      within(screen.getByRole("list", { name: "Citas sin entrada" })).getByText("[12]"),
    ).toBeVisible();
    expect(
      within(screen.getByRole("list", { name: "Entradas no citadas" })).getByText(
        "Entrada 3: [3] Referencia ficticia 3.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Norma del caso: IEEE.")).toBeVisible();
  }, 15000);

  it("informa cuando la verificación no pudo atenderse", async () => {
    vi.stubGlobal(
      "fetch",
      apiFicticia(aceptada(), [vista({ estado: "no_atendida", motivo: "grobid_no_disponible" })]),
    );
    await verificar();
    expect(await screen.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
      "El servicio que estructura la lista de referencias no está disponible.",
    );
  }, 10000);
});

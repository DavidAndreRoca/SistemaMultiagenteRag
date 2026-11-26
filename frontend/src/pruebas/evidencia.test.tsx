import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ProveedorSesion } from "../sesion/sesion";

const SOLICITUD = "55555555-5555-4555-8555-555555555555";

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

const cita = (identificador: string, abierta: boolean) => ({
  identificador,
  texto: "La tutoría entre pares redujo la ansiedad ante la estadística en un grupo ficticio.",
  titulo: abierta ? "Tutoría entre pares (artículo ficticio)" : "Artículo ficticio cerrado",
  seccion: "resultados",
  pagina_inicio: 4,
  pagina_fin: 5,
  acceso_abierto: abierta,
  url_acceso_abierto: abierta ? "https://repositorio.example/a1" : null,
  incompleto: false,
});

function vista(cambios: Record<string, unknown>) {
  return {
    id: SOLICITUD,
    consulta: "Quiero sustentar que la tutoría entre pares reduce la ansiedad",
    estado: "entregada",
    motivo: null,
    creada_en: "2026-11-24T10:00:00Z",
    entregada_en: "2026-11-24T10:01:00Z",
    abstencion: false,
    aviso: null,
    invitacion_aporte: null,
    etiqueta: null,
    respuesta: [
      {
        afirmacion: "La tutoría entre pares reduce la ansiedad ante la estadística.",
        citas: [cita("F1", true)],
      },
    ],
    evidencia_divergente: [],
    notas_para_el_estudiante: ["La evidencia proviene de un solo contexto."],
    fuentes: [
      {
        documento_id: "66666666-6666-4666-8666-666666666666",
        referencia: "Quispe, A. (2021). Tutoría entre pares. Revista Ficticia de Pedagogía.",
        metodo: "csl_local",
        url_acceso_abierto: "https://repositorio.example/a1",
        identificadores: ["F1"],
      },
    ],
    advertencias: [],
    comprobaciones: [],
    ...cambios,
  };
}

/** El GET devuelve `get` o, si es una lista, cada elemento en orden (el último se repite). */
function apiFicticia(post: Response, get: unknown, llamadas: Request[] = []) {
  const respuestas = Array.isArray(get) ? get : [get];
  let consultas = 0;
  return vi.fn((peticion: Request) => {
    llamadas.push(peticion);
    const ruta = new URL(peticion.url).pathname.replace(/^\/api/, "");
    if (ruta === "/sesion") return Promise.resolve(respuestaJson(sesion));
    if (ruta === "/caso/evidencias" && peticion.method === "POST") {
      return Promise.resolve(post.clone());
    }
    if (ruta === `/caso/evidencias/${SOLICITUD}`) {
      const actual: unknown = respuestas[Math.min(consultas, respuestas.length - 1)];
      consultas += 1;
      return Promise.resolve(respuestaJson(actual));
    }
    return Promise.resolve(respuestaJson({ codigo: "no_existe", mensaje: "No existe." }, 404));
  });
}

const aceptada = () =>
  respuestaJson({ id: SOLICITUD, estado: "recibida", creada_en: "2026-11-24T10:00:00Z" }, 202);

async function buscar(consulta: string) {
  const usuario = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/panel/evidencia"]}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </MemoryRouter>,
  );
  await usuario.type(
    await screen.findByRole("textbox", { name: "Consulta o afirmación" }),
    consulta,
  );
  await usuario.click(screen.getByRole("button", { name: "Buscar evidencia" }));
  return usuario;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("búsqueda de evidencia", () => {
  it("muestra el motivo cuando la consulta se rechaza", async () => {
    const rechazo = respuestaJson(
      {
        codigo: "consulta_rechazada",
        mensaje: "Esta solicitud está fuera de lo que el sistema puede hacer. Por ejemplo: ...",
        detalle: { motivo: "fuera_de_alcance" },
      },
      422,
    );
    vi.stubGlobal("fetch", apiFicticia(rechazo, null));
    await buscar("Redacta la introducción completa de mi artículo");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Esta solicitud está fuera de lo que el sistema puede hacer.",
    );
  });

  it("entrega la respuesta con citas desplegables y fuentes de acceso abierto", async () => {
    const llamadas: Request[] = [];
    const conCerrada = vista({
      etiqueta: "con_advertencias",
      advertencias: ["cita a una fuente sin acceso abierto comprobado: F2"],
      respuesta: [
        {
          afirmacion: "La tutoría entre pares reduce la ansiedad ante la estadística.",
          citas: [cita("F1", true), cita("F2", false)],
        },
      ],
    });
    const enCurso = vista({ estado: "recuperando", respuesta: [], fuentes: [] });
    vi.stubGlobal("fetch", apiFicticia(aceptada(), [enCurso, conCerrada], llamadas));
    const usuario = await buscar("Quiero sustentar que la tutoría entre pares reduce la ansiedad");
    expect(await screen.findByText(/Buscando evidencia/)).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Evidencia encontrada" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Con advertencias/)).toBeInTheDocument();
    expect(screen.getByText("cita a una fuente sin acceso abierto comprobado: F2")).toBeVisible();

    const lista = screen.getByRole("list", { name: "Respuesta con sus citas" });
    const abierta = within(lista).getByText(/Cita F1: Tutoría entre pares/);
    await usuario.click(abierta);
    const detalle = abierta.closest("details");
    expect(detalle).not.toBeNull();
    expect(detalle).toHaveAttribute("open");
    expect(within(detalle as HTMLElement).getByText(/Resultados, páginas 4 a 5/)).toBeVisible();
    const enlace = within(detalle as HTMLElement).getByRole("link", {
      name: /Ver la fuente en acceso abierto/,
    });
    expect(enlace).toHaveAttribute("href", "https://repositorio.example/a1");
    expect(enlace).toHaveAttribute("rel", "noopener noreferrer");
    const cerrada = within(lista)
      .getByText(/Cita F2: Artículo ficticio cerrado/)
      .closest("details");
    expect(within(cerrada as HTMLElement).getByText(/Sin acceso abierto comprobado/)).toBeTruthy();

    expect(screen.getByText(/Quispe, A. \(2021\). Tutoría entre pares/)).toBeVisible();
    expect(screen.getByText("La evidencia proviene de un solo contexto.")).toBeVisible();
    const envio = llamadas.find((p) => p.method === "POST");
    expect(await envio?.json()).toEqual({
      consulta: "Quiero sustentar que la tutoría entre pares reduce la ansiedad",
    });
  }, 10000);

  it("con evidencia insuficiente avisa e invita a aportar una fuente", async () => {
    const abstencion = vista({
      abstencion: true,
      aviso: "Sin evidencia suficiente",
      invitacion_aporte: "Puede aportar una fuente de acceso abierto sobre su consulta.",
      etiqueta: "sin_evidencia_suficiente",
      respuesta: [],
      fuentes: [],
      notas_para_el_estudiante: [],
    });
    vi.stubGlobal("fetch", apiFicticia(aceptada(), abstencion));
    await buscar("Quiero sustentar que la política monetaria reduce la inflación");
    expect(
      await screen.findByRole("heading", { name: "Sin evidencia suficiente" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Puede aportar una fuente de acceso abierto/)).toBeVisible();
  }, 10000);

  it("informa cuando la búsqueda no pudo atenderse", async () => {
    vi.stubGlobal(
      "fetch",
      apiFicticia(aceptada(), vista({ estado: "no_atendida", motivo: "modelo:sobrecarga" })),
    );
    await buscar("Quiero sustentar que la tutoría entre pares reduce la ansiedad");
    expect(await screen.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
      "La búsqueda no pudo atenderse.",
    );
  }, 10000);

  it("abre un resultado guardado desde la dirección, sin volver a pedirlo", async () => {
    const llamadas: Request[] = [];
    vi.stubGlobal("fetch", apiFicticia(aceptada(), vista({}), llamadas));
    render(
      <MemoryRouter initialEntries={[`/panel/evidencia?solicitud=${SOLICITUD}`]}>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: "Evidencia encontrada" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Consulta o afirmación" })).toHaveValue(
      "Quiero sustentar que la tutoría entre pares reduce la ansiedad",
    );
    expect(llamadas.some((p) => p.method === "POST")).toBe(false);
  }, 10000);
});

import { describe, expect, it } from "vitest";

import {
  CABECERA_CSRF,
  ErrorApi,
  MENSAJE_SIN_CONEXION,
  errorDe,
  exigir,
  leerCookie,
  middlewareCsrf,
} from "../api/cliente";

describe("cookies y CSRF", () => {
  it("lee una cookie por su nombre", () => {
    expect(leerCookie("sma_csrf", "otra=1; sma_csrf=abc%3D; x=2")).toBe("abc=");
    expect(leerCookie("sma_csrf", "otra=1")).toBeNull();
  });

  it("agrega el token solo a las peticiones que cambian datos", async () => {
    document.cookie = "sma_csrf=token-de-prueba";
    const aplicar = middlewareCsrf.onRequest;
    if (aplicar === undefined) throw new Error("falta onRequest");
    const contexto = (metodo: string) =>
      ({ request: new Request("http://prueba/api/caso", { method: metodo }) }) as Parameters<
        typeof aplicar
      >[0];
    const post = (await aplicar(contexto("POST"))) as Request;
    const get = (await aplicar(contexto("GET"))) as Request;
    expect(post.headers.get(CABECERA_CSRF)).toBe("token-de-prueba");
    expect(get.headers.get(CABECERA_CSRF)).toBeNull();
  });
});

describe("errores en el formato común", () => {
  it("toma código, mensaje, detalle e incidencia del cuerpo", () => {
    const error = errorDe(new Response(null, { status: 422 }), {
      codigo: "docx_con_macros",
      mensaje: "El archivo contiene macros.",
      detalle: { motivo: "docx_con_macros" },
      incidencia_id: "abc123",
    });
    expect(error).toBeInstanceOf(ErrorApi);
    expect([error.estado, error.codigo, error.message, error.incidenciaId]).toEqual([
      422,
      "docx_con_macros",
      "El archivo contiene macros.",
      "abc123",
    ]);
  });

  it("un cuerpo desconocido da un mensaje genérico, sin exponer el cuerpo", () => {
    const error = errorDe(new Response(null, { status: 502 }), "<html>proxy</html>");
    expect(error.codigo).toBe("error_inesperado");
    expect(error.message).not.toContain("proxy");
  });

  it("un fallo de red es un ErrorApi sin conexión", async () => {
    const fallida = Promise.reject(new TypeError("Failed to fetch"));
    await expect(exigir(fallida)).rejects.toMatchObject({
      codigo: "sin_conexion",
      message: MENSAJE_SIN_CONEXION,
    });
  });

  it("devuelve los datos de una respuesta correcta", async () => {
    const respuesta = Promise.resolve({ data: { ok: true }, response: new Response("{}") });
    await expect(exigir(respuesta)).resolves.toEqual({ ok: true });
  });
});

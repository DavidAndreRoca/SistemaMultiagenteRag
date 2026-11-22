// Cliente de la API generado desde el contrato OpenAPI (docs/api/openapi.json): los tipos
// de src/api/esquema.d.ts salen de `npm run generar:api` y nunca se escriben a mano.
import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./esquema";

export type Esquemas = components["schemas"];

export const RUTA_BASE = "/api";
export const COOKIE_CSRF = "sma_csrf";
export const CABECERA_CSRF = "X-CSRF-Token";
const METODOS_SEGUROS = new Set(["GET", "HEAD", "OPTIONS"]);

/** Error en el formato común de la API (hoja de ruta, 4.4), o uno de red equivalente. */
export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    readonly codigo: string,
    mensaje: string,
    readonly detalle: unknown = null,
    readonly incidenciaId: string | null = null,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }
}

/** Error de una validación de la propia interfaz: ``AvisoError`` muestra su mensaje tal cual. */
export function errorDeValidacion(mensaje: string): ErrorApi {
  return new ErrorApi(0, "validacion_interfaz", mensaje);
}

export const MENSAJE_SIN_CONEXION =
  "No se pudo conectar con el servidor. Revise su conexión e intente de nuevo.";

export function leerCookie(nombre: string, cookies: string = document.cookie): string | null {
  for (const parte of cookies.split(";")) {
    const [clave, ...valor] = parte.trim().split("=");
    if (clave === nombre) return decodeURIComponent(valor.join("="));
  }
  return null;
}

/** Agrega el token CSRF (cookie no HttpOnly) a toda petición que cambia datos. */
export const middlewareCsrf: Middleware = {
  onRequest({ request }) {
    if (!METODOS_SEGUROS.has(request.method)) {
      const token = leerCookie(COOKIE_CSRF);
      if (token) request.headers.set(CABECERA_CSRF, token);
    }
    return request;
  },
};

// Siempre el mismo origen de la página (la API está detrás del mismo dominio, T13). La URL
// absoluta también la entiende el fetch de Node que usan las pruebas unitarias.
export const api = createClient<paths>({
  baseUrl: `${globalThis.location.origin}${RUTA_BASE}`,
  credentials: "same-origin",
  fetch: (peticion) => globalThis.fetch(peticion), // en cada petición, no al importar
});
api.use(middlewareCsrf);

function esErrorComun(cuerpo: unknown): cuerpo is Esquemas["RespuestaError"] {
  return (
    typeof cuerpo === "object" &&
    cuerpo !== null &&
    typeof (cuerpo as { codigo?: unknown }).codigo === "string" &&
    typeof (cuerpo as { mensaje?: unknown }).mensaje === "string"
  );
}

/** Convierte cualquier respuesta de error en un ``ErrorApi`` con mensaje para el usuario. */
export function errorDe(respuesta: Response | undefined, cuerpo: unknown): ErrorApi {
  const estado = respuesta?.status ?? 0;
  if (esErrorComun(cuerpo)) {
    return new ErrorApi(
      estado,
      cuerpo.codigo,
      cuerpo.mensaje,
      cuerpo.detalle ?? null,
      cuerpo.incidencia_id ?? null,
    );
  }
  return new ErrorApi(
    estado,
    "error_inesperado",
    "Ocurrió un error inesperado. Intente de nuevo más tarde.",
  );
}

type Resultado<T> = { data?: T; error?: unknown; response: Response };

/** Devuelve los datos o lanza ``ErrorApi``; un fallo de red también es un ``ErrorApi``. */
export async function exigir<T>(peticion: Promise<Resultado<T>>): Promise<T> {
  let resultado: Resultado<T>;
  try {
    resultado = await peticion;
  } catch {
    throw new ErrorApi(0, "sin_conexion", MENSAJE_SIN_CONEXION);
  }
  if (!resultado.response.ok || resultado.data === undefined) {
    if (resultado.response.ok && resultado.response.status === 204) return undefined as T;
    throw errorDe(resultado.response, resultado.error);
  }
  return resultado.data;
}

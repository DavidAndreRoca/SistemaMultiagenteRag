// Estados de una solicitud mientras el sistema la atiende (T28): la pantalla sigue
// consultando hasta que llega a "entregada" o "no_atendida". "recibida" incluye la espera en
// la cola y la vuelta a la cola tras una caída del proveedor.
export const EN_CURSO: ReadonlySet<string> = new Set([
  "recibida",
  "asignada",
  "recuperando",
  "generando",
  "verificando",
  "reintentando",
]);

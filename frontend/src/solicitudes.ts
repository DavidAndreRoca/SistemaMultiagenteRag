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

// Pantalla de resultado y nombre de cada tipo de pedido (panel e historial, T33).
export const PANTALLAS: Record<string, string> = {
  busqueda_evidencia: "/panel/evidencia",
  verificacion_referencias: "/panel/referencias",
  revision_estructura: "/panel/estructura",
  propuesta_redaccion: "/panel/redaccion",
  revision_metodologica: "/panel/metodologia",
  plan_tarea: "/panel/plan",
};
export const NOMBRES_PEDIDO: Record<string, string> = {
  busqueda_evidencia: "Búsqueda de evidencia",
  verificacion_referencias: "Verificación de referencias",
  revision_estructura: "Revisión de estructura y coherencia",
  propuesta_redaccion: "Propuesta de redacción",
  revision_metodologica: "Revisión metodológica",
  plan_tarea: "Plan de tarea",
};
// Etiqueta del resultado entregado (T30) y la clase de su insignia.
export const ETIQUETAS: Record<string, { texto: string; clase: string }> = {
  verificada: { texto: "Verificada", clase: "insignia--entregada" },
  con_advertencias: { texto: "Con advertencias", clase: "insignia--pendiente" },
  sin_evidencia_suficiente: { texto: "Sin evidencia suficiente", clase: "insignia--neutra" },
};

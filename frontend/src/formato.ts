// Formatos para mostrar datos al usuario, en español del Perú (Ica).
const ZONA = "America/Lima";

export function fechaHora(iso: string): string {
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: ZONA,
  }).format(new Date(iso));
}

export function tamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toLocaleString("es-PE", { maximumFractionDigits: 1 })} MB`;
}

export function numero(valor: number): string {
  return valor.toLocaleString("es-PE");
}

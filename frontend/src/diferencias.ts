// Comparación palabra por palabra entre el párrafo original y la propuesta de redacción (T27,
// vista comparada de RF-07). Usa la subsecuencia común más larga: lo que queda fuera de ella
// se marca como quitado en el original o agregado en la propuesta. Un párrafo tiene hasta unas
// 250 palabras, así que la tabla cabe de sobra en memoria.

export type TipoTramo = "igual" | "quitado" | "agregado";

export interface Tramo {
  tipo: TipoTramo;
  texto: string;
}

export interface Comparacion {
  original: Tramo[];
  propuesta: Tramo[];
}

function palabras(texto: string): string[] {
  return texto.split(/\s+/).filter((palabra) => palabra.length > 0);
}

function agregar(tramos: Tramo[], tipo: TipoTramo, palabra: string): void {
  const ultimo = tramos.at(-1);
  if (ultimo?.tipo === tipo) ultimo.texto += ` ${palabra}`;
  else tramos.push({ tipo, texto: palabra });
}

export function compararPalabras(original: string, propuesta: string): Comparacion {
  const a = palabras(original);
  const b = palabras(propuesta);
  // comun[i][j]: largo de la subsecuencia común de a[i..] y b[j..].
  const comun = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    const fila = comun[i] ?? [];
    const siguiente = comun[i + 1] ?? [];
    for (let j = b.length - 1; j >= 0; j--) {
      fila[j] =
        a[i] === b[j] ? (siguiente[j + 1] ?? 0) + 1 : Math.max(siguiente[j] ?? 0, fila[j + 1] ?? 0);
    }
  }
  const resultado: Comparacion = { original: [], propuesta: [] };
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    const pa = a[i];
    const pb = b[j];
    if (pa !== undefined && pb !== undefined && pa === pb) {
      agregar(resultado.original, "igual", pa);
      agregar(resultado.propuesta, "igual", pb);
      i++;
      j++;
    } else if (
      pa !== undefined &&
      (pb === undefined || (comun[i + 1]?.[j] ?? 0) >= (comun[i]?.[j + 1] ?? 0))
    ) {
      agregar(resultado.original, "quitado", pa);
      i++;
    } else if (pb !== undefined) {
      agregar(resultado.propuesta, "agregado", pb);
      j++;
    }
  }
  return resultado;
}

// Aporte de una fuente tras "Sin evidencia suficiente" (T32; RF-13, CU-12). El caso escribe
// los datos de la obra (título, autores y año; DOI opcional) y, si lo tiene, adjunta el PDF.
// El sistema comprueba que la obra existe, evalúa si trata lo que quiere sustentar, propone
// la cita en la norma del caso y, si se confirmó, la guarda solo en su colección personal y
// vuelve a buscar evidencia con la misma consulta.
import { useEffect, useState } from "react";
import { Form } from "react-aria-components";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import {
  AvisoError,
  AvisoInformativo,
  Boton,
  CampoTexto,
  CampoTextoLargo,
  SelectorArchivo,
} from "./controles";

type VistaAporte = Esquemas["VistaAporte"];
type CuerpoAporte = Esquemas["Body_aportar_caso_solicitudes__solicitud_id__aporte_post"];

const TIPO_PDF = ".pdf";

const COHERENCIA: Record<string, string> = {
  coherente: "La fuente trata lo que quiere sustentar.",
  parcial: "La fuente trata solo una parte de lo que quiere sustentar, o un asunto cercano.",
  no_coherente: "La fuente parece tratar otro asunto. Revísela antes de usarla.",
  no_evaluada: "No se pudo evaluar si la fuente trata lo que quiere sustentar.",
};

function existencia(aporte: VistaAporte): string {
  if (aporte.existencia === "confirmada") {
    return aporte.metodo_existencia === "doi"
      ? "La obra existe: su DOI se confirmó en las bases bibliográficas."
      : "La obra existe: el título, un autor y el año coinciden con un registro bibliográfico.";
  }
  if (aporte.existencia === "no_comprobable") {
    return (
      "No se pudo comprobar la obra porque las bases bibliográficas no respondieron. No se" +
      " guardó; inténtelo más tarde. Esto no significa que la obra no exista."
    );
  }
  return (
    "No se confirmó que la obra exista: el DOI no se resolvió o los datos no se localizaron" +
    " en las bases bibliográficas. No se guardó en su colección."
  );
}

function indexacion(aporte: VistaAporte): string | null {
  if (aporte.indexacion === "indexada") {
    return aporte.texto_indexado === "pdf"
      ? "Se guardó el PDF en su colección personal. Solo usted la usa."
      : "Se guardó el resumen de la obra en su colección personal. Solo usted la usa.";
  }
  if (aporte.indexacion === "ya_indexada") {
    return "La obra ya estaba en su colección personal: no se duplicó.";
  }
  if (aporte.existencia === "confirmada" && aporte.motivo_indexacion === "sin_texto") {
    return (
      "La obra existe, pero las bases bibliográficas no tienen su resumen. Adjunte el PDF" +
      " para guardarla en su colección."
    );
  }
  return null;
}

export function AporteDeFuente({
  solicitud,
  abierto,
  alAportado,
  alNuevaBusqueda,
}: {
  solicitud: string;
  abierto: boolean;
  alAportado?: () => void;
  alNuevaBusqueda: (nueva: string) => void;
}) {
  const [titulo, setTitulo] = useState("");
  const [autores, setAutores] = useState("");
  const [anio, setAnio] = useState("");
  const [doi, setDoi] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const [ultimo, setUltimo] = useState<VistaAporte | null>(null);
  const [previos, setPrevios] = useState<VistaAporte[]>([]);

  useEffect(() => {
    let vigente = true;
    exigir(
      api.GET("/caso/solicitudes/{solicitud_id}/aportes", {
        params: { path: { solicitud_id: solicitud } },
      }),
    )
      .then((lista) => {
        if (vigente) setPrevios(lista);
      })
      .catch(() => {
        if (vigente) setPrevios([]);
      });
    return () => {
      vigente = false;
    };
  }, [solicitud, ultimo]);

  async function enviar() {
    setError(null);
    setUltimo(null);
    const numero = Number(anio);
    if (titulo.trim() === "" || autores.trim() === "" || !Number.isInteger(numero)) {
      setError(errorDeValidacion("Escriba el título, al menos un autor y el año de la obra."));
      return;
    }
    const datos = new FormData();
    datos.append("titulo", titulo.trim());
    datos.append("autores", autores.trim());
    datos.append("anio", String(numero));
    if (doi.trim() !== "") datos.append("doi", doi.trim());
    if (archivo !== null) datos.append("archivo", archivo);
    setEnviando(true);
    try {
      const aporte = await exigir(
        api.POST("/caso/solicitudes/{solicitud_id}/aporte", {
          params: { path: { solicitud_id: solicitud } },
          // Formulario con archivo: el contrato lo describe como campos de texto.
          body: datos as unknown as CuerpoAporte,
          bodySerializer: (cuerpo) => cuerpo as unknown as FormData,
        }),
      );
      setUltimo(aporte);
      alAportado?.();
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  const anteriores = previos.filter((p) => p.id !== ultimo?.id);
  return (
    <section aria-labelledby={`titulo-aporte-${solicitud}`} className="aporte">
      <h2 id={`titulo-aporte-${solicitud}`}>Aportar una fuente</h2>
      {abierto ? (
        <>
          <p>
            Escriba los datos de una obra que trate su consulta. El sistema comprobará que existe,
            propondrá su cita y, si se confirma, la guardará solo en su colección personal y volverá
            a buscar evidencia. El PDF es opcional: sin él se usa el resumen de la obra.
          </p>
          <Form
            className="formulario"
            onSubmit={(evento) => {
              evento.preventDefault();
              void enviar();
            }}
          >
            <CampoTexto etiqueta="Título" value={titulo} onChange={setTitulo} isRequired />
            <CampoTextoLargo
              etiqueta="Autores"
              descripcion="Apellidos de los autores, uno por línea."
              value={autores}
              onChange={setAutores}
              isRequired
            />
            <CampoTexto
              etiqueta="Año"
              inputMode="numeric"
              value={anio}
              onChange={setAnio}
              isRequired
            />
            <CampoTexto
              etiqueta="DOI (opcional)"
              descripcion="Por ejemplo, 10.1234/abcd.5678"
              value={doi}
              onChange={setDoi}
            />
            <SelectorArchivo
              etiqueta="Adjuntar el PDF (opcional)"
              tipos={[TIPO_PDF]}
              archivo={archivo}
              alElegir={setArchivo}
            />
            <AvisoError error={error} />
            <Boton type="submit" isDisabled={enviando}>
              {enviando ? "Comprobando la fuente…" : "Aportar la fuente"}
            </Boton>
          </Form>
        </>
      ) : null}
      {ultimo ? <Desenlace aporte={ultimo} alNuevaBusqueda={alNuevaBusqueda} /> : null}
      {anteriores.length > 0 ? (
        <details className="aporte__previos">
          <summary>Fuentes que ya aportó para esta consulta ({anteriores.length})</summary>
          <ul>
            {anteriores.map((p) => (
              <li key={p.id}>
                {p.titulo} ({p.anio ?? "s. f."}): {indexacion(p) ?? existencia(p)}
                {p.nueva_solicitud_id ? (
                  <>
                    {" "}
                    <Boton
                      variante="claro"
                      onPress={() => {
                        alNuevaBusqueda(p.nueva_solicitud_id ?? "");
                      }}
                    >
                      Ver la nueva búsqueda
                    </Boton>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function Desenlace({
  aporte,
  alNuevaBusqueda,
}: {
  aporte: VistaAporte;
  alNuevaBusqueda: (nueva: string) => void;
}) {
  const guardada = indexacion(aporte);
  return (
    <AvisoInformativo>
      <p>{existencia(aporte)}</p>
      {aporte.existencia === "confirmada" ? (
        <>
          <p>
            {COHERENCIA[aporte.coherencia]}
            {aporte.explicacion_coherencia ? ` ${aporte.explicacion_coherencia}` : ""}
          </p>
          {aporte.cita_propuesta ? (
            <p>
              Cita propuesta en la norma de su caso: <span>{aporte.cita_propuesta}</span>
            </p>
          ) : null}
        </>
      ) : null}
      {guardada ? <p>{guardada}</p> : null}
      {aporte.nueva_solicitud_id ? (
        <Boton
          onPress={() => {
            alNuevaBusqueda(aporte.nueva_solicitud_id ?? "");
          }}
        >
          Ver la nueva búsqueda con su fuente
        </Boton>
      ) : null}
    </AvisoInformativo>
  );
}

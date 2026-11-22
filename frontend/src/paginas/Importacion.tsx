// Importación de las referencias del artículo O1 (T15; RF-20, CU-14). El investigador elige
// el tema, sube el artículo (PDF o .docx) o pega los DOI y sigue el avance. Después ve el
// informe del tema y sube a mano los PDF que quedaron pendientes. El artículo no se guarda.
import { useCallback, useEffect, useState } from "react";
import { Form, Link } from "react-aria-components";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import {
  AvisoError,
  AvisoInformativo,
  Boton,
  CampoTextoLargo,
  Selector,
  SelectorArchivo,
} from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { numero } from "../formato";

type Coleccion = Esquemas["ColeccionVista"];
type Importacion = Esquemas["ImportacionVista"];
type Informe = Esquemas["InformeTema"];
type Referencia = Esquemas["ReferenciaVista"];
type CuerpoImportacion =
  Esquemas["Body_iniciar_importacion_investigador_colecciones__coleccion_id__importaciones_post"];
type CuerpoPdf =
  Esquemas["Body_subir_pdf_referencia_investigador_referencias__referencia_id__pdf_post"];

const TIPOS_ARTICULO = [
  ".pdf",
  ".docx",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ESPERA_AVANCE_MS = 2000;

export const MOTIVOS: Record<string, string> = {
  sin_acceso_abierto: "Sin acceso abierto",
  no_localizada: "No localizada en Crossref ni OpenAlex",
  sin_doi: "Sin DOI",
  doi_invalido: "No tiene forma de DOI",
  sin_capa_de_texto: "PDF escaneado, sin capa de texto",
  pdf_ilegible: "PDF ilegible",
  pdf_cifrado: "PDF cifrado",
  no_es_pdf: "El archivo no es un PDF",
  excede_tamano: "El PDF supera el tamaño máximo",
  excede_paginas: "El PDF supera el número máximo de páginas",
  duplicado: "Duplicado de otro documento",
  descarga_fallida: "La descarga automática falló",
  sin_enlace_directo: "Sin enlace directo al PDF",
};

const ERRORES: Record<string, string> = {
  articulo_no_valido: "El artículo no se pudo leer. Revise que sea un PDF o un .docx válido.",
  sin_referencias:
    "No se encontró la lista de referencias del artículo. Revise que tenga una sección de referencias o pegue la lista de DOI.",
  error_interno: "Ocurrió un error inesperado durante la importación. Intente de nuevo.",
};

export function motivo(codigo: string | null): string {
  if (codigo === null) return "";
  if (codigo.startsWith("crossref_") || codigo.startsWith("openalex_")) {
    return "Crossref u OpenAlex no respondieron";
  }
  if (codigo.startsWith("unpaywall_")) return "Unpaywall no respondió";
  return MOTIVOS[codigo] ?? codigo;
}

function enCurso(importacion: Importacion): boolean {
  return importacion.estado === "en_cola" || importacion.estado === "en_proceso";
}

export function ImportacionReferencias() {
  const [colecciones, setColecciones] = useState<Coleccion[] | null>(null);
  const [coleccion, setColeccion] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ronda, setRonda] = useState(0);

  useEffect(() => {
    let vigente = true;
    exigir(api.GET("/investigador/colecciones"))
      .then((lista) => {
        if (vigente) setColecciones(lista);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, []);

  const actualizar = useCallback(() => {
    setRonda((n) => n + 1);
  }, []);

  const temas = (colecciones ?? []).filter((c) => c.tipo === "cientifica" && c.tema !== null);

  return (
    <Marco titulo="Importar referencias del artículo O1">
      <p>
        <a href="/investigador">Volver a casos y colecciones</a>
      </p>
      <AvisoError error={error} />
      {colecciones === null ? (
        error ? null : (
          <p role="status">Cargando temas…</p>
        )
      ) : temas.length === 0 ? (
        <p>Primero cree un tema en la página de casos y colecciones.</p>
      ) : (
        <>
          <Selector
            etiqueta="Tema"
            opciones={temas.map((t) => ({ id: t.id, etiqueta: t.tema ?? "" }))}
            valor={coleccion}
            alCambiar={setColeccion}
            requerido
            marcador="Elija el tema"
          />
          {coleccion ? (
            <>
              <NuevaImportacion key={coleccion} coleccion={coleccion} alTerminar={actualizar} />
              <InformeDelTema coleccion={coleccion} ronda={ronda} />
              <Pendientes coleccion={coleccion} ronda={ronda} alSubir={actualizar} />
            </>
          ) : null}
        </>
      )}
    </Marco>
  );
}

function NuevaImportacion({
  coleccion,
  alTerminar,
}: {
  coleccion: string;
  alTerminar: () => void;
}) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [dois, setDois] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [importacion, setImportacion] = useState<Importacion | null>(null);

  const id = importacion?.id ?? null;
  const siguiendo = importacion !== null && enCurso(importacion);

  useEffect(() => {
    if (id === null || !siguiendo) return;
    let vigente = true;
    const espera = setTimeout(() => {
      exigir(
        api.GET("/investigador/importaciones/{importacion_id}", {
          params: { path: { importacion_id: id } },
        }),
      )
        .then((actual) => {
          if (!vigente) return;
          setImportacion(actual);
          if (!enCurso(actual)) alTerminar();
        })
        .catch((fallo: unknown) => {
          if (vigente) setError(fallo);
        });
    }, ESPERA_AVANCE_MS);
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
  }, [id, siguiendo, importacion, alTerminar]);

  async function enviar() {
    setError(null);
    const hayDois = dois.trim() !== "";
    if ((archivo === null) === !hayDois) {
      setError(errorDeValidacion("Suba el artículo o pegue la lista de DOI, pero no ambos."));
      return;
    }
    const datos = new FormData();
    if (archivo) datos.append("archivo", archivo);
    else datos.append("dois", dois);
    try {
      const nueva = await exigir(
        api.POST("/investigador/colecciones/{coleccion_id}/importaciones", {
          params: { path: { coleccion_id: coleccion } },
          // Formulario con archivo: el contrato lo describe como campos de texto.
          body: datos as unknown as CuerpoImportacion,
          bodySerializer: (cuerpo) => cuerpo as unknown as FormData,
        }),
      );
      setImportacion(nueva);
      setArchivo(null);
      setDois("");
    } catch (fallo) {
      setError(fallo);
    }
  }

  return (
    <section aria-labelledby="titulo-importar">
      <h2 id="titulo-importar">Nueva importación</h2>
      <Form
        className="formulario"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
      >
        <p className="campo__descripcion">
          Del artículo solo se usan sus referencias: se borra apenas se extraen y no se guarda ni se
          indexa.
        </p>
        <SelectorArchivo
          etiqueta="Elegir el artículo (PDF o .docx)"
          tipos={TIPOS_ARTICULO}
          archivo={archivo}
          alElegir={setArchivo}
        />
        <CampoTextoLargo
          etiqueta="O pegue la lista de DOI"
          descripcion="Uno por línea. Las líneas que no tengan forma de DOI se excluyen."
          name="dois"
          value={dois}
          onChange={setDois}
          maxLength={100000}
        />
        <AvisoError error={error} />
        <Boton type="submit" isDisabled={siguiendo}>
          Importar las referencias
        </Boton>
      </Form>
      {importacion ? <Avance importacion={importacion} /> : null}
    </section>
  );
}

function Avance({ importacion }: { importacion: Importacion }) {
  if (enCurso(importacion)) {
    return (
      <div role="status" aria-live="polite" className="avance">
        <p>
          {importacion.estado === "en_cola"
            ? "La importación está en cola."
            : `Procesando: ${numero(importacion.procesadas)} de ${numero(importacion.total)} referencias.`}
        </p>
        <progress
          max={Math.max(importacion.total, 1)}
          value={importacion.procesadas}
          aria-label="Avance de la importación"
        />
      </div>
    );
  }
  if (importacion.estado === "terminada") {
    return (
      <AvisoInformativo>
        <p>
          Importación terminada: {numero(importacion.total)} referencias procesadas. El informe del
          tema está actualizado.
        </p>
      </AvisoInformativo>
    );
  }
  const mensaje =
    importacion.estado === "interrumpida"
      ? "La importación se interrumpió por un reinicio del servidor. Vuelva a importar: lo ya procesado no se repite."
      : (ERRORES[importacion.error ?? ""] ?? ERRORES.error_interno);
  return (
    <div className="aviso aviso--error" role="alert">
      <p>{mensaje}</p>
    </div>
  );
}

function InformeDelTema({ coleccion, ronda }: { coleccion: string; ronda: number }) {
  const [informe, setInforme] = useState<Informe | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;
    exigir(
      api.GET("/investigador/colecciones/{coleccion_id}/informe", {
        params: { path: { coleccion_id: coleccion } },
      }),
    )
      .then((datos) => {
        if (vigente) setInforme(datos);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, [coleccion, ronda]);

  const motivos = Object.entries(informe?.excluidas_por_motivo ?? {});
  return (
    <section aria-labelledby="titulo-informe">
      <h2 id="titulo-informe">Informe del tema</h2>
      <AvisoError error={error} />
      {informe === null ? null : informe.referencias === 0 ? (
        <p>Este tema todavía no tiene referencias importadas.</p>
      ) : (
        <>
          <table className="tabla">
            <caption className="oculto">Referencias del tema por estado</caption>
            <tbody>
              <Fila nombre="Referencias" valor={informe.referencias} />
              <Fila nombre="De acceso abierto" valor={informe.de_acceso_abierto} />
              <Fila nombre="Incluidas en la colección" valor={informe.incluidas} />
              <Fila nombre="Pendientes de PDF" valor={informe.pendientes_pdf} />
              <Fila
                nombre="No comprobables (un servicio no respondió; se reintentan)"
                valor={informe.no_comprobables}
              />
              <Fila nombre="Excluidas" valor={informe.excluidas} />
            </tbody>
          </table>
          {motivos.length > 0 ? (
            <table className="tabla">
              <caption>Excluidas por motivo</caption>
              <thead>
                <tr>
                  <th scope="col">Motivo</th>
                  <th scope="col">Referencias</th>
                </tr>
              </thead>
              <tbody>
                {motivos.map(([codigo, cantidad]) => (
                  <Fila key={codigo} nombre={motivo(codigo)} valor={cantidad} />
                ))}
              </tbody>
            </table>
          ) : null}
        </>
      )}
    </section>
  );
}

function Fila({ nombre, valor }: { nombre: string; valor: number }) {
  return (
    <tr>
      <th scope="row">{nombre}</th>
      <td>{numero(valor)}</td>
    </tr>
  );
}

function Pendientes({
  coleccion,
  ronda,
  alSubir,
}: {
  coleccion: string;
  ronda: number;
  alSubir: () => void;
}) {
  const [pendientes, setPendientes] = useState<Referencia[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ultima, setUltima] = useState<Referencia | null>(null);

  const alTerminar = useCallback(
    (actual: Referencia) => {
      setUltima(actual);
      alSubir();
    },
    [alSubir],
  );

  useEffect(() => {
    let vigente = true;
    exigir(
      api.GET("/investigador/colecciones/{coleccion_id}/referencias", {
        params: { path: { coleccion_id: coleccion }, query: { estado: "pendiente_pdf" } },
      }),
    )
      .then((lista) => {
        if (vigente) setPendientes(lista);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, [coleccion, ronda]);

  return (
    <section aria-labelledby="titulo-pendientes">
      <h2 id="titulo-pendientes">Pendientes de PDF</h2>
      <AvisoError error={error} />
      {ultima ? (
        <AvisoInformativo>
          <p>
            {ultima.estado === "incluida"
              ? "PDF indexado: la referencia quedó incluida."
              : `La referencia quedó excluida: ${motivo(ultima.motivo)}.`}
          </p>
        </AvisoInformativo>
      ) : null}
      {pendientes === null ? null : pendientes.length === 0 ? (
        <p>No hay referencias pendientes de PDF.</p>
      ) : (
        <>
          <p>
            Son de acceso abierto, pero el PDF no se pudo bajar solo. Ábralo desde su página de
            acceso abierto, guárdelo y súbalo aquí.
          </p>
          <ul className="pendientes">
            {pendientes.map((referencia) => (
              <Pendiente key={referencia.id} referencia={referencia} alSubir={alTerminar} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Pendiente({
  referencia,
  alSubir,
}: {
  referencia: Referencia;
  alSubir: (actual: Referencia) => void;
}) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const pagina = referencia.url_acceso_abierto ?? referencia.url_pdf;

  async function subir() {
    setError(null);
    if (archivo === null) {
      setError(errorDeValidacion("Elija el PDF de la referencia."));
      return;
    }
    const datos = new FormData();
    datos.append("archivo", archivo);
    setEnviando(true);
    try {
      const actual = await exigir(
        api.POST("/investigador/referencias/{referencia_id}/pdf", {
          params: { path: { referencia_id: referencia.id } },
          body: datos as unknown as CuerpoPdf,
          bodySerializer: (cuerpo) => cuerpo as unknown as FormData,
        }),
      );
      setArchivo(null);
      alSubir(actual);
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <li className="pendiente">
      <p className="pendiente__texto">{referencia.texto}</p>
      <p className="campo__descripcion">
        {motivo(referencia.motivo)}
        {referencia.licencia ? `. Licencia: ${referencia.licencia}` : ""}
      </p>
      {pagina ? (
        <p>
          <Link href={pagina} target="_blank" rel="noopener noreferrer">
            Abrir la página de acceso abierto<span className="oculto"> (otra pestaña)</span>
          </Link>
        </p>
      ) : null}
      <SelectorArchivo
        etiqueta="Elegir el PDF"
        tipos={[".pdf", "application/pdf"]}
        archivo={archivo}
        alElegir={setArchivo}
      />
      <AvisoError error={error} />
      <Boton
        variante="secundario"
        isDisabled={enviando}
        onPress={() => {
          void subir();
        }}
      >
        Subir el PDF
      </Boton>
    </li>
  );
}

// Búsqueda de evidencia del caso (T19; RF-08, CU-07, RF-21 en parte). El estudiante escribe
// una consulta o una afirmación; el sistema la valida, busca en las fuentes de su tema y de
// su colección personal y responde con afirmaciones citadas. Cada cita se despliega con el
// fragmento, el documento, la sección, las páginas y el enlace de acceso abierto.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { Form } from "react-aria-components";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, Boton, CampoTextoLargo } from "../componentes/controles";
import { AporteDeFuente } from "../componentes/Aporte";
import { DecisionSobreResultado } from "../componentes/Decision";
import { Marco } from "../componentes/Marco";
import { fechaHora } from "../formato";
import { AvanceSolicitud, NoAtendida, Verificada } from "../componentes/Seguimiento";
import { EN_CURSO } from "../solicitudes";

type Vista = Esquemas["VistaEvidencia"];
type Afirmacion = Esquemas["AfirmacionVista"];
type Cita = Esquemas["CitaVista"];

const ESPERA_AVANCE_MS = 2000;
const SECCIONES: Record<string, string> = {
  resumen: "Resumen",
  introduccion: "Introducción",
  metodos: "Métodos",
  resultados: "Resultados",
  discusion: "Discusión",
  conclusiones: "Conclusiones",
  otra: "Otra sección",
};
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "La búsqueda se interrumpió por un reinicio del servidor. Vuelva a pedirla.",
};

function documento(cita: Cita): string {
  const partes = [cita.autores, cita.anio === null ? null : `(${String(cita.anio)})`].filter(
    (parte): parte is string => Boolean(parte),
  );
  return partes.length > 0 ? `${partes.join(" ")}. ` : "";
}

/** Fuente de la colección personal: los datos que aportó el caso (RF-21). */
function DatosAportados({ aporte }: { aporte: NonNullable<Cita["aporte"]> }) {
  return (
    <p className="campo__descripcion">
      Fuente que usted aportó el {fechaHora(aporte.aportada_en)}: «{aporte.titulo}»,{" "}
      {aporte.autores.join(", ")}
      {aporte.anio === null ? "" : `, ${String(aporte.anio)}`}
      {aporte.doi ? `, DOI ${aporte.doi}` : ""}.
    </p>
  );
}

function paginas(cita: Cita): string {
  if (cita.pagina_inicio === null) return "";
  if (cita.pagina_fin === null || cita.pagina_fin === cita.pagina_inicio) {
    return `, página ${cita.pagina_inicio}`;
  }
  return `, páginas ${cita.pagina_inicio} a ${cita.pagina_fin}`;
}

export function Evidencia() {
  const [consulta, setConsulta] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  // La solicitud va en la dirección (?solicitud=...): el resultado sobrevive a una
  // recarga y se puede abrir desde la lista del panel.
  const [parametros, setParametros] = useSearchParams();
  const [solicitud, setSolicitud] = useState<string | null>(parametros.get("solicitud"));
  const [enviando, setEnviando] = useState(false);
  // Aporte de una fuente tras una abstención (T32): el formulario se abre desde la decisión.
  const [aportando, setAportando] = useState(false);
  const [aportes, setAportes] = useState(0);

  const siguiendo = solicitud !== null && (vista === null || EN_CURSO.has(vista.estado));

  useEffect(() => {
    if (solicitud === null || !siguiendo) return;
    let vigente = true;
    const espera = setTimeout(
      () => {
        exigir(
          api.GET("/caso/evidencias/{solicitud_id}", {
            params: { path: { solicitud_id: solicitud } },
          }),
        )
          .then((actual) => {
            if (!vigente) return;
            setVista(actual);
            setConsulta((escrita) => escrita || actual.consulta);
          })
          .catch((fallo: unknown) => {
            if (vigente) setError(fallo);
          });
      },
      vista === null ? 0 : ESPERA_AVANCE_MS,
    );
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
  }, [solicitud, siguiendo, vista]);

  function seguir(nueva: string) {
    setAportando(false);
    setVista(null);
    setSolicitud(nueva);
    setParametros({ solicitud: nueva }, { replace: true });
  }

  async function enviar() {
    setError(null);
    setAportando(false);
    setVista(null);
    setSolicitud(null);
    if (consulta.trim() === "") {
      setError(
        errorDeValidacion("Escriba la consulta o la afirmación para la que busca evidencia."),
      );
      return;
    }
    setEnviando(true);
    try {
      const nueva = await exigir(
        api.POST("/caso/evidencias", { body: { consulta: consulta.trim() } }),
      );
      setSolicitud(nueva.id);
      setParametros({ solicitud: nueva.id }, { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Buscar evidencia">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <Form
        className="formulario"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
      >
        <CampoTextoLargo
          etiqueta="Consulta o afirmación"
          descripcion="Escriba la afirmación que quiere sustentar o la pregunta que quiere responder. El sistema busca solo en las fuentes de su tema y de su colección personal."
          name="consulta"
          value={consulta}
          onChange={setConsulta}
          maxLength={1000}
        />
        <AvisoError error={error} />
        <Boton type="submit" isDisabled={enviando || siguiendo}>
          {enviando ? "Enviando…" : "Buscar evidencia"}
        </Boton>
      </Form>
      {siguiendo ? (
        <AvanceSolicitud
          solicitud={solicitud}
          alTerminar={() => {
            setVista(null);
          }}
          mensaje={
            <>Buscando evidencia en las fuentes de su tema. Puede tardar uno o dos minutos.</>
          }
        />
      ) : null}
      {vista && !EN_CURSO.has(vista.estado) ? (
        <Resultado vista={vista} alReenviar={seguir} />
      ) : null}
      {vista?.estado === "entregada" && solicitud !== null ? (
        <DecisionSobreResultado
          key={`${solicitud}-${String(aportes)}`}
          solicitud={solicitud}
          alAportar={
            vista.abstencion
              ? () => {
                  setAportando(true);
                }
              : undefined
          }
        />
      ) : null}
      {vista?.estado === "entregada" && vista.abstencion && solicitud !== null ? (
        <AporteDeFuente
          key={solicitud}
          solicitud={solicitud}
          abierto={aportando}
          alAportado={() => {
            setAportes((n) => n + 1);
          }}
          alNuevaBusqueda={seguir}
        />
      ) : null}
    </Marco>
  );
}

function Resultado({ vista, alReenviar }: { vista: Vista; alReenviar: (nueva: string) => void }) {
  if (vista.estado === "no_atendida") {
    return (
      <NoAtendida
        solicitud={vista.id}
        mensaje={
          MOTIVOS_NO_ATENDIDA[vista.motivo ?? ""] ??
          "La búsqueda no pudo atenderse. Intente de nuevo en unos minutos."
        }
        alReenviar={alReenviar}
      />
    );
  }
  if (vista.abstencion) {
    return (
      <section aria-labelledby="titulo-resultado" className="evidencia">
        <h2 id="titulo-resultado">{vista.aviso ?? "Sin evidencia suficiente"}</h2>
        <p>
          Las fuentes de su tema no tienen evidencia suficiente para esta consulta, así que el
          sistema no genera una respuesta.
        </p>
        {vista.invitacion_aporte ? <p>{vista.invitacion_aporte}</p> : null}
      </section>
    );
  }
  return (
    <section aria-labelledby="titulo-resultado" className="evidencia">
      <h2 id="titulo-resultado">Evidencia encontrada</h2>
      {vista.etiqueta === "verificada" ? <Verificada /> : null}
      {vista.etiqueta === "con_advertencias" ? (
        <div className="aviso aviso--importante" role="status">
          <p>Con advertencias: revise estas observaciones antes de usar la respuesta.</p>
          <ul>
            {vista.advertencias.map((advertencia) => (
              <li key={advertencia}>{advertencia}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <ListaAfirmaciones afirmaciones={vista.respuesta} etiqueta="Respuesta con sus citas" />
      {vista.evidencia_divergente.length > 0 ? (
        <>
          <h3>Evidencia divergente</h3>
          <p>
            Las fuentes no coinciden. Se presentan las posturas tal como aparecen; la decisión es
            suya.
          </p>
          <ListaAfirmaciones afirmaciones={vista.evidencia_divergente} etiqueta="Posturas" />
        </>
      ) : null}
      {vista.notas_para_el_estudiante.length > 0 ? (
        <>
          <h3>Notas</h3>
          <ul>
            {vista.notas_para_el_estudiante.map((nota) => (
              <li key={nota}>{nota}</li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>Fuentes recomendadas</h3>
      {vista.fuentes.length === 0 ? (
        <p>Ninguna de las fuentes citadas tiene acceso abierto comprobado.</p>
      ) : (
        <ul className="fuentes">
          {vista.fuentes.map((fuente) => (
            <li key={fuente.documento_id}>
              <p>{fuente.referencia}</p>
              <p className="campo__descripcion">
                Citada en {fuente.identificadores.join(", ")}
                {fuente.url_acceso_abierto ? (
                  <>
                    {". "}
                    <a href={fuente.url_acceso_abierto} target="_blank" rel="noopener noreferrer">
                      Acceso abierto<span className="oculto"> (otra pestaña)</span>
                    </a>
                  </>
                ) : null}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ListaAfirmaciones({
  afirmaciones,
  etiqueta,
}: {
  afirmaciones: Afirmacion[];
  etiqueta: string;
}) {
  return (
    <ul className="afirmaciones" aria-label={etiqueta}>
      {afirmaciones.map((afirmacion, indice) => (
        <li key={`${indice}-${afirmacion.afirmacion}`}>
          <p>{afirmacion.afirmacion}</p>
          {afirmacion.citas.map((cita) => (
            <details key={cita.identificador} className="cita">
              <summary>
                Cita {cita.identificador}: {cita.titulo ?? "Documento sin título"}
              </summary>
              <blockquote>{cita.texto}</blockquote>
              <p className="campo__descripcion">
                {documento(cita)}
                {SECCIONES[cita.seccion] ?? cita.seccion}
                {paginas(cita)}
                {cita.incompleto ? ". Documento con extracción incompleta" : ""}
                {cita.acceso_abierto && cita.url_acceso_abierto ? (
                  <>
                    {". "}
                    <a href={cita.url_acceso_abierto} target="_blank" rel="noopener noreferrer">
                      Ver la fuente en acceso abierto<span className="oculto"> (otra pestaña)</span>
                    </a>
                  </>
                ) : cita.aporte ? (
                  ""
                ) : (
                  ". Sin acceso abierto comprobado"
                )}
              </p>
              {cita.aporte ? <DatosAportados aporte={cita.aporte} /> : null}
            </details>
          ))}
        </li>
      ))}
    </ul>
  );
}

// Propuesta de redacción de un párrafo (T27; RF-07, CU-06). El estudiante elige un párrafo de
// su versión vigente (hasta unas 250 palabras, CP-09); el sistema propone una versión del mismo
// párrafo, de hasta 1.2 veces su extensión (CP-10), y la muestra junto al original con los
// cambios resaltados y la pauta de la guía que justifica cada uno. El estudiante decide qué
// incorporar: la propuesta no modifica su borrador.
import { useEffect, useMemo, useState } from "react";
import { Form } from "react-aria-components";
import { useSearchParams } from "react-router";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, AvisoInformativo, Boton, Selector } from "../componentes/controles";
import { DecisionSobreResultado } from "../componentes/Decision";
import { Marco } from "../componentes/Marco";
import { AvanceSolicitud, NoAtendida, Verificada } from "../componentes/Seguimiento";
import { compararPalabras, type Tramo } from "../diferencias";
import { numero } from "../formato";
import { EN_CURSO } from "../solicitudes";

type Vista = Esquemas["VistaRedaccion"];
type Parrafos = Esquemas["ParrafosRedactables"];
type Cambio = Esquemas["CambioVista"];

const ESPERA_AVANCE_MS = 2000;
const PALABRAS_DE_MUESTRA = 9;
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "La propuesta se interrumpió por un reinicio del servidor. Vuelva a pedirla.",
};

function muestra(texto: string): string {
  const palabras = texto.split(/\s+/).filter(Boolean);
  const inicio = palabras.slice(0, PALABRAS_DE_MUESTRA).join(" ");
  return palabras.length > PALABRAS_DE_MUESTRA ? `${inicio}…` : inicio;
}

export function Redaccion() {
  const [datos, setDatos] = useState<Parrafos | null>(null);
  const [parrafo, setParrafo] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  // La solicitud va en la dirección (?solicitud=...): el resultado sobrevive a una recarga.
  const [parametros, setParametros] = useSearchParams();
  const [solicitud, setSolicitud] = useState<string | null>(parametros.get("solicitud"));
  const [enviando, setEnviando] = useState(false);

  const siguiendo = solicitud !== null && (vista === null || EN_CURSO.has(vista.estado));
  const elegido = datos?.parrafos.find((p) => p.id === parrafo) ?? null;

  useEffect(() => {
    let vigente = true;
    exigir(api.GET("/caso/redaccion/parrafos"))
      .then((lista) => {
        if (vigente) setDatos(lista);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    if (solicitud === null || !siguiendo) return;
    let vigente = true;
    const espera = setTimeout(
      () => {
        exigir(
          api.GET("/caso/redaccion/{solicitud_id}", {
            params: { path: { solicitud_id: solicitud } },
          }),
        )
          .then((actual) => {
            if (!vigente) return;
            setVista(actual);
            setParrafo((anterior) => anterior ?? actual.parrafo_id);
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
    setVista(null);
    setSolicitud(nueva);
    setParametros({ solicitud: nueva }, { replace: true });
  }

  async function enviar() {
    setError(null);
    setVista(null);
    setSolicitud(null);
    if (parrafo === null) {
      setError(errorDeValidacion("Elija el párrafo que quiere mejorar."));
      return;
    }
    setEnviando(true);
    try {
      const nueva = await exigir(api.POST("/caso/redaccion", { body: { parrafo_id: parrafo } }));
      setSolicitud(nueva.id);
      setParametros({ solicitud: nueva.id }, { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Proponer una redacción">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        Elija un párrafo de su versión vigente, de hasta {numero(datos?.limite_palabras ?? 250)}{" "}
        palabras. El sistema propone una versión del mismo párrafo, con el mismo contenido, y
        explica cada cambio con las pautas de redacción del programa. Usted decide qué incorporar:
        su borrador no se modifica.
      </p>
      {datos !== null && datos.parrafos.length === 0 ? (
        <AvisoInformativo>
          <p>Su versión vigente no tiene párrafos de texto. Cargue una versión desde el panel.</p>
        </AvisoInformativo>
      ) : (
        <Form
          className="formulario"
          onSubmit={(evento) => {
            evento.preventDefault();
            void enviar();
          }}
        >
          <Selector
            etiqueta="Párrafo"
            opciones={(datos?.parrafos ?? []).map((p) => ({
              id: p.id,
              etiqueta: `${p.seccion}: ${muestra(p.texto)} (${numero(p.palabras)} palabras${
                p.dentro_del_limite ? "" : ", excede el límite"
              })`,
            }))}
            valor={parrafo}
            alCambiar={(valor) => {
              setParrafo(valor);
              setError(null);
            }}
            requerido
            marcador="Elija el párrafo"
          />
          {elegido ? (
            <div className="parrafo-elegido">
              <p className="parrafo-elegido__titulo">
                Párrafo elegido ({numero(elegido.palabras)} palabras)
              </p>
              <blockquote>{elegido.texto}</blockquote>
            </div>
          ) : null}
          <AvisoError error={error} />
          <Boton type="submit" isDisabled={enviando || siguiendo || datos === null}>
            {enviando ? "Enviando…" : "Proponer una redacción"}
          </Boton>
        </Form>
      )}
      {siguiendo ? (
        <AvanceSolicitud
          solicitud={solicitud}
          alTerminar={() => {
            setVista(null);
          }}
          mensaje={
            <>
              Preparando la propuesta con las pautas de redacción. Puede tardar uno o dos minutos.
            </>
          }
        />
      ) : null}
      {vista && !EN_CURSO.has(vista.estado) ? (
        <Resultado vista={vista} alReenviar={seguir} />
      ) : null}
      {vista?.estado === "entregada" && solicitud !== null ? (
        <DecisionSobreResultado key={solicitud} solicitud={solicitud} />
      ) : null}
    </Marco>
  );
}

function Resultado({ vista, alReenviar }: { vista: Vista; alReenviar: (nueva: string) => void }) {
  const comparacion = useMemo(
    () => compararPalabras(vista.original ?? "", vista.propuesta ?? ""),
    [vista.original, vista.propuesta],
  );
  if (vista.estado === "no_atendida") {
    return (
      <NoAtendida
        solicitud={vista.id}
        mensaje={
          MOTIVOS_NO_ATENDIDA[vista.motivo ?? ""] ??
          "La propuesta no pudo atenderse. Intente de nuevo en unos minutos."
        }
        alReenviar={alReenviar}
      />
    );
  }
  if (vista.abstencion || vista.propuesta === null) {
    return (
      <section aria-labelledby="titulo-resultado" className="evidencia">
        <h2 id="titulo-resultado">{vista.aviso ?? "Sin evidencia suficiente"}</h2>
        <p>
          Las guías del programa no tienen pautas suficientes para este párrafo, así que el sistema
          no genera una propuesta.
        </p>
      </section>
    );
  }
  return (
    <section aria-labelledby="titulo-resultado" className="evidencia">
      <h2 id="titulo-resultado">Propuesta de redacción</h2>
      {vista.etiqueta === "verificada" ? <Verificada /> : null}
      {vista.etiqueta === "con_advertencias" ? (
        <div className="aviso aviso--importante" role="status">
          <p>Con advertencias: revise estas observaciones antes de usar la propuesta.</p>
          <ul>
            {vista.advertencias.map((advertencia) => (
              <li key={advertencia}>{advertencia}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="texto-suave">
        En el original se tachan las palabras que la propuesta cambia; en la propuesta se resaltan
        las nuevas.
      </p>
      <div className="comparacion">
        <section aria-labelledby="titulo-original" className="comparacion__lado">
          <h3 id="titulo-original">Original ({numero(vista.palabras_original)} palabras)</h3>
          <p>
            <Tramos tramos={comparacion.original} />
          </p>
        </section>
        <section aria-labelledby="titulo-propuesta" className="comparacion__lado">
          <h3 id="titulo-propuesta">
            Propuesta ({numero(vista.palabras_propuesta)} palabras, hasta{" "}
            {numero(vista.limite_palabras_propuesta)})
          </h3>
          <p>
            <Tramos tramos={comparacion.propuesta} />
          </p>
        </section>
      </div>
      <h3>Cambios y sus razones</h3>
      {vista.cambios.length === 0 ? (
        <p className="vacio">El párrafo ya cumple las pautas: la propuesta no lo cambia.</p>
      ) : (
        <ol className="afirmaciones" aria-label="Cambios propuestos">
          {vista.cambios.map((cambio, indice) => (
            <FilaCambio key={`${String(indice)}-${cambio.antes}`} cambio={cambio} />
          ))}
        </ol>
      )}
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
    </section>
  );
}

function Tramos({ tramos }: { tramos: Tramo[] }) {
  return tramos.map((tramo, indice) => {
    const separador = indice > 0 ? " " : "";
    const clave = `${String(indice)}-${tramo.tipo}`;
    if (tramo.tipo === "quitado") {
      return (
        <span key={clave}>
          {separador}
          <del className="tramo tramo--quitado">{tramo.texto}</del>
        </span>
      );
    }
    if (tramo.tipo === "agregado") {
      return (
        <span key={clave}>
          {separador}
          <ins className="tramo tramo--agregado">{tramo.texto}</ins>
        </span>
      );
    }
    return <span key={clave}>{`${separador}${tramo.texto}`}</span>;
  });
}

function FilaCambio({ cambio }: { cambio: Cambio }) {
  return (
    <li>
      <p>
        <span className="insignia insignia--cambio">{cambio.tipo_nombre}</span>
      </p>
      <p>
        <strong>Antes:</strong> «{cambio.antes}». <strong>Después:</strong> «{cambio.despues}».
      </p>
      <p>
        <strong>Por qué:</strong> {cambio.razon}
      </p>
      {cambio.citas.map((cita) => (
        <details key={cita.identificador} className="cita">
          <summary>
            Pauta {cita.identificador}: {cita.guia ?? "Guía del programa"}
            {cita.apartado ? `, ${cita.apartado}` : ""}
          </summary>
          <blockquote>{cita.texto}</blockquote>
        </details>
      ))}
    </li>
  );
}

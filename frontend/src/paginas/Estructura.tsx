// Diagnóstico de estructura y coherencia de una sección (T23; RF-04, CU-03). El estudiante
// elige una sección de su versión vigente; el sistema la revisa con las guías del programa y
// devuelve hallazgos con ubicación, severidad y recomendación, sin reescribirla. Cada cita
// se despliega con el fragmento de la guía que sustenta el criterio.
import { useEffect, useState } from "react";
import { Form } from "react-aria-components";
import { useSearchParams } from "react-router";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, AvisoInformativo, Boton, Selector } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { numero } from "../formato";

type Vista = Esquemas["VistaEstructura"];
type Seccion = Esquemas["SeccionRevisable"];
type Hallazgo = Esquemas["HallazgoVista"];

const ESPERA_AVANCE_MS = 2000;
const EN_CURSO = new Set(["recibida", "asignada", "recuperando", "generando"]);
const SEVERIDADES: Record<string, string> = { alta: "Alta", media: "Media", baja: "Baja" };
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "La revisión se interrumpió por un reinicio del servidor. Vuelva a pedirla.",
};

export function Estructura() {
  const [secciones, setSecciones] = useState<Seccion[] | null>(null);
  const [seccion, setSeccion] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  // La solicitud va en la dirección (?solicitud=...): el resultado sobrevive a una recarga.
  const [parametros, setParametros] = useSearchParams();
  const [solicitud, setSolicitud] = useState<string | null>(parametros.get("solicitud"));
  const [enviando, setEnviando] = useState(false);

  const siguiendo = solicitud !== null && (vista === null || EN_CURSO.has(vista.estado));

  useEffect(() => {
    let vigente = true;
    exigir(api.GET("/caso/estructura/secciones"))
      .then((lista) => {
        if (vigente) setSecciones(lista);
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
          api.GET("/caso/estructura/{solicitud_id}", {
            params: { path: { solicitud_id: solicitud } },
          }),
        )
          .then((actual) => {
            if (!vigente) return;
            setVista(actual);
            setSeccion((elegida) => elegida ?? actual.seccion_id);
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

  async function enviar() {
    setError(null);
    setVista(null);
    setSolicitud(null);
    if (seccion === null) {
      setError(errorDeValidacion("Elija la sección que quiere revisar."));
      return;
    }
    setEnviando(true);
    try {
      const nueva = await exigir(api.POST("/caso/estructura", { body: { seccion_id: seccion } }));
      setSolicitud(nueva.id);
      setParametros({ solicitud: nueva.id }, { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Revisar estructura y coherencia">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        El sistema revisa una sección de su versión vigente con las guías del programa: la
        alineación entre problema, objetivos e hipótesis, la secuencia lógica y la cohesión. Le dice
        qué revisar y dónde; no reescribe su texto.
      </p>
      {secciones !== null && secciones.length === 0 ? (
        <AvisoInformativo>
          <p>
            Su versión vigente no tiene secciones detectadas. Use estilos de título en su documento
            y vuelva a cargarlo desde el panel.
          </p>
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
            etiqueta="Sección"
            opciones={(secciones ?? []).map((s) => ({
              id: s.id,
              etiqueta: `${s.titulo} (${numero(s.palabras)} palabras)`,
            }))}
            valor={seccion}
            alCambiar={setSeccion}
            requerido
            marcador="Elija la sección"
          />
          <AvisoError error={error} />
          <Boton type="submit" isDisabled={enviando || siguiendo || secciones === null}>
            {enviando ? "Enviando…" : "Revisar la sección"}
          </Boton>
        </Form>
      )}
      {siguiendo ? (
        <p role="status" aria-live="polite">
          Revisando la sección con las guías del programa. Puede tardar uno o dos minutos.
        </p>
      ) : null}
      {vista && !EN_CURSO.has(vista.estado) ? <Resultado vista={vista} /> : null}
    </Marco>
  );
}

function Resultado({ vista }: { vista: Vista }) {
  if (vista.estado === "no_atendida") {
    return (
      <div className="aviso aviso--error" role="alert">
        <p>
          {MOTIVOS_NO_ATENDIDA[vista.motivo ?? ""] ??
            "La revisión no pudo atenderse. Intente de nuevo en unos minutos."}
        </p>
      </div>
    );
  }
  if (vista.abstencion) {
    return (
      <section aria-labelledby="titulo-resultado" className="evidencia">
        <h2 id="titulo-resultado">{vista.aviso ?? "Sin evidencia suficiente"}</h2>
        <p>
          Las guías del programa no tienen criterios suficientes para revisar esta sección, así que
          el sistema no genera un diagnóstico.
        </p>
      </section>
    );
  }
  return (
    <section aria-labelledby="titulo-resultado" className="evidencia">
      <h2 id="titulo-resultado">
        Diagnóstico{vista.seccion_titulo ? `: ${vista.seccion_titulo}` : ""}
      </h2>
      {vista.etiqueta === "con_advertencias" ? (
        <div className="aviso aviso--importante" role="status">
          <p>Con advertencias: revise estas observaciones antes de usar el diagnóstico.</p>
          <ul>
            {vista.advertencias.map((advertencia) => (
              <li key={advertencia}>{advertencia}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {vista.hallazgos.length === 0 ? (
        <p className="vacio">No se encontraron problemas en estos indicadores.</p>
      ) : (
        <ol className="afirmaciones" aria-label="Hallazgos, de mayor a menor severidad">
          {vista.hallazgos.map((hallazgo, indice) => (
            <FilaHallazgo key={`${String(indice)}-${hallazgo.ubicacion}`} hallazgo={hallazgo} />
          ))}
        </ol>
      )}
      {vista.fortalezas.length > 0 ? (
        <>
          <h3>Fortalezas</h3>
          <ul>
            {vista.fortalezas.map((fortaleza) => (
              <li key={fortaleza}>{fortaleza}</li>
            ))}
          </ul>
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
    </section>
  );
}

export function FilaHallazgo({ hallazgo }: { hallazgo: Hallazgo }) {
  return (
    <li>
      <p>
        <span className={`insignia insignia--severidad-${hallazgo.severidad}`}>
          Severidad {SEVERIDADES[hallazgo.severidad] ?? hallazgo.severidad}
        </span>{" "}
        {hallazgo.indicador_nombre}. Ubicación: {hallazgo.ubicacion}.
      </p>
      <p>{hallazgo.descripcion}</p>
      <p>
        <strong>Qué revisar:</strong> {hallazgo.recomendacion}
      </p>
      {hallazgo.citas.map((cita) => (
        <details key={cita.identificador} className="cita">
          <summary>
            Criterio {cita.identificador}: {cita.guia ?? "Guía del programa"}
            {cita.apartado ? `, ${cita.apartado}` : ""}
          </summary>
          <blockquote>{cita.texto}</blockquote>
        </details>
      ))}
    </li>
  );
}

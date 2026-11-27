// Diagnóstico metodológico de una sección (T26; RF-06, CU-05). El estudiante elige una sección
// de su versión vigente (por defecto, la de método); el sistema la revisa con la lista de
// comprobación del diseño que declara y devuelve hallazgos y preguntas sobre lo que falta, sin
// reescribirla ni inventar datos. Cada criterio se despliega con el fragmento de la guía.
import { useEffect, useState } from "react";
import { Form } from "react-aria-components";
import { useSearchParams } from "react-router";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, AvisoInformativo, Boton, Selector } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { numero } from "../formato";
import { EN_CURSO } from "../solicitudes";
import { FilaHallazgo } from "./Estructura";

type Vista = Esquemas["VistaMetodologia"];
type Seccion = Esquemas["SeccionMetodologica"];

const ESPERA_AVANCE_MS = 2000;
const DE_METODO = /m[eé]todo|metodolog/i;
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "La revisión se interrumpió por un reinicio del servidor. Vuelva a pedirla.",
};

function etiquetaSeccion(seccion: Seccion): string {
  const diseno = seccion.diseno ? `, diseño ${seccion.diseno}` : "";
  return `${seccion.titulo} (${numero(seccion.palabras)} palabras${diseno})`;
}

export function Metodologia() {
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
    exigir(api.GET("/caso/metodologia/secciones"))
      .then((lista) => {
        if (!vigente) return;
        setSecciones(lista);
        // Por defecto, la sección de método si la hay.
        setSeccion((elegida) => elegida ?? lista.find((s) => DE_METODO.test(s.titulo))?.id ?? null);
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
          api.GET("/caso/metodologia/{solicitud_id}", {
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
      const nueva = await exigir(api.POST("/caso/metodologia", { body: { seccion_id: seccion } }));
      setSolicitud(nueva.id);
      setParametros({ solicitud: nueva.id }, { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Revisar la metodología">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        El sistema revisa una sección de su versión vigente con la lista de comprobación del diseño
        que usted declara: la justificación del diseño, la validez de técnicas e instrumentos y el
        análisis de datos. Le dice qué revisar y le pregunta lo que falta; no reescribe su texto ni
        inventa datos.
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
            opciones={(secciones ?? []).map((s) => ({ id: s.id, etiqueta: etiquetaSeccion(s) }))}
            valor={seccion}
            alCambiar={setSeccion}
            requerido
            marcador="Elija la sección"
          />
          <AvisoError error={error} />
          <Boton type="submit" isDisabled={enviando || siguiendo || secciones === null}>
            {enviando ? "Enviando…" : "Revisar la metodología"}
          </Boton>
        </Form>
      )}
      {siguiendo ? (
        <p role="status" aria-live="polite">
          Revisando la metodología con la lista de comprobación. Puede tardar uno o dos minutos.
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
        Diagnóstico metodológico{vista.seccion_titulo ? `: ${vista.seccion_titulo}` : ""}
      </h2>
      <p>
        {vista.diseno
          ? `Diseño declarado: ${vista.diseno}. Se revisó con su lista de comprobación y con los elementos comunes a todos los diseños.`
          : "La sección no nombra su diseño: se revisó con los elementos comunes a todos los diseños."}
      </p>
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
      {vista.preguntas_al_estudiante.length > 0 ? (
        <>
          <h3>Preguntas para usted</h3>
          <ul aria-label="Preguntas sobre lo que falta">
            {vista.preguntas_al_estudiante.map((pregunta) => (
              <li key={pregunta}>{pregunta}</li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>Hallazgos</h3>
      {vista.hallazgos.length === 0 ? (
        <p className="vacio">No se encontraron problemas en estos indicadores.</p>
      ) : (
        <ol className="afirmaciones" aria-label="Hallazgos, de mayor a menor severidad">
          {vista.hallazgos.map((hallazgo, indice) => (
            <FilaHallazgo key={`${String(indice)}-${hallazgo.ubicacion}`} hallazgo={hallazgo} />
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

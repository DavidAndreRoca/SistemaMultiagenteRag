// Plan de tarea del hito (T24; RF-05, CU-04). El estudiante elige un hito con versión cargada;
// el sistema compara las instrucciones del programa con el estado del borrador y devuelve
// tareas ordenadas con su criterio de logro. El plan se puede copiar o descargar en texto; no
// modifica el borrador. Sin instrucciones del hito en las guías, el sistema se abstiene.
import { useEffect, useState } from "react";
import { Form } from "react-aria-components";
import { useSearchParams } from "react-router";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, AvisoInformativo, Boton, Selector } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { fechaHora } from "../formato";

type Vista = Esquemas["VistaPlan"];
type Hito = Esquemas["HitoDelPlan"];

const ESPERA_AVANCE_MS = 2000;
const EN_CURSO = new Set(["recibida", "asignada", "recuperando", "generando"]);
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "El plan se interrumpió por un reinicio del servidor. Vuelva a pedirlo.",
};

/** El plan en texto plano, para copiarlo o descargarlo. */
export function planEnTexto(vista: Vista): string {
  const lineas = [`Plan de tarea: ${vista.hito ?? ""}`, ""];
  for (const tarea of vista.tareas) {
    lineas.push(`${String(tarea.orden)}. ${tarea.tarea}`);
    lineas.push(`   Criterio de logro: ${tarea.criterio_de_logro}`);
  }
  if (vista.notas_para_el_estudiante.length > 0) {
    lineas.push("", "Notas:");
    for (const nota of vista.notas_para_el_estudiante) lineas.push(`- ${nota}`);
  }
  return lineas.join("\n") + "\n";
}

export function Plan() {
  const [hitos, setHitos] = useState<Hito[] | null>(null);
  const [hito, setHito] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  // La solicitud va en la dirección (?solicitud=...): el resultado sobrevive a una recarga.
  const [parametros, setParametros] = useSearchParams();
  const [solicitud, setSolicitud] = useState<string | null>(parametros.get("solicitud"));
  const [enviando, setEnviando] = useState(false);

  const siguiendo = solicitud !== null && (vista === null || EN_CURSO.has(vista.estado));
  const conVersion = (hitos ?? []).filter((h) => h.version_cargada_en !== null);

  useEffect(() => {
    let vigente = true;
    exigir(api.GET("/caso/plan/hitos"))
      .then((lista) => {
        if (!vigente) return;
        setHitos(lista);
        // Por defecto, el último hito con versión cargada.
        const cargados = lista.filter((h) => h.version_cargada_en !== null);
        setHito((elegido) => elegido ?? cargados.at(-1)?.codigo ?? null);
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
          api.GET("/caso/plan/{solicitud_id}", {
            params: { path: { solicitud_id: solicitud } },
          }),
        )
          .then((actual) => {
            if (vigente) setVista(actual);
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
    if (hito === null) {
      setError(errorDeValidacion("Elija el hito para el que quiere el plan."));
      return;
    }
    setEnviando(true);
    try {
      const nueva = await exigir(api.POST("/caso/plan", { body: { hito } }));
      setSolicitud(nueva.id);
      setParametros({ solicitud: nueva.id }, { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Plan de tarea del hito">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        El sistema compara las instrucciones del programa para el hito con lo que ya tiene su
        borrador y le devuelve una lista ordenada de tareas, cada una con su criterio de logro.
        Puede copiarla o descargarla; su borrador no se modifica.
      </p>
      {hitos !== null && conVersion.length === 0 ? (
        <AvisoInformativo>
          <p>Todavía no cargó ninguna versión. Cargue su borrador desde el panel.</p>
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
            etiqueta="Hito"
            opciones={conVersion.map((h) => ({
              id: h.codigo,
              etiqueta: `${h.nombre} (versión del ${fechaHora(h.version_cargada_en ?? "")})`,
            }))}
            valor={hito}
            alCambiar={setHito}
            requerido
            marcador="Elija el hito"
          />
          <AvisoError error={error} />
          <Boton type="submit" isDisabled={enviando || siguiendo || hitos === null}>
            {enviando ? "Enviando…" : "Preparar el plan"}
          </Boton>
        </Form>
      )}
      {siguiendo ? (
        <p role="status" aria-live="polite">
          Preparando el plan con las instrucciones del programa. Puede tardar uno o dos minutos.
        </p>
      ) : null}
      {vista && !EN_CURSO.has(vista.estado) ? <Resultado vista={vista} /> : null}
    </Marco>
  );
}

function Resultado({ vista }: { vista: Vista }) {
  const [copiado, setCopiado] = useState<string | null>(null);
  if (vista.estado === "no_atendida") {
    return (
      <div className="aviso aviso--error" role="alert">
        <p>
          {MOTIVOS_NO_ATENDIDA[vista.motivo ?? ""] ??
            "El plan no pudo atenderse. Intente de nuevo en unos minutos."}
        </p>
      </div>
    );
  }
  if (vista.abstencion) {
    return (
      <section aria-labelledby="titulo-resultado" className="evidencia">
        <h2 id="titulo-resultado">{vista.aviso ?? "Sin evidencia suficiente"}</h2>
        <p>
          {vista.motivo_abstencion ??
            "Las guías del programa no alcanzan para armar el plan de este hito."}{" "}
          El sistema no genera un plan sin las instrucciones del programa.
        </p>
      </section>
    );
  }
  const texto = planEnTexto(vista);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado("Plan copiado.");
    } catch {
      setCopiado("No se pudo copiar: use la descarga en texto.");
    }
  }

  function descargar() {
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(new Blob([texto], { type: "text/plain;charset=utf-8" }));
    enlace.download = "plan-de-tarea.txt";
    enlace.click();
    URL.revokeObjectURL(enlace.href);
  }

  return (
    <section aria-labelledby="titulo-resultado" className="evidencia">
      <h2 id="titulo-resultado">Plan de tarea{vista.hito ? `: ${vista.hito}` : ""}</h2>
      {vista.etiqueta === "con_advertencias" ? (
        <div className="aviso aviso--importante" role="status">
          <p>Con advertencias: revise estas observaciones antes de usar el plan.</p>
          <ul>
            {vista.advertencias.map((advertencia) => (
              <li key={advertencia}>{advertencia}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="botones">
        <Boton variante="secundario" onPress={() => void copiar()}>
          Copiar el plan
        </Boton>
        <Boton variante="secundario" onPress={descargar}>
          Descargar en texto
        </Boton>
      </div>
      {copiado ? <p role="status">{copiado}</p> : null}
      <ol className="afirmaciones" aria-label="Tareas, en orden">
        {vista.tareas.map((tarea) => (
          <li key={tarea.orden}>
            <p>{tarea.tarea}</p>
            <p>
              <strong>Criterio de logro:</strong> {tarea.criterio_de_logro}
            </p>
            {tarea.citas.map((cita) => (
              <details key={cita.identificador} className="cita">
                <summary>
                  Instrucción {cita.identificador}: {cita.guia ?? "Guía del programa"}
                  {cita.apartado ? `, ${cita.apartado}` : ""}
                </summary>
                <blockquote>{cita.texto}</blockquote>
              </details>
            ))}
          </li>
        ))}
      </ol>
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

// Verificación de las referencias del caso (T20; RF-09, CU-08). El sistema comprueba cada
// referencia de la lista de la versión vigente en las bases bibliográficas y cruza las citas
// del texto con la lista según la norma del caso. El estado de cada referencia lo decide el
// sistema; si un servicio no responde, la referencia queda "No comprobable", nunca
// inexistente (RN-18).
import { useEffect, useState } from "react";

import { api, exigir, type Esquemas } from "../api/cliente";
import { AvisoError, Boton } from "../componentes/controles";
import { Marco } from "../componentes/Marco";

type Vista = Esquemas["VistaVerificacion"];
type Referencia = Esquemas["ReferenciaVerificadaVista"];

const ESPERA_AVANCE_MS = 2000;
const EN_CURSO = new Set(["recibida", "asignada", "recuperando", "generando"]);
const ESTADOS: Record<string, string> = {
  verificada: "Verificada",
  con_discrepancias: "Con discrepancias",
  no_localizada: "No localizada",
  no_comprobable: "No comprobable",
};
const AYUDA_ESTADO: Record<string, string> = {
  verificada: "La obra existe y sus datos coinciden con la fuente.",
  con_discrepancias: "La obra existe, pero algún dato de su referencia difiere de la fuente.",
  no_localizada: "Ninguna base bibliográfica la encontró. Revise si la obra existe.",
  no_comprobable:
    "Un servicio no respondió y no se pudo comprobar. No significa que la obra no exista.",
};
const MOTIVOS_NO_ATENDIDA: Record<string, string> = {
  interrumpida: "La verificación se interrumpió por un reinicio del servidor. Vuelva a pedirla.",
  grobid_no_disponible:
    "El servicio que estructura la lista de referencias no está disponible. Intente más tarde.",
};

export function Referencias() {
  const [error, setError] = useState<unknown>(null);
  const [vista, setVista] = useState<Vista | null>(null);
  const [solicitud, setSolicitud] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const siguiendo = solicitud !== null && (vista === null || EN_CURSO.has(vista.estado));

  useEffect(() => {
    if (solicitud === null || !siguiendo) return;
    let vigente = true;
    const espera = setTimeout(() => {
      exigir(
        api.GET("/caso/referencias/{solicitud_id}", {
          params: { path: { solicitud_id: solicitud } },
        }),
      )
        .then((actual) => {
          if (vigente) setVista(actual);
        })
        .catch((fallo: unknown) => {
          if (vigente) setError(fallo);
        });
    }, ESPERA_AVANCE_MS);
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
  }, [solicitud, siguiendo, vista]);

  async function verificar() {
    setError(null);
    setVista(null);
    setSolicitud(null);
    setEnviando(true);
    try {
      const nueva = await exigir(api.POST("/caso/referencias"));
      setSolicitud(nueva.id);
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Verificar referencias">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        El sistema comprueba cada referencia de la lista de su versión vigente en las bases
        bibliográficas (Crossref y OpenAlex) y cruza las citas del texto con la lista según la norma
        de su caso.
      </p>
      <AvisoError error={error} />
      <Boton onPress={() => void verificar()} isDisabled={enviando || siguiendo}>
        {enviando ? "Enviando…" : "Verificar las referencias"}
      </Boton>
      {siguiendo ? (
        <p role="status" aria-live="polite">
          {vista?.progreso
            ? `Verificando referencias: ${String(vista.progreso.hechas)} de ${String(vista.progreso.total)}.`
            : "Preparando la lista de referencias."}{" "}
          Puede tardar unos minutos.
        </p>
      ) : null}
      {vista && !EN_CURSO.has(vista.estado) ? <Informe vista={vista} /> : null}
    </Marco>
  );
}

function Informe({ vista }: { vista: Vista }) {
  if (vista.estado === "no_atendida") {
    return (
      <div className="aviso aviso--error" role="alert">
        <p>
          {MOTIVOS_NO_ATENDIDA[vista.motivo ?? ""] ??
            "La verificación no pudo atenderse. Intente de nuevo en unos minutos."}
        </p>
      </div>
    );
  }
  return (
    <section aria-labelledby="titulo-informe" className="referencias">
      <h2 id="titulo-informe">Informe de referencias</h2>
      {vista.norma_nombre ? <p>Norma del caso: {vista.norma_nombre}.</p> : null}
      {vista.avisos.length > 0 ? (
        <div className="aviso aviso--importante" role="status">
          <ul>
            {vista.avisos.map((aviso) => (
              <li key={aviso}>{aviso}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <ul className="resumen-estados" aria-label="Resumen por estado">
        {Object.entries(ESTADOS).map(([clave, nombre]) => (
          <li key={clave}>
            {nombre}: {String(vista.resumen[clave] ?? 0)}
          </li>
        ))}
      </ul>
      <h3>Referencias de la lista</h3>
      <ol className="lista-referencias" aria-label="Estado de cada referencia">
        {vista.referencias.map((referencia) => (
          <FilaReferencia key={referencia.indice} referencia={referencia} />
        ))}
      </ol>
      <h3>Citas sin entrada en la lista</h3>
      {vista.citas_sin_entrada.length === 0 ? (
        <p>Todas las citas del texto tienen su entrada en la lista.</p>
      ) : (
        <ul aria-label="Citas sin entrada">
          {vista.citas_sin_entrada.map((cita) => (
            <li key={cita}>{cita}</li>
          ))}
        </ul>
      )}
      <h3>Entradas no citadas en el texto</h3>
      {vista.entradas_no_citadas.length === 0 ? (
        <p>Todas las entradas de la lista se citan en el texto.</p>
      ) : (
        <ul aria-label="Entradas no citadas">
          {vista.entradas_no_citadas.map((entrada) => (
            <li key={entrada.indice}>
              Entrada {String(entrada.indice)}: {entrada.texto}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FilaReferencia({ referencia }: { referencia: Referencia }) {
  return (
    <li value={referencia.indice} className="referencia">
      <p>
        <strong className={`estado-referencia estado-referencia--${referencia.estado}`}>
          {ESTADOS[referencia.estado] ?? referencia.estado}
        </strong>
        {referencia.citada ? null : <span>. No se cita en el texto</span>}
      </p>
      <p className="referencia__texto">{referencia.texto_original}</p>
      <p className="campo__descripcion">{AYUDA_ESTADO[referencia.estado]}</p>
      {referencia.discrepancias.length > 0 ? (
        <ul aria-label={`Discrepancias de la referencia ${String(referencia.indice)}`}>
          {referencia.discrepancias.map((d) => (
            <li key={d.campo}>
              {d.etiqueta}: en su referencia, {d.valor_borrador ?? "no figura"}; en la fuente,{" "}
              {d.valor_fuente ?? "no figura"}.
            </li>
          ))}
        </ul>
      ) : null}
      {referencia.explicacion ? <p>{referencia.explicacion}</p> : null}
      {referencia.url_doi ? (
        <p>
          <a href={referencia.url_doi} target="_blank" rel="noopener noreferrer">
            Ver la obra en doi.org<span className="oculto"> (otra pestaña)</span>
          </a>
        </p>
      ) : null}
    </li>
  );
}

// Seguimiento de una solicitud (T29; RF-22, F-16). El avance llega por eventos enviados por el
// servidor (GET /caso/solicitudes/{id}/eventos): el navegador reconecta solo y, al
// reconectarse, el servidor envía el estado actual. Si el navegador no tiene EventSource, la
// pantalla sigue con su consulta periódica del resultado. Una solicitud que no pudo atenderse
// se vuelve a pedir con un botón (reenvío enlazado a la original).
import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { api, exigir, RUTA_BASE } from "../api/cliente";
import { AvisoError, Boton } from "./controles";

const PASOS: { estado: string; nombre: string }[] = [
  { estado: "recibida", nombre: "En cola" },
  { estado: "asignada", nombre: "Asignada a su agente" },
  { estado: "recuperando", nombre: "Buscando en las guías y fuentes" },
  { estado: "generando", nombre: "Preparando la respuesta" },
  { estado: "verificando", nombre: "Verificando" },
  { estado: "entregada", nombre: "Entregada" },
];
const FINALES = new Set(["entregada", "no_atendida", "rechazada"]);
const MAX_INTENTOS_TECNICOS = 3;

interface EventoEstado {
  estado: string;
  motivo: string | null;
  intentos_tecnicos: number;
}

export function AvanceSolicitud({
  solicitud,
  mensaje,
  alTerminar,
}: {
  solicitud: string;
  mensaje: ReactNode;
  alTerminar?: () => void;
}) {
  const [actual, setActual] = useState<EventoEstado | null>(null);

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const fuente = new EventSource(`${RUTA_BASE}/caso/solicitudes/${solicitud}/eventos`);
    fuente.addEventListener("estado", (evento) => {
      const datos = JSON.parse((evento as MessageEvent<string>).data) as EventoEstado;
      setActual(datos);
      if (FINALES.has(datos.estado)) {
        fuente.close();
        alTerminar?.();
      }
    });
    return () => {
      fuente.close();
    };
    // alTerminar puede cambiar en cada dibujo: el canal depende solo de la solicitud.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solicitud]);

  const indice = PASOS.findIndex((p) => p.estado === actual?.estado);
  const reintento =
    actual !== null && actual.estado === "recibida" && actual.intentos_tecnicos > 0
      ? `El servicio del modelo no respondió; el sistema lo intentará de nuevo (intento ${String(
          actual.intentos_tecnicos + 1,
        )} de ${String(MAX_INTENTOS_TECNICOS + 1)}).`
      : null;
  return (
    <div className="avance-solicitud">
      <p role="status" aria-live="polite">
        {mensaje}
        {indice >= 0 ? ` Estado: ${PASOS[indice]?.nombre ?? ""}.` : ""}
      </p>
      {actual !== null ? (
        <ol className="pasos" aria-label="Avance de la solicitud">
          {PASOS.map((paso, i) => (
            <li
              key={paso.estado}
              className={
                i < indice ? "paso paso--hecho" : i === indice ? "paso paso--actual" : "paso"
              }
              aria-current={i === indice ? "step" : undefined}
            >
              {paso.nombre}
              {i < indice ? <span className="oculto"> (hecho)</span> : null}
            </li>
          ))}
        </ol>
      ) : null}
      {reintento ? <p>{reintento}</p> : null}
    </div>
  );
}

export function NoAtendida({
  solicitud,
  mensaje,
  alReenviar,
}: {
  solicitud: string;
  mensaje: string;
  alReenviar: (nueva: string) => void;
}) {
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function reenviar() {
    setError(null);
    setEnviando(true);
    try {
      const nueva = await exigir(
        api.POST("/caso/solicitudes/{solicitud_id}/reenvio", {
          params: { path: { solicitud_id: solicitud } },
        }),
      );
      alReenviar(nueva.id);
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="aviso aviso--error" role="alert">
      <p>{mensaje}</p>
      <AvisoError error={error} />
      <Boton variante="secundario" onPress={() => void reenviar()} isDisabled={enviando}>
        {enviando ? "Enviando…" : "Volver a pedir"}
      </Boton>
    </div>
  );
}

/** Otra revisión sobre el mismo alcance (por ejemplo, la metodología de la misma sección). */
export function OtraRevision({
  solicitud,
  tipo,
  ruta,
  texto,
}: {
  solicitud: string;
  tipo: "revision_estructura" | "revision_metodologica";
  ruta: string;
  texto: string;
}) {
  const navegar = useNavigate();
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function pedir() {
    setError(null);
    setEnviando(true);
    try {
      const nueva = await exigir(
        api.POST("/caso/solicitudes/{solicitud_id}/mismo-alcance", {
          params: { path: { solicitud_id: solicitud } },
          body: { tipo },
        }),
      );
      void navegar(`${ruta}?solicitud=${nueva.id}`);
    } catch (fallo) {
      setError(fallo);
      setEnviando(false);
    }
  }

  return (
    <div className="otra-revision">
      <AvisoError error={error} />
      <Boton variante="secundario" onPress={() => void pedir()} isDisabled={enviando}>
        {enviando ? "Enviando…" : texto}
      </Boton>
    </div>
  );
}

/** Etiqueta "Verificada" (T30): el resultado superó las comprobaciones que aplican a su tipo. */
export function Verificada() {
  return (
    <p className="etiqueta-resultado">
      <span className="insignia insignia--entregada">Verificada</span> Superó las comprobaciones del
      sistema antes de entregarse: esquema, límites, citas a los fragmentos recuperados y fidelidad
      a las fuentes, según el tipo.
    </p>
  );
}

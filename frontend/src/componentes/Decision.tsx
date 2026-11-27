// Decisión del investigador sobre un resultado entregado (T31; RF-12, CU-11, HU-10). Sobre una
// propuesta: aceptarla, usarla con cambios o no usarla; tras "Sin evidencia suficiente":
// continuar sin aportar una fuente (aportar una fuente llega en T32). Cambiar de decisión
// registra otra que reemplaza a la anterior; las dos se conservan en el historial.
import { useEffect, useState } from "react";

import { api, exigir, type Esquemas } from "../api/cliente";
import { fechaHora } from "../formato";
import { AvisoError, Boton } from "./controles";

type VistaDecision = Esquemas["VistaDecision"];
type Opcion = Esquemas["OpcionDecision"];

export const TEXTOS_OPCION: Record<Opcion, string> = {
  aceptar: "La acepto",
  modificar: "La usaré con cambios",
  rechazar: "No la usaré",
  continuar: "Continuar sin aportar una fuente",
  aportar: "Aportar una fuente",
};
const OPCION_PENDIENTE: Opcion = "aportar";

export function DecisionSobreResultado({ solicitud }: { solicitud: string }) {
  const [vista, setVista] = useState<VistaDecision | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const [ronda, setRonda] = useState(0);

  useEffect(() => {
    let vigente = true;
    exigir(
      api.GET("/caso/solicitudes/{solicitud_id}/decision", {
        params: { path: { solicitud_id: solicitud } },
      }),
    )
      .then((datos) => {
        if (vigente) setVista(datos);
      })
      // Si no carga, el resultado se sigue viendo; solo falta la decisión.
      .catch(() => {
        if (vigente) setVista(null);
      });
    return () => {
      vigente = false;
    };
  }, [solicitud, ronda]);

  async function decidir(opcion: Opcion) {
    setError(null);
    setEnviando(true);
    try {
      await exigir(
        api.POST("/caso/solicitudes/{solicitud_id}/decision", {
          params: { path: { solicitud_id: solicitud } },
          body: { opcion },
        }),
      );
      setRonda((n) => n + 1);
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  if (vista === null || vista.opciones.length === 0) return null;
  const vigente = vista.vigente;
  const anteriores = vista.historial.slice(0, -1);
  return (
    <section aria-labelledby={`titulo-decision-${solicitud}`} className="decision">
      <h2 id={`titulo-decision-${solicitud}`}>Su decisión sobre este resultado</h2>
      {vigente ? (
        <p role="status">
          Decidió: <strong>{TEXTOS_OPCION[vigente.opcion]}</strong>, el{" "}
          {fechaHora(vigente.decidida_en)}. Puede cambiarla; la anterior se conserva.
        </p>
      ) : (
        <p>
          Indique qué hará con este resultado. Se registra en su caso y cuenta para el seguimiento
          de su uso del sistema.
        </p>
      )}
      <AvisoError error={error} />
      <div className="decision__opciones">
        {vista.opciones.map((opcion) =>
          opcion === OPCION_PENDIENTE ? (
            <span key={opcion} className="decision__pendiente">
              <Boton variante="secundario" isDisabled>
                {TEXTOS_OPCION[opcion]}
              </Boton>{" "}
              <span className="insignia insignia--pendiente">Pendiente</span>
            </span>
          ) : (
            <Boton
              key={opcion}
              variante={vigente?.opcion === opcion ? "principal" : "secundario"}
              isDisabled={enviando || vigente?.opcion === opcion}
              onPress={() => void decidir(opcion)}
            >
              {TEXTOS_OPCION[opcion]}
            </Boton>
          ),
        )}
      </div>
      {anteriores.length > 0 ? (
        <details className="decision__historial">
          <summary>Decisiones anteriores ({anteriores.length})</summary>
          <ol>
            {anteriores.map((d) => (
              <li key={d.id}>
                {TEXTOS_OPCION[d.opcion]}, el {fechaHora(d.decidida_en)}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </section>
  );
}

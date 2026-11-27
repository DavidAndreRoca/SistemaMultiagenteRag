// Historial del caso (T33; RF-14, CU-13, HU-12, CP-20): versiones, solicitudes, resultados
// con su etiqueta, decisiones y fuentes aportadas en orden cronológico, filtrable por hito y
// periodo, con enlace al detalle de cada resultado y un resumen descargable para la
// declaración de herramientas. Todo viene de rutas que filtran por el caso de la sesión.
import { useEffect, useState } from "react";
import { Form } from "react-aria-components";

import { api, errorDeValidacion, exigir, RUTA_BASE, type Esquemas } from "../api/cliente";
import { AvisoError, Boton, CampoTexto, Selector } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { fechaHora } from "../formato";
import { ETIQUETAS, NOMBRES_PEDIDO, PANTALLAS } from "../solicitudes";

type Evento = Esquemas["EventoHistorial"];
type Hito = Esquemas["HitoVista"];

const CLASES: Record<string, string> = {
  version: "Versión",
  solicitud: "Solicitud",
  resultado: "Resultado",
  decision: "Decisión",
  aporte: "Fuente aportada",
};
const TODOS = "todos";
const FECHA = /^\d{4}-\d{2}-\d{2}$/;

interface Filtros {
  hito: string;
  desde: string;
  hasta: string;
}

function consulta(filtros: Filtros): Record<string, string> {
  const params: Record<string, string> = {};
  if (filtros.hito !== TODOS) params.hito = filtros.hito;
  if (filtros.desde) params.desde = filtros.desde;
  if (filtros.hasta) params.hasta = filtros.hasta;
  return params;
}

export function Historial() {
  const [hitos, setHitos] = useState<Hito[]>([]);
  const [hito, setHito] = useState<string>(TODOS);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [aplicados, setAplicados] = useState<Filtros>({ hito: TODOS, desde: "", hasta: "" });
  const [eventos, setEventos] = useState<Evento[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    exigir(api.GET("/caso"))
      .then((caso) => {
        setHitos(caso.hitos);
      })
      .catch(() => {
        setHitos([]);
      });
  }, []);

  useEffect(() => {
    let vigente = true;
    const { hito: h, desde: d, hasta: a } = consulta(aplicados);
    exigir(api.GET("/caso/historial", { params: { query: { hito: h, desde: d, hasta: a } } }))
      .then((datos) => {
        if (!vigente) return;
        setEventos(datos.eventos);
        setError(null);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, [aplicados]);

  function filtrar() {
    if ((desde && !FECHA.test(desde)) || (hasta && !FECHA.test(hasta))) {
      setError(errorDeValidacion("Escriba las fechas como AAAA-MM-DD, por ejemplo 2026-11-27."));
      return;
    }
    setError(null);
    setEventos(null);
    setAplicados({ hito, desde, hasta });
  }

  const descarga = `${RUTA_BASE}/caso/historial/resumen?${new URLSearchParams(
    consulta(aplicados),
  ).toString()}`;

  return (
    <Marco titulo="Historial del caso">
      <p>
        <a href="/panel">Volver al panel del caso</a>
      </p>
      <p>
        Su trayectoria en el sistema, de lo más antiguo a lo más reciente: versiones cargadas,
        solicitudes, resultados con su etiqueta, decisiones y fuentes aportadas. Solo usted la ve.
      </p>
      <section aria-labelledby="titulo-filtros">
        <h2 id="titulo-filtros">Filtrar</h2>
        <Form
          className="formulario filtros"
          onSubmit={(evento) => {
            evento.preventDefault();
            filtrar();
          }}
        >
          <Selector
            etiqueta="Hito"
            opciones={[
              { id: TODOS, etiqueta: "Todos los hitos" },
              ...hitos.map((h) => ({ id: h.codigo, etiqueta: `${h.nombre}: ${h.contenido}` })),
            ]}
            valor={hito}
            alCambiar={(valor) => {
              setHito(valor ?? TODOS);
            }}
          />
          <CampoTexto
            etiqueta="Desde"
            descripcion="Fecha AAAA-MM-DD (opcional)."
            value={desde}
            onChange={setDesde}
          />
          <CampoTexto
            etiqueta="Hasta"
            descripcion="Fecha AAAA-MM-DD (opcional)."
            value={hasta}
            onChange={setHasta}
          />
          <Boton type="submit">Aplicar el filtro</Boton>
        </Form>
      </section>
      <AvisoError error={error} />
      <section aria-labelledby="titulo-eventos">
        <h2 id="titulo-eventos">Su trayectoria</h2>
        <p>
          <a className="accion__enlace" href={descarga} download>
            Descargar el resumen para su declaración de herramientas
          </a>
        </p>
        {eventos === null ? (
          error ? null : (
            <p role="status">Cargando su historial…</p>
          )
        ) : eventos.length === 0 ? (
          <p className="vacio">No hay registros con este filtro.</p>
        ) : (
          <table className="tabla">
            <caption className="oculto">
              Historial del caso, de lo más antiguo a lo más reciente
            </caption>
            <thead>
              <tr>
                <th scope="col">Fecha y hora</th>
                <th scope="col">Hito</th>
                <th scope="col">Qué pasó</th>
                <th scope="col">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((evento, indice) => (
                <FilaEvento key={`${evento.momento}-${String(indice)}`} evento={evento} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </Marco>
  );
}

function FilaEvento({ evento }: { evento: Evento }) {
  const etiqueta = evento.etiqueta ? ETIQUETAS[evento.etiqueta] : undefined;
  const pantalla = evento.tipo ? PANTALLAS[evento.tipo] : undefined;
  return (
    <tr>
      <td>{fechaHora(evento.momento)}</td>
      <td>{evento.nombre_hito ?? evento.hito ?? ""}</td>
      <th scope="row">
        <span className="historial__clase">{CLASES[evento.clase] ?? evento.clase}</span>{" "}
        {evento.descripcion}{" "}
        {etiqueta ? <span className={`insignia ${etiqueta.clase}`}>{etiqueta.texto}</span> : null}
        {evento.vigente === false && evento.clase === "decision" ? (
          <span className="insignia">Reemplazada</span>
        ) : null}
      </th>
      <td>
        {pantalla && evento.solicitud_id ? (
          <a href={`${pantalla}?solicitud=${evento.solicitud_id}`}>
            Ver
            <span className="oculto">
              {` ${NOMBRES_PEDIDO[evento.tipo ?? ""] ?? "el resultado"}`}
            </span>
          </a>
        ) : null}
      </td>
    </tr>
  );
}

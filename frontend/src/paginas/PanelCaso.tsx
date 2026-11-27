// Panel del caso (RF-19 en parte, RF-01): versión vigente por hito, carga de versiones y
// lista de versiones. Todo lo que muestra viene de rutas que filtran por el caso de la sesión.
import { useCallback, useEffect, useState } from "react";
import { Form } from "react-aria-components";

import { api, errorDeValidacion, exigir, type Esquemas } from "../api/cliente";
import {
  AvisoError,
  AvisoInformativo,
  Boton,
  Selector,
  SelectorArchivo,
} from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { fechaHora, numero, tamano } from "../formato";

type Caso = Esquemas["CasoPropio"];
type Version = Esquemas["VersionResumen"];
type Carga = Esquemas["ResultadoCarga"];
type CuerpoCarga = Esquemas["Body_cargar_version_caso_versiones_post"];
type SolicitudResumen = Esquemas["SolicitudResumen"];

const TIPO_DOCX = ".docx";

export function PanelCaso() {
  const [caso, setCaso] = useState<Caso | null>(null);
  const [versiones, setVersiones] = useState<Version[] | null>(null);
  const [solicitudes, setSolicitudes] = useState<SolicitudResumen[]>([]);
  const [errorCarga, setErrorCarga] = useState<unknown>(null);

  const [ronda, setRonda] = useState(0);

  useEffect(() => {
    let vigente = true;
    Promise.all([
      exigir(api.GET("/caso")),
      exigir(api.GET("/caso/versiones")),
      exigir(api.GET("/caso/solicitudes")),
    ])
      .then(([datos, lista, pedidas]) => {
        if (!vigente) return;
        setCaso(datos);
        setVersiones(lista);
        setSolicitudes(pedidas);
        setErrorCarga(null);
      })
      .catch((fallo: unknown) => {
        if (vigente) setErrorCarga(fallo);
      });
    return () => {
      vigente = false;
    };
  }, [ronda]);

  const actualizar = useCallback(() => {
    setRonda((n) => n + 1);
  }, []);

  return (
    <Marco titulo="Panel del caso">
      <AvisoError error={errorCarga} />
      {caso === null || versiones === null ? (
        errorCarga ? null : (
          <p role="status">Cargando los datos del caso…</p>
        )
      ) : (
        <>
          <DatosDelCaso caso={caso} />
          <Acciones />
          <ListaDeSolicitudes solicitudes={solicitudes} />
          <VigentesPorHito caso={caso} versiones={versiones} />
          <CargarVersion caso={caso} alCargar={actualizar} />
          <ListaDeVersiones versiones={versiones} />
        </>
      )}
    </Marco>
  );
}

function DatosDelCaso({ caso }: { caso: Caso }) {
  return (
    <section aria-labelledby="titulo-caso">
      <h2 id="titulo-caso">Su caso</h2>
      <dl className="datos">
        <dt>Código</dt>
        <dd>{caso.codigo}</dd>
        <dt>Tema</dt>
        <dd>{caso.tema}</dd>
        <dt>Autoría</dt>
        <dd>{caso.tipo_autoria === "pareja" ? "En pareja" : "Individual"}</dd>
        <dt>Norma de citación</dt>
        <dd>{caso.norma_citacion.toUpperCase()}</dd>
      </dl>
    </section>
  );
}

function VigentesPorHito({ caso, versiones }: { caso: Caso; versiones: Version[] }) {
  const vigentes = new Map(versiones.filter((v) => v.vigente).map((v) => [v.hito, v]));
  return (
    <section aria-labelledby="titulo-vigentes">
      <h2 id="titulo-vigentes">Versión vigente por hito</h2>
      {versiones.length === 0 ? (
        <AvisoInformativo>
          <p>
            Aún no ha cargado ninguna versión de su borrador. Cargue la primera para empezar a pedir
            revisiones.
          </p>
        </AvisoInformativo>
      ) : null}
      <table className="tabla">
        <caption className="oculto">Versión vigente de cada hito</caption>
        <thead>
          <tr>
            <th scope="col">Hito</th>
            <th scope="col">Contenido</th>
            <th scope="col">Versión vigente</th>
          </tr>
        </thead>
        <tbody>
          {caso.hitos.map((hito) => {
            const vigente = vigentes.get(hito.codigo);
            return (
              <tr key={hito.codigo}>
                <th scope="row">{hito.nombre}</th>
                <td>{hito.contenido}</td>
                <td>
                  {vigente
                    ? `Cargada el ${fechaHora(vigente.cargada_en)} (${numero(vigente.palabras)} palabras)`
                    : "Sin versión"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function CargarVersion({ caso, alCargar }: { caso: Caso; alCargar: () => void }) {
  const [hito, setHito] = useState<string | null>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<Carga | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setResultado(null);
    setError(null);
    if (hito === null || archivo === null) {
      setError(errorDeValidacion("Elija el hito y el archivo .docx de su borrador."));
      return;
    }
    const datos = new FormData();
    datos.append("hito", hito);
    datos.append("archivo", archivo);
    setEnviando(true);
    try {
      const carga = await exigir(
        api.POST("/caso/versiones", {
          // Formulario con archivo: el contrato lo describe como campos de texto.
          body: datos as unknown as CuerpoCarga,
          bodySerializer: (cuerpo) => cuerpo as unknown as FormData,
        }),
      );
      setResultado(carga);
      setArchivo(null);
      alCargar();
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section aria-labelledby="titulo-carga">
      <h2 id="titulo-carga">Cargar una versión</h2>
      <p>
        Cada carga crea una versión nueva, que queda vigente en su hito. Las versiones anteriores se
        conservan. Solo se admiten archivos .docx de hasta 15 MB.
      </p>
      <Form
        className="formulario"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
      >
        <Selector
          etiqueta="Hito"
          opciones={caso.hitos.map((h) => ({
            id: h.codigo,
            etiqueta: `${h.nombre}: ${h.contenido}`,
          }))}
          valor={hito}
          alCambiar={setHito}
          requerido
          marcador="Elija el hito"
        />
        <SelectorArchivo
          etiqueta="Elegir el archivo .docx"
          tipos={[TIPO_DOCX]}
          archivo={archivo}
          alElegir={setArchivo}
        />
        <AvisoError error={error} />
        {resultado ? (
          <AvisoInformativo>
            <p>Versión cargada el {fechaHora(resultado.version.cargada_en)}.</p>
            {resultado.mensajes.map((mensaje) => (
              <p key={mensaje}>{mensaje}</p>
            ))}
          </AvisoInformativo>
        ) : null}
        <Boton type="submit" isDisabled={enviando}>
          {enviando ? "Cargando…" : "Cargar la versión"}
        </Boton>
      </Form>
    </section>
  );
}

function ListaDeVersiones({ versiones }: { versiones: Version[] }) {
  return (
    <section aria-labelledby="titulo-versiones">
      <h2 id="titulo-versiones">Versiones cargadas</h2>
      {versiones.length === 0 ? (
        <p className="vacio">Todavía no hay versiones.</p>
      ) : (
        <table className="tabla">
          <caption className="oculto">
            Versiones cargadas, de la más reciente a la más antigua
          </caption>
          <thead>
            <tr>
              <th scope="col">Hito</th>
              <th scope="col">Fecha y hora</th>
              <th scope="col">Estado</th>
              <th scope="col">Palabras</th>
              <th scope="col">Tamaño</th>
            </tr>
          </thead>
          <tbody>
            {versiones.map((version) => (
              <tr key={version.id}>
                <th scope="row">{version.nombre_hito ?? version.hito}</th>
                <td>{fechaHora(version.cargada_en)}</td>
                <td>
                  {version.vigente ? (
                    <span className="insignia insignia--entregada">Vigente</span>
                  ) : (
                    "Anterior"
                  )}
                </td>
                <td>{numero(version.palabras)}</td>
                <td>{tamano(version.tamano_bytes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

const PANTALLAS: Record<string, string> = {
  busqueda_evidencia: "/panel/evidencia",
  verificacion_referencias: "/panel/referencias",
  revision_estructura: "/panel/estructura",
  propuesta_redaccion: "/panel/redaccion",
  revision_metodologica: "/panel/metodologia",
  plan_tarea: "/panel/plan",
};
const NOMBRES_PEDIDO: Record<string, string> = {
  busqueda_evidencia: "Búsqueda de evidencia",
  verificacion_referencias: "Verificación de referencias",
  revision_estructura: "Revisión de estructura y coherencia",
  propuesta_redaccion: "Propuesta de redacción",
  revision_metodologica: "Revisión metodológica",
  plan_tarea: "Plan de tarea",
};

const ESTADOS_SOLICITUD: Record<string, string> = {
  recibida: "En curso",
  asignada: "En curso",
  recuperando: "En curso",
  generando: "En curso",
  verificando: "En curso",
  reintentando: "En curso",
  entregada: "Entregada",
  no_atendida: "No atendida",
};

/** Búsquedas de evidencia y verificaciones de referencias, para volver a abrir su resultado. */
function ListaDeSolicitudes({ solicitudes }: { solicitudes: SolicitudResumen[] }) {
  return (
    <section aria-labelledby="titulo-solicitudes">
      <h2 id="titulo-solicitudes">Sus solicitudes</h2>
      {solicitudes.length === 0 ? (
        <p className="vacio">Todavía no hizo ninguna solicitud.</p>
      ) : (
        <table className="tabla">
          <caption className="oculto">Sus solicitudes, de la más reciente a la más antigua</caption>
          <thead>
            <tr>
              <th scope="col">Pedido</th>
              <th scope="col">Fecha y hora</th>
              <th scope="col">Estado</th>
              <th scope="col">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {solicitudes.map((solicitud) => {
              const evidencia = solicitud.tipo === "busqueda_evidencia";
              const pantalla = PANTALLAS[solicitud.tipo] ?? "/panel";
              return (
                <tr key={solicitud.id}>
                  <th scope="row">
                    {evidencia
                      ? `Evidencia: ${solicitud.consulta ?? ""}`
                      : (NOMBRES_PEDIDO[solicitud.tipo] ?? solicitud.tipo)}
                  </th>
                  <td>{fechaHora(solicitud.creada_en)}</td>
                  <td>
                    <span className={`insignia insignia--${solicitud.estado}`}>
                      {ESTADOS_SOLICITUD[solicitud.estado] ?? solicitud.estado}
                    </span>
                  </td>
                  <td>
                    <a href={`${pantalla}?solicitud=${solicitud.id}`}>
                      Ver resultado
                      <span className="oculto">
                        {` de: ${NOMBRES_PEDIDO[solicitud.tipo] ?? solicitud.tipo}`}
                      </span>
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}

interface Accion {
  titulo: string;
  descripcion: string;
  enlace?: { href: string; texto: string };
}

// Lo que el caso puede pedir. Los agentes aún no implementados figuran como pendientes, sin
// enlace (prototipo, 26-11-2026).
const ACCIONES: Accion[] = [
  {
    titulo: "Evidencia",
    descripcion: "Respalde una afirmación o responda una pregunta con fragmentos citados.",
    enlace: { href: "/panel/evidencia", texto: "Buscar evidencia en las fuentes de su tema" },
  },
  {
    titulo: "Referencias",
    descripcion: "Compruebe cada referencia en las bases bibliográficas y cruce sus citas.",
    enlace: { href: "/panel/referencias", texto: "Verificar las referencias de su borrador" },
  },
  {
    titulo: "Estructura y coherencia",
    descripcion: "Diagnóstico de una sección según las guías del programa.",
    enlace: { href: "/panel/estructura", texto: "Revisar la estructura de una sección" },
  },
  {
    titulo: "Metodología",
    descripcion: "Diagnóstico del diseño, la muestra y el análisis.",
    enlace: { href: "/panel/metodologia", texto: "Revisar la metodología de una sección" },
  },
  {
    titulo: "Redacción",
    descripcion: "Propuesta acotada para un párrafo, con cada cambio justificado.",
    enlace: { href: "/panel/redaccion", texto: "Proponer una redacción para un párrafo" },
  },
  {
    titulo: "Plan de tarea",
    descripcion: "Tareas ordenadas para el hito, cada una con su criterio de logro.",
    enlace: { href: "/panel/plan", texto: "Preparar el plan de tarea del hito" },
  },
];

function Acciones() {
  return (
    <section aria-labelledby="titulo-acciones" className="sin-tarjeta">
      <h2 id="titulo-acciones">Qué puede pedir</h2>
      <ul className="acciones">
        {ACCIONES.map((accion) => (
          <li key={accion.titulo} className={accion.enlace ? "accion" : "accion accion--pendiente"}>
            <h3>{accion.titulo}</h3>
            <p>{accion.descripcion}</p>
            {accion.enlace ? (
              <a className="accion__enlace" href={accion.enlace.href}>
                {accion.enlace.texto}
              </a>
            ) : (
              <span className="insignia insignia--pendiente">Pendiente</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

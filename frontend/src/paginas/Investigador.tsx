// Pantalla del investigador (A2): temas con su colección científica y casos (RF-16, T07).
// Las credenciales iniciales de un caso nuevo se muestran una sola vez y no se guardan.
import { useCallback, useEffect, useState } from "react";
import { Form } from "react-aria-components";

import { api, exigir, type Esquemas } from "../api/cliente";
import {
  AvisoError,
  AvisoInformativo,
  Boton,
  CampoTexto,
  Selector,
} from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { numero } from "../formato";

type Coleccion = Esquemas["ColeccionVista"];
type Caso = Esquemas["CasoVista"];
type CasoCreado = Esquemas["CasoCreadoVista"];
type Autoria = Esquemas["TipoAutoria"];

export function Investigador() {
  const [colecciones, setColecciones] = useState<Coleccion[] | null>(null);
  const [casos, setCasos] = useState<Caso[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const [ronda, setRonda] = useState(0);

  useEffect(() => {
    let vigente = true;
    Promise.all([
      exigir(api.GET("/investigador/colecciones")),
      exigir(api.GET("/investigador/casos")),
    ])
      .then(([cols, lista]) => {
        if (!vigente) return;
        setColecciones(cols);
        setCasos(lista);
        setError(null);
      })
      .catch((fallo: unknown) => {
        if (vigente) setError(fallo);
      });
    return () => {
      vigente = false;
    };
  }, [ronda]);

  const actualizar = useCallback(() => {
    setRonda((n) => n + 1);
  }, []);

  const temas = (colecciones ?? []).filter((c) => c.tipo === "cientifica" && c.tema !== null);

  return (
    <Marco titulo="Casos y colecciones">
      <AvisoError error={error} />
      {colecciones === null || casos === null ? (
        error ? null : (
          <p role="status">Cargando casos y colecciones…</p>
        )
      ) : (
        <>
          <section aria-labelledby="titulo-casos">
            <h2 id="titulo-casos">Casos</h2>
            <TablaCasos casos={casos} />
            <NuevoCaso temas={temas} alCrear={actualizar} />
          </section>
          <section aria-labelledby="titulo-temas">
            <h2 id="titulo-temas">Temas y colecciones científicas</h2>
            <TablaTemas temas={temas} />
            <NuevoTema alCrear={actualizar} />
          </section>
        </>
      )}
    </Marco>
  );
}

function TablaCasos({ casos }: { casos: Caso[] }) {
  if (casos.length === 0) return <p>Todavía no hay casos registrados.</p>;
  return (
    <table className="tabla">
      <caption className="oculto">Casos registrados</caption>
      <thead>
        <tr>
          <th scope="col">Código</th>
          <th scope="col">Tema</th>
          <th scope="col">Autoría</th>
          <th scope="col">Norma</th>
          <th scope="col">Estado</th>
        </tr>
      </thead>
      <tbody>
        {casos.map((caso) => (
          <tr key={caso.codigo}>
            <th scope="row">{caso.codigo}</th>
            <td>{caso.tema}</td>
            <td>{caso.tipo_autoria === "pareja" ? "En pareja" : "Individual"}</td>
            <td>{caso.norma_citacion.toUpperCase()}</td>
            <td>{caso.estado === "habilitado" ? "Habilitado" : "Desactivado"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TablaTemas({ temas }: { temas: Coleccion[] }) {
  if (temas.length === 0) return <p>Todavía no hay temas.</p>;
  return (
    <table className="tabla">
      <caption className="oculto">Temas con su colección científica</caption>
      <thead>
        <tr>
          <th scope="col">Tema</th>
          <th scope="col">Documentos incluidos</th>
          <th scope="col">Excluidos</th>
          <th scope="col">Pendientes</th>
        </tr>
      </thead>
      <tbody>
        {temas.map((tema) => (
          <tr key={tema.id}>
            <th scope="row">{tema.tema}</th>
            <td>{numero(tema.n_incluidas)}</td>
            <td>{numero(tema.n_excluidas)}</td>
            <td>{numero(tema.n_pendientes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function NuevoTema({ alCrear }: { alCrear: () => void }) {
  const [tema, setTema] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [creado, setCreado] = useState<string | null>(null);

  async function enviar() {
    setError(null);
    setCreado(null);
    try {
      const nuevo = await exigir(
        api.POST("/investigador/colecciones/cientificas", { body: { tema: tema.trim() } }),
      );
      setCreado(nuevo.tema);
      setTema("");
      alCrear();
    } catch (fallo) {
      setError(fallo);
    }
  }

  return (
    <Form
      className="formulario"
      onSubmit={(evento) => {
        evento.preventDefault();
        void enviar();
      }}
    >
      <h3>Crear un tema</h3>
      <CampoTexto
        etiqueta="Código del tema"
        descripcion="Por ejemplo, TEMA-01. Crea su colección científica vacía."
        name="tema"
        value={tema}
        onChange={setTema}
        isRequired
        minLength={2}
        maxLength={80}
      />
      <AvisoError error={error} />
      {creado ? (
        <AvisoInformativo>
          <p>Tema {creado} creado.</p>
        </AvisoInformativo>
      ) : null}
      <Boton type="submit">Crear el tema</Boton>
    </Form>
  );
}

function NuevoCaso({ temas, alCrear }: { temas: Coleccion[]; alCrear: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [autoria, setAutoria] = useState<string | null>("individual");
  const [tema, setTema] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [creado, setCreado] = useState<CasoCreado | null>(null);

  async function enviar() {
    setError(null);
    setCreado(null);
    if (tema === null || autoria === null) {
      setError(new Error("Elija el tema y el tipo de autoría."));
      return;
    }
    try {
      const nuevo = await exigir(
        api.POST("/investigador/casos", {
          body: { codigo: codigo.trim(), tipo_autoria: autoria as Autoria, tema },
        }),
      );
      setCreado(nuevo);
      setCodigo("");
      alCrear();
    } catch (fallo) {
      setError(fallo);
    }
  }

  return (
    <Form
      className="formulario"
      onSubmit={(evento) => {
        evento.preventDefault();
        void enviar();
      }}
    >
      <h3>Registrar un caso</h3>
      <CampoTexto
        etiqueta="Código del caso"
        descripcion="Por ejemplo, CASO-01. Identifica al caso sin datos personales."
        name="codigo"
        value={codigo}
        onChange={setCodigo}
        isRequired
        minLength={2}
        maxLength={30}
      />
      <Selector
        etiqueta="Tipo de autoría"
        opciones={[
          { id: "individual", etiqueta: "Individual" },
          { id: "pareja", etiqueta: "En pareja" },
        ]}
        valor={autoria}
        alCambiar={setAutoria}
        requerido
      />
      <Selector
        etiqueta="Tema"
        opciones={temas.map((t) => ({ id: t.tema ?? "", etiqueta: t.tema ?? "" }))}
        valor={tema}
        alCambiar={setTema}
        requerido
        marcador="Elija el tema"
      />
      <AvisoError error={error} />
      {creado ? (
        <div className="aviso aviso--importante" role="alert">
          <p>
            Caso {creado.codigo} registrado. Entregue estas credenciales al estudiante: se muestran
            una sola vez y no se pueden recuperar.
          </p>
          <ul>
            {creado.credenciales.map((credencial) => (
              <li key={credencial.cuenta}>
                Cuenta <strong>{credencial.cuenta}</strong>, contraseña inicial{" "}
                <code>{credencial.contrasena_inicial}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <Boton type="submit">Registrar el caso</Boton>
    </Form>
  );
}

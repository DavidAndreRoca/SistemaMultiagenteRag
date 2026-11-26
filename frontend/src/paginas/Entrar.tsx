// Inicio de sesión con código de cuenta y contraseña (RF-18, F-01).
import { useState } from "react";
import { Form } from "react-aria-components";
import { useNavigate } from "react-router";

import { AvisoError, Boton, CampoTexto } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { inicioDe, useSesion } from "../sesion/sesion";

export function Entrar() {
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [codigo, setCodigo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setError(null);
    setEnviando(true);
    try {
      const sesion = await entrar(codigo.trim(), contrasena);
      await navegar(inicioDe(sesion), { replace: true });
    } catch (fallo) {
      setError(fallo);
      setContrasena("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Iniciar sesión" variante="acceso">
      <p>Ingrese el código de su cuenta y su contraseña.</p>
      <Form
        className="formulario"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
      >
        <CampoTexto
          etiqueta="Código de cuenta"
          name="codigo"
          value={codigo}
          onChange={setCodigo}
          isRequired
          autoComplete="username"
        />
        <CampoTexto
          etiqueta="Contraseña"
          name="contrasena"
          type="password"
          value={contrasena}
          onChange={setContrasena}
          isRequired
          autoComplete="current-password"
        />
        <AvisoError error={error} />
        <Boton type="submit" isDisabled={enviando}>
          {enviando ? "Ingresando…" : "Ingresar"}
        </Boton>
      </Form>
    </Marco>
  );
}

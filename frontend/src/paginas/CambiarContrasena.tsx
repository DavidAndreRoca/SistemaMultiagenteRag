// Cambio de la contraseña inicial, obligatorio antes de usar el sistema (RF-18).
import { useState } from "react";
import { Form } from "react-aria-components";
import { useNavigate } from "react-router";

import { api, exigir } from "../api/cliente";
import { AvisoError, AvisoInformativo, Boton, CampoTexto } from "../componentes/controles";
import { Marco } from "../componentes/Marco";
import { inicioDe, useSesion } from "../sesion/sesion";

export function CambiarContrasena() {
  const { sesion, recargar } = useSesion();
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setError(null);
    setEnviando(true);
    try {
      await exigir(
        api.POST("/sesion/contrasena", {
          body: { contrasena_actual: actual, contrasena_nueva: nueva },
        }),
      );
      const renovada = await recargar();
      await navegar(renovada ? inicioDe(renovada) : "/entrar", { replace: true });
    } catch (fallo) {
      setError(fallo);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Marco titulo="Cambiar la contraseña">
      {sesion?.debe_cambiar_contrasena ? (
        <AvisoInformativo>
          <p>Antes de continuar, reemplace la contraseña inicial por una propia.</p>
        </AvisoInformativo>
      ) : null}
      <Form
        className="formulario"
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
      >
        <CampoTexto
          etiqueta="Contraseña actual"
          name="actual"
          type="password"
          value={actual}
          onChange={setActual}
          isRequired
          autoComplete="current-password"
        />
        <CampoTexto
          etiqueta="Contraseña nueva"
          name="nueva"
          type="password"
          value={nueva}
          onChange={setNueva}
          isRequired
          autoComplete="new-password"
        />
        <CampoTexto
          etiqueta="Repita la contraseña nueva"
          name="repetida"
          type="password"
          value={repetida}
          onChange={setRepetida}
          isRequired
          autoComplete="new-password"
          validate={(valor) =>
            valor === nueva ? null : "Las dos contraseñas nuevas no coinciden."
          }
        />
        <AvisoError error={error} />
        <Boton type="submit" isDisabled={enviando}>
          {enviando ? "Guardando…" : "Cambiar la contraseña"}
        </Boton>
      </Form>
    </Marco>
  );
}

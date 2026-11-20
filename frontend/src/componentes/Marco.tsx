// Estructura común de las páginas: enlace para saltar al contenido, encabezado con la
// cuenta y el cierre de sesión, y una región principal con su título (RNF-18).
import { useEffect, useRef, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { useSesion } from "../sesion/sesion";
import { Boton } from "./controles";

export function Marco({ titulo, children }: { titulo: string; children: ReactNode }) {
  const { sesion, salir } = useSesion();
  const navegar = useNavigate();
  const encabezado = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = `${titulo} | Asistencia para artículos científicos`;
    encabezado.current?.focus(); // al cambiar de página, el lector de pantalla la anuncia
  }, [titulo]);

  return (
    <>
      <a className="saltar" href="#contenido">
        Saltar al contenido
      </a>
      <header className="cabecera">
        <p className="cabecera__nombre">Asistencia para artículos científicos</p>
        {sesion ? (
          <div className="cabecera__cuenta">
            <span>Cuenta: {sesion.cuenta}</span>
            <Boton
              variante="secundario"
              onPress={() => {
                void salir().then(() => {
                  void navegar("/entrar", { replace: true });
                });
              }}
            >
              Cerrar sesión
            </Boton>
          </div>
        ) : null}
      </header>
      <main id="contenido" className="contenido">
        <h1 ref={encabezado} tabIndex={-1}>
          {titulo}
        </h1>
        {children}
      </main>
    </>
  );
}

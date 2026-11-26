// Estructura común de las páginas: enlace para saltar al contenido, encabezado con el nombre del
// sistema, la cuenta y el cierre de sesión, y una región principal con su título (RNF-18).
// La variante "acceso" (inicio de sesión) centra el contenido en una tarjeta con la
// presentación del sistema.
import { useEffect, useRef, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { useSesion } from "../sesion/sesion";
import { Boton } from "./controles";
import { Logo } from "./Logo";

export const NOMBRE_SISTEMA = "Asistencia para artículos científicos";

export function Marco({
  titulo,
  children,
  variante = "normal",
}: {
  titulo: string;
  children: ReactNode;
  variante?: "normal" | "acceso";
}) {
  const { sesion, salir } = useSesion();
  const navegar = useNavigate();
  const encabezado = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = `${titulo} | ${NOMBRE_SISTEMA}`;
    encabezado.current?.focus(); // al cambiar de página, el lector de pantalla la anuncia
  }, [titulo]);

  const titular = (
    <h1 ref={encabezado} tabIndex={-1}>
      {titulo}
    </h1>
  );

  return (
    <>
      <a className="saltar" href="#contenido">
        Saltar al contenido
      </a>
      <header className="cabecera">
        <p className="cabecera__nombre">
          <Logo tamano={28} />
          <span>{NOMBRE_SISTEMA}</span>
        </p>
        {sesion ? (
          <div className="cabecera__cuenta">
            <span className="cabecera__codigo">Cuenta: {sesion.cuenta}</span>
            <Boton
              variante="claro"
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
      {variante === "acceso" ? (
        <main id="contenido" className="contenido contenido--acceso">
          <div className="acceso">
            <div className="acceso__presentacion">
              <Logo tamano={56} />
              <p className="acceso__nombre">{NOMBRE_SISTEMA}</p>
              <p className="acceso__descripcion">
                Asistente para estudiantes que redactan artículos científicos empíricos: busca
                evidencia en las fuentes de su tema y verifica sus referencias, sin escribir por
                usted.
              </p>
            </div>
            <div className="tarjeta acceso__tarjeta">
              {titular}
              {children}
            </div>
          </div>
        </main>
      ) : (
        <main id="contenido" className="contenido">
          {titular}
          {children}
        </main>
      )}
    </>
  );
}

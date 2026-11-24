// Rutas de la interfaz, protegidas por rol (T13, tareas técnicas). La API también
// autoriza cada petición: esta protección solo evita mostrar pantallas que no corresponden.
import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";

import { Marco } from "./componentes/Marco";
import { CambiarContrasena } from "./paginas/CambiarContrasena";
import { Entrar } from "./paginas/Entrar";
import { Evidencia } from "./paginas/Evidencia";
import { ImportacionReferencias } from "./paginas/Importacion";
import { Investigador } from "./paginas/Investigador";
import { PanelCaso } from "./paginas/PanelCaso";
import { inicioDe, ROL_CASO, ROL_INVESTIGADOR, useSesion, type Rol } from "./sesion/sesion";

function Cargando() {
  return (
    <main className="contenido">
      <p role="status">Cargando…</p>
    </main>
  );
}

function Protegida({ rol, children }: { rol?: Rol; children: ReactNode }) {
  const { sesion, cargando } = useSesion();
  const ubicacion = useLocation();
  if (cargando) return <Cargando />;
  if (sesion === null) return <Navigate to="/entrar" replace state={{ desde: ubicacion }} />;
  if (rol === undefined) return children; // cambio de contraseña: cualquier sesión
  if (sesion.debe_cambiar_contrasena) return <Navigate to="/contrasena" replace />;
  if (sesion.rol !== rol) return <Navigate to={inicioDe(sesion)} replace />;
  return children;
}

function Inicio() {
  const { sesion, cargando } = useSesion();
  if (cargando) return <Cargando />;
  return <Navigate to={sesion ? inicioDe(sesion) : "/entrar"} replace />;
}

function SoloSinSesion({ children }: { children: ReactNode }) {
  const { sesion, cargando } = useSesion();
  if (cargando) return <Cargando />;
  return sesion ? <Navigate to={inicioDe(sesion)} replace /> : children;
}

function NoEncontrada() {
  return (
    <Marco titulo="Página no encontrada">
      <p>
        La dirección no existe. <a href="/">Volver al inicio</a>.
      </p>
    </Marco>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route
        path="/entrar"
        element={
          <SoloSinSesion>
            <Entrar />
          </SoloSinSesion>
        }
      />
      <Route
        path="/contrasena"
        element={
          <Protegida>
            <CambiarContrasena />
          </Protegida>
        }
      />
      <Route
        path="/panel"
        element={
          <Protegida rol={ROL_CASO}>
            <PanelCaso />
          </Protegida>
        }
      />
      <Route
        path="/panel/evidencia"
        element={
          <Protegida rol={ROL_CASO}>
            <Evidencia />
          </Protegida>
        }
      />
      <Route
        path="/investigador"
        element={
          <Protegida rol={ROL_INVESTIGADOR}>
            <Investigador />
          </Protegida>
        }
      />
      <Route
        path="/investigador/importacion"
        element={
          <Protegida rol={ROL_INVESTIGADOR}>
            <ImportacionReferencias />
          </Protegida>
        }
      />
      <Route path="*" element={<NoEncontrada />} />
    </Routes>
  );
}

// Estado de la sesión (RF-18): se consulta GET /sesion al abrir la aplicación y después de
// iniciar o cerrar sesión. Las rutas protegidas leen el rol de aquí.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api, ErrorApi, exigir, type Esquemas } from "../api/cliente";

export type EstadoSesion = Esquemas["EstadoSesion"];
export type Rol = Esquemas["Rol"];
export const ROL_CASO: Rol = "A1";
export const ROL_INVESTIGADOR: Rol = "A2";

interface ValorSesion {
  sesion: EstadoSesion | null;
  cargando: boolean;
  entrar: (codigo: string, contrasena: string) => Promise<EstadoSesion>;
  salir: () => Promise<void>;
  recargar: () => Promise<EstadoSesion | null>;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

async function consultar(): Promise<EstadoSesion | null> {
  try {
    return await exigir(api.GET("/sesion"));
  } catch (error) {
    if (error instanceof ErrorApi && error.estado === 401) return null;
    throw error;
  }
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<EstadoSesion | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    const actual = await consultar().catch(() => null);
    setSesion(actual);
    return actual;
  }, []);

  useEffect(() => {
    let vigente = true;
    void consultar()
      .catch(() => null)
      .then((actual) => {
        if (!vigente) return;
        setSesion(actual);
        setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, []);

  const entrar = useCallback(async (codigo: string, contrasena: string) => {
    const nueva = await exigir(api.POST("/sesion", { body: { codigo, contrasena } }));
    setSesion(nueva);
    return nueva;
  }, []);

  const salir = useCallback(async () => {
    await exigir(api.DELETE("/sesion")).catch(() => undefined);
    setSesion(null);
  }, []);

  const valor = useMemo(
    () => ({ sesion, cargando, entrar, salir, recargar }),
    [sesion, cargando, entrar, salir, recargar],
  );
  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (valor === null) throw new Error("useSesion fuera de ProveedorSesion");
  return valor;
}

/** Página de inicio según el rol de la sesión. */
export function inicioDe(sesion: EstadoSesion): string {
  if (sesion.debe_cambiar_contrasena) return "/contrasena";
  return sesion.rol === ROL_INVESTIGADOR ? "/investigador" : "/panel";
}

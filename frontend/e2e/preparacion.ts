// Cuenta de investigador para las pruebas de extremo a extremo, en una base de pruebas.
//
// * Si existen E2E_INVESTIGADOR y E2E_CONTRASENA_INVESTIGADOR, se usan (scripts/e2e.ps1
//   los crea en un proyecto de Compose aislado y los pasa en un archivo temporal).
// * Si no, se ejecuta E2E_CREAR_INVESTIGADOR (por ejemplo, "python -m
//   app.seguridad.crear_investigador" en E2E_DIRECTORIO_BACKEND), como en la CI.
//
// La contraseña inicial solo queda en memoria: nunca se imprime ni se escribe en disco.
import { execSync } from "node:child_process";

const PATRON = /Contraseña inicial \(se muestra una sola vez\): (\S+)/;

export default function preparar(): void {
  if (process.env.E2E_INVESTIGADOR && process.env.E2E_CONTRASENA_INVESTIGADOR) return;
  const comando = process.env.E2E_CREAR_INVESTIGADOR;
  if (!comando) {
    throw new Error(
      "Falta la cuenta de investigador: defina E2E_INVESTIGADOR y E2E_CONTRASENA_INVESTIGADOR" +
        " o E2E_CREAR_INVESTIGADOR (ver e2e/preparacion.ts).",
    );
  }
  const codigo = `INV-E2E-${Date.now().toString(36).toUpperCase()}`;
  const salida = execSync(`${comando} ${codigo}`, {
    cwd: process.env.E2E_DIRECTORIO_BACKEND ?? process.cwd(),
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  const contrasena = PATRON.exec(salida)?.[1];
  if (!contrasena) throw new Error("El comando no informó la contraseña inicial.");
  process.env.E2E_INVESTIGADOR = codigo;
  process.env.E2E_CONTRASENA_INVESTIGADOR = contrasena;
}

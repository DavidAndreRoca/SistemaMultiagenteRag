import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, type TestInfo } from "@playwright/test";

export const CONTRASENA_NUEVA = "Contrasena-de-prueba-E2E-2026";
export const BORRADOR_VALIDO = "../backend/pruebas/datos/docx/valido.docx";

export function sufijo(): string {
  return Date.now().toString(36).toUpperCase().slice(-6);
}

/** Inicia sesión desde la pantalla de ingreso. */
export async function entrar(pagina: Page, codigo: string, contrasena: string): Promise<void> {
  await pagina.goto("/entrar");
  await pagina.getByLabel("Código de cuenta").fill(codigo);
  await pagina.getByLabel("Contraseña", { exact: true }).fill(contrasena);
  await pagina.getByRole("button", { name: "Ingresar" }).click();
}

/** Reemplaza la contraseña inicial, como exige el primer ingreso (RF-18). */
export async function cambiarContrasena(pagina: Page, actual: string): Promise<void> {
  await expect(pagina.getByRole("heading", { name: "Cambiar la contraseña" })).toBeVisible();
  await pagina.getByLabel("Contraseña actual").fill(actual);
  await pagina.getByLabel("Contraseña nueva", { exact: true }).fill(CONTRASENA_NUEVA);
  await pagina.getByLabel("Repita la contraseña nueva").fill(CONTRASENA_NUEVA);
  await pagina.getByRole("button", { name: "Cambiar la contraseña" }).click();
}

export async function salir(pagina: Page): Promise<void> {
  await pagina.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(pagina.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
}

/**
 * Revisión automática de accesibilidad (WCAG 2.2 A y AA): no admite infracciones graves ni
 * críticas y deja anotadas las demás para la revisión manual.
 */
export async function revisarAccesibilidad(
  pagina: Page,
  pantalla: string,
  info: TestInfo,
): Promise<void> {
  const resultado = await new AxeBuilder({ page: pagina })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const graves = resultado.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  for (const leve of resultado.violations.filter((v) => !graves.includes(v))) {
    info.annotations.push({ type: `accesibilidad (${pantalla})`, description: leve.id });
  }
  expect(
    graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
    `Infracciones graves de accesibilidad en ${pantalla}`,
  ).toEqual([]);
}

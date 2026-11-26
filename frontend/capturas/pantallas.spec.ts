// Capturas de las pantallas del prototipo con los datos de demostración. Variables:
// CAP_DESTINO (carpeta), CAP_CASO y CAP_CLAVE_CASO, CAP_INVESTIGADOR y CAP_CLAVE_INVESTIGADOR,
// CAP_EVIDENCIA y CAP_REFERENCIAS (solicitudes ya entregadas). Las contraseñas llegan por un
// archivo temporal y no se imprimen.
import { expect, test, type Page } from "@playwright/test";

function variable(nombre: string): string {
  const valor = process.env[nombre];
  if (!valor) throw new Error(`Falta ${nombre}`);
  return valor;
}

const destino = (nombre: string) => `${variable("CAP_DESTINO")}/${nombre}.png`;

async function entrar(pagina: Page, codigo: string, contrasena: string): Promise<void> {
  await pagina.goto("/entrar");
  await pagina.getByLabel("Código de cuenta").fill(codigo);
  await pagina.getByLabel("Contraseña", { exact: true }).fill(contrasena);
  await pagina.getByRole("button", { name: "Ingresar" }).click();
}

test("pantallas del caso", async ({ page }) => {
  await page.goto("/entrar");
  await expect(page.getByLabel("Código de cuenta")).toBeVisible();
  await page.screenshot({ path: destino("01-inicio-de-sesion"), fullPage: true });

  await entrar(page, variable("CAP_CASO"), variable("CAP_CLAVE_CASO"));
  await expect(page.getByText("DEMO-01", { exact: true })).toBeVisible();
  await page.screenshot({ path: destino("02-panel-del-caso"), fullPage: true });

  await page.goto(`/panel/evidencia?solicitud=${variable("CAP_EVIDENCIA")}`);
  await expect(page.getByText("Fuentes recomendadas")).toBeVisible({ timeout: 15_000 });
  await page.locator("details.cita").first().locator("summary").click();
  await page.screenshot({ path: destino("03-evidencia"), fullPage: true });

  await page.goto(`/panel/referencias?solicitud=${variable("CAP_REFERENCIAS")}`);
  await expect(page.getByText("Referencias de la lista")).toBeVisible({ timeout: 15_000 });
  await page.screenshot({ path: destino("04-referencias"), fullPage: true });
});

test("pantalla del investigador", async ({ page }) => {
  await entrar(page, variable("CAP_INVESTIGADOR"), variable("CAP_CLAVE_INVESTIGADOR"));
  await expect(page.getByRole("heading", { name: "Casos y colecciones" })).toBeVisible();
  await page.screenshot({ path: destino("05-investigador"), fullPage: true });
});

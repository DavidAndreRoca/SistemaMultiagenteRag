// Criterios de aceptación de T13:
// * Playwright recorre inicio de sesión, carga y versión visible.
// * La revisión automática no encuentra errores de accesibilidad graves en estas pantallas.
// * Un caso no ve datos de otro desde la interfaz.
// T15: la pantalla de importación de referencias es accesible. La importación y la subida de
// pendientes se prueban con pruebas unitarias y de integración, porque la CI no tiene GROBID.
import { expect, test, type Page } from "@playwright/test";

import {
  BORRADOR_VALIDO,
  cambiarContrasena,
  CONTRASENA_NUEVA,
  entrar,
  revisarAccesibilidad,
  salir,
  sufijo,
} from "./ayudas";

test.describe.configure({ mode: "serial" });

interface Credencial {
  cuenta: string;
  contrasena: string;
}

const marca = sufijo();
const TEMA = `TEMA-E2E-${marca}`;
const CASO_A = `CASO-E2E-A${marca}`;
const CASO_B = `CASO-E2E-B${marca}`;
const credenciales = new Map<string, Credencial>();

function investigador(): Credencial {
  const cuenta = process.env.E2E_INVESTIGADOR;
  const contrasena = process.env.E2E_CONTRASENA_INVESTIGADOR;
  if (!cuenta || !contrasena) throw new Error("Falta la cuenta de investigador (preparacion.ts)");
  return { cuenta, contrasena };
}

async function elegir(pagina: Page, etiqueta: string, opcion: string): Promise<void> {
  await pagina.getByRole("button", { name: new RegExp(etiqueta) }).click();
  await pagina.getByRole("option", { name: opcion }).click();
}

async function registrarCaso(pagina: Page, codigo: string): Promise<Credencial> {
  await pagina.getByLabel("Código del caso").fill(codigo);
  await elegir(pagina, "Tipo de autoría", "Individual");
  await elegir(pagina, "Tema", TEMA);
  await pagina.getByRole("button", { name: "Registrar el caso" }).click();
  const aviso = pagina.locator(".aviso--importante");
  await expect(aviso).toContainText(`Caso ${codigo} registrado`);
  const cuenta = (await aviso.locator("li strong").first().textContent()) ?? "";
  const contrasena = (await aviso.locator("li code").first().textContent()) ?? "";
  expect(cuenta).not.toBe("");
  expect(contrasena.length).toBeGreaterThanOrEqual(12);
  return { cuenta, contrasena };
}

test("el investigador ingresa, crea un tema y registra dos casos", async ({ page }, info) => {
  const { cuenta, contrasena } = investigador();
  await entrar(page, cuenta, contrasena);
  await cambiarContrasena(page, contrasena);
  await expect(page.getByRole("heading", { name: "Casos y colecciones" })).toBeVisible();

  await page.getByLabel("Código del tema").fill(TEMA);
  await page.getByRole("button", { name: "Crear el tema" }).click();
  await expect(page.getByRole("status").filter({ hasText: `Tema ${TEMA} creado` })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: TEMA })).toBeVisible();

  credenciales.set(CASO_A, await registrarCaso(page, CASO_A));
  credenciales.set(CASO_B, await registrarCaso(page, CASO_B));
  await expect(page.getByRole("rowheader", { name: CASO_A })).toBeVisible();
  await revisarAccesibilidad(page, "casos y colecciones", info);
  await salir(page);
});

test("el investigador abre la importación de referencias de un tema (T15)", async ({
  page,
}, info) => {
  const { cuenta } = investigador();
  await entrar(page, cuenta, CONTRASENA_NUEVA);
  await expect(page.getByRole("heading", { name: "Casos y colecciones" })).toBeVisible();
  await page.getByRole("link", { name: "Importar las referencias del artículo O1" }).click();
  await expect(
    page.getByRole("heading", { name: "Importar referencias del artículo O1" }),
  ).toBeVisible();
  await elegir(page, "Tema", TEMA);
  await expect(page.getByText("Este tema todavía no tiene referencias importadas.")).toBeVisible();
  await expect(page.getByText("No hay referencias pendientes de PDF.")).toBeVisible();
  await expect(page.getByLabel("O pegue la lista de DOI")).toBeVisible();
  await revisarAccesibilidad(page, "importación de referencias", info);
  await salir(page);
});

test("la pantalla de inicio de sesión es accesible y usable con teclado", async ({
  page,
}, info) => {
  await page.goto("/entrar");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await revisarAccesibilidad(page, "inicio de sesión", info);
  // Al abrir la página, el foco va a su título (el lector de pantalla la anuncia); desde ahí,
  // el tabulador recorre el formulario en orden.
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Código de cuenta")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Contraseña", { exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Ingresar" })).toBeFocused();
  // Hacia atrás, antes del título está el enlace para saltar al contenido.
  for (let i = 0; i < 2; i++) await page.keyboard.press("Shift+Tab");
  await expect(page.getByLabel("Código de cuenta")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  const saltar = page.getByRole("link", { name: "Saltar al contenido" });
  await expect(saltar).toBeFocused();
  await expect(saltar).toBeVisible(); // visible al recibir el foco
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#contenido$/);
});

test("un caso ingresa, carga su borrador y ve la versión", async ({ page }, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, caso.contrasena);
  await cambiarContrasena(page, caso.contrasena);
  await expect(page.getByRole("heading", { name: "Panel del caso" })).toBeVisible();
  await expect(page.getByText(/Aún no ha cargado ninguna versión/)).toBeVisible();
  await revisarAccesibilidad(page, "panel del caso sin versiones", info);

  await elegir(page, "Hito", "Avance 1: Planteamiento");
  const [selector] = await Promise.all([
    page.waitForEvent("filechooser"),
    page.getByRole("button", { name: "Elegir el archivo .docx" }).click(),
  ]);
  await selector.setFiles(BORRADOR_VALIDO);
  await expect(page.getByText("Archivo elegido: valido.docx")).toBeVisible();
  await page.getByRole("button", { name: "Cargar la versión" }).click();

  await expect(page.getByText("Es la primera versión del hito Avance 1.")).toBeVisible();
  const versiones = page.getByRole("table", { name: /Versiones cargadas/ });
  await expect(versiones.getByRole("row")).toHaveCount(2); // encabezado y la versión
  await expect(versiones.getByRole("row").nth(1)).toContainText("Vigente");
  const vigentes = page.getByRole("table", { name: /Versión vigente de cada hito/ });
  await expect(vigentes.getByRole("row", { name: /Avance 1/ })).toContainText("Cargada el");
  await revisarAccesibilidad(page, "panel del caso con una versión", info);

  // Un archivo no admitido se rechaza con su motivo y no crea versión (CP-02 desde la interfaz).
  const [otro] = await Promise.all([
    page.waitForEvent("filechooser"),
    page.getByRole("button", { name: "Elegir el archivo .docx" }).click(),
  ]);
  await otro.setFiles({
    name: "borrador.docx",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  await page.getByRole("button", { name: "Cargar la versión" }).click();
  await expect(page.getByRole("alert")).toContainText("no es un documento de Word");
  await expect(versiones.getByRole("row")).toHaveCount(2);
  await salir(page);
});

test("un caso abre la búsqueda de evidencia (T19)", async ({ page }, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await expect(page.getByRole("heading", { name: "Panel del caso" })).toBeVisible();
  await page.getByRole("link", { name: "Buscar evidencia en las fuentes de su tema" }).click();
  await expect(page.getByRole("heading", { name: "Buscar evidencia" })).toBeVisible();
  await expect(page.getByLabel("Consulta o afirmación")).toBeVisible();
  await revisarAccesibilidad(page, "búsqueda de evidencia", info);
  await salir(page);
});

test("un caso abre la verificación de referencias (T20)", async ({ page }, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await expect(page.getByRole("heading", { name: "Panel del caso" })).toBeVisible();
  await page.getByRole("link", { name: "Verificar las referencias de su borrador" }).click();
  await expect(page.getByRole("heading", { name: "Verificar referencias" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Verificar las referencias" })).toBeEnabled();
  await revisarAccesibilidad(page, "verificación de referencias", info);
  await salir(page);
});

test("un caso abre la revisión de estructura con las secciones de su versión (T23)", async ({
  page,
}, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await page.getByRole("link", { name: "Revisar la estructura de una sección" }).click();
  await expect(
    page.getByRole("heading", { name: "Revisar estructura y coherencia" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Revisar la sección" })).toBeVisible();
  await revisarAccesibilidad(page, "estructura y coherencia", info);
  await salir(page);
});

test("un caso abre la propuesta de redacción con los párrafos de su versión (T27)", async ({
  page,
}, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await page.getByRole("link", { name: "Proponer una redacción para un párrafo" }).click();
  await expect(page.getByRole("heading", { name: "Proponer una redacción" })).toBeVisible();
  // El botón se habilita cuando llegaron los párrafos: antes, la lista estaría vacía.
  await expect(page.getByRole("button", { name: "Proponer una redacción" })).toBeEnabled();
  await page.getByRole("button", { name: /Párrafo/ }).click();
  await page.getByRole("option").first().click();
  await expect(page.getByText(/Párrafo elegido/)).toBeVisible();
  await revisarAccesibilidad(page, "propuesta de redacción", info);
  await salir(page);
});

test("un caso abre la revisión metodológica con la sección de método elegida (T26)", async ({
  page,
}, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await page.getByRole("link", { name: "Revisar la metodología de una sección" }).click();
  await expect(page.getByRole("heading", { name: "Revisar la metodología" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Revisar la metodología" })).toBeEnabled();
  await revisarAccesibilidad(page, "revisión metodológica", info);
  await salir(page);
});

test("un caso abre el plan de tarea con el hito de su versión (T24)", async ({ page }, info) => {
  const caso = credenciales.get(CASO_A);
  if (!caso) throw new Error("El caso A no se registró");
  await entrar(page, caso.cuenta, CONTRASENA_NUEVA);
  await page.getByRole("link", { name: "Preparar el plan de tarea del hito" }).click();
  await expect(page.getByRole("heading", { name: "Plan de tarea del hito" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Avance 1: Planteamiento/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Preparar el plan" })).toBeEnabled();
  await revisarAccesibilidad(page, "plan de tarea", info);
  await salir(page);
});

test("un caso no ve las versiones de otro", async ({ page }) => {
  const caso = credenciales.get(CASO_B);
  if (!caso) throw new Error("El caso B no se registró");
  await entrar(page, caso.cuenta, caso.contrasena);
  await cambiarContrasena(page, caso.contrasena);
  await expect(page.getByRole("heading", { name: "Panel del caso" })).toBeVisible();
  await expect(page.getByText(CASO_B, { exact: true })).toBeVisible();
  await expect(page.getByText(/Aún no ha cargado ninguna versión/)).toBeVisible();
  await expect(page.getByText("Todavía no hay versiones.")).toBeVisible();
  await expect(page.getByText(CASO_A)).toHaveCount(0);
  // Tampoco puede abrir la pantalla del investigador: vuelve a su panel.
  await page.goto("/investigador");
  await expect(page.getByRole("heading", { name: "Panel del caso" })).toBeVisible();
  await salir(page);
});

// Capturas de las pantallas del prototipo (cambio visual del 26-11-2026). No es parte de las
// pruebas: se ejecuta a mano contra el prototipo con datos (ver capturas/pantallas.spec.ts).
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./capturas",
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    locale: "es-PE",
    viewport: { width: 1280, height: 860 },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 860 } },
    },
  ],
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 180_000,
  },
});

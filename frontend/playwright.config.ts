// Pruebas de extremo a extremo (T13): la interfaz compilada (vite preview) frente a la API
// real con su base. La API se indica con URL_API; la cuenta de investigador, con las
// variables que describe e2e/preparacion.ts.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/preparacion.ts",
  fullyParallel: false, // un solo flujo con una base compartida
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    locale: "es-PE",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});

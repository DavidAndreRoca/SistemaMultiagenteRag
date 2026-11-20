/// <reference types="vitest/config" />
// Interfaz y API bajo un mismo origen (T13, actividad 6): el navegador pide /api/... y
// Vite lo reenvía a la API sin el prefijo. Así la cookie de sesión (Secure, SameSite=Lax)
// funciona sin CORS, igual que detrás de Caddy en producción.
import react from "@vitejs/plugin-react";
import { defineConfig, type ProxyOptions } from "vite";

const URL_API = process.env.URL_API ?? "http://127.0.0.1:8000";

const proxy: Record<string, ProxyOptions> = {
  "/api": {
    target: URL_API,
    changeOrigin: false,
    rewrite: (ruta) => ruta.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true, proxy },
  build: { sourcemap: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/pruebas/configuracion.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});

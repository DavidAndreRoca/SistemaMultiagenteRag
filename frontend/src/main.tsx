import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { I18nProvider } from "react-aria-components";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { ProveedorSesion } from "./sesion/sesion";
import "./estilos.css";

const raiz = document.getElementById("raiz");
if (raiz === null) throw new Error("Falta el elemento #raiz");

createRoot(raiz).render(
  <StrictMode>
    <I18nProvider locale="es-PE">
      <BrowserRouter>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </BrowserRouter>
    </I18nProvider>
  </StrictMode>,
);

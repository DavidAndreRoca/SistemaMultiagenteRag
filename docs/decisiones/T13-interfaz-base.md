# T13-01. Interfaz base

**Fase:** T13 (Fase 3). **Fecha:** 19 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T13 (RF-18, RF-01, parte de RF-19, RNF-17 y RNF-18) y línea base D-01 (React, TypeScript, Vite y una biblioteca de componentes accesible "que se elige en T13"). La biblioteca la eligió el equipo el 19 de noviembre de 2026 (apartado 2).

## 1. Pila y versiones

Todas fijadas con versión exacta en `frontend/package.json` y el árbol completo en `package-lock.json`. Cada versión se publicó al menos dos semanas antes de elegirla.

| Pieza | Versión | Licencia | Para qué |
| --- | --- | --- | --- |
| Node | 24.22.2 (LTS) | MIT | Herramientas del frontend, aquí (contenedor) y en la CI |
| React y React DOM | 19.3.1 | MIT | Interfaz |
| React Aria Components | 1.22.1 | Apache 2.0 | Controles accesibles (apartado 2) |
| React Router | 8.5.1 | MIT | Rutas |
| Vite y su complemento de React | 8.3.6 y 6.2.1 | MIT | Compilación y servidor de desarrollo |
| TypeScript | 5.9.3 | Apache 2.0 | Tipos en modo estricto |
| openapi-typescript y openapi-fetch | 7.13.0 y 0.17.0 | MIT | Cliente tipado generado del contrato |
| ESLint, typescript-eslint, jsx-a11y y react-hooks | 9.39.5, 8.72.1, 6.10.2 y 7.1.1 | MIT | Análisis, con reglas de accesibilidad |
| Prettier | 3.9.10 | MIT | Formato |
| Vitest, Testing Library y jsdom | 5.1.0, 16.3.3 y 31.0.0 | MIT | Pruebas unitarias |
| Playwright y axe-core para Playwright | 1.65.0 y 4.14.0 | Apache 2.0 y MPL 2.0 | Extremo a extremo y revisión automática de accesibilidad |

**Decisiones de versión:**
- **TypeScript 5.9 y no 7:** openapi-typescript exige TypeScript 5, y typescript-eslint, menos de 6.1.
- **ESLint 9 y no 10:** eslint-plugin-jsx-a11y solo admite hasta la 9.
- **Node 24 y no 22:** jsdom y React Router piden Node 22.22.2 o más, y este equipo tiene 22.13.1. En vez de bajar versiones o cambiar la instalación del equipo, las herramientas del frontend corren en el contenedor `node:24.22.2-bookworm-slim`.
- **npm 11 (el de Node 24):** npm 10 falla con un error interno al resolver los pares opcionales de Vitest.
- **`overrides` de `playwright-core` a 1.65.0:** sin él, axe-core para Playwright traía otra copia (1.65.1, más reciente que el mínimo de dos semanas) con tipos incompatibles.

## 2. Biblioteca de componentes: React Aria Components

**Criterio (hoja de ruta):** WCAG 2.2 AA, uso completo con teclado y foco visible. Opciones consideradas:

| Opción | A favor | En contra |
| --- | --- | --- |
| **React Aria Components (elegida)** | Comportamiento accesible probado por Adobe en cada control: teclado, foco, lectores de pantalla y anuncios de validación. Textos en español (`I18nProvider`). Sin estilos impuestos | Los estilos se escriben a mano |
| Radix UI con shadcn/ui | Componentes ya estilados | Algunas piezas exigen cuidar la accesibilidad a mano; agrega Tailwind |
| MUI | La más rápida para tener pantallas | Más pesada y difícil de adaptar a un estilo propio |

Los controles comunes están en `src/componentes/controles.tsx` (`CampoTexto`, `Selector`, `SelectorArchivo`, `Boton` y avisos).

**Estilos (`src/estilos.css`):**
- texto con contraste de al menos 4,5:1 y bordes de controles de al menos 3:1;
- foco visible de 3 px en un color de contraste;
- objetivos de 40 px de alto;
- enlace para saltar al contenido, y el título de cada página recibe el foco al navegar;
- se respeta `prefers-reduced-motion`.

## 3. Cliente de la API, generado del contrato

- `python -m app.contrato` escribe `docs/api/openapi.json`. Una prueba de arquitectura del backend falla si no coincide con la aplicación.
- `npm run generar:api` genera `src/api/esquema.d.ts`. La CI lo regenera y falla si cambia.
- Así el cliente nunca se escribe a mano (hoja de ruta, 4.2) y no puede desfasarse de la API.
- **Mismo contrato con Python 3.12 y 3.13:** FastAPI nombra cada respuesta con el estado de `http.HTTPStatus`, que cambió en 3.13. El generador fija los nombres de la RFC 9110 (413 y 422). Si una versión nueva de FastAPI cambia el contrato, la prueba lo detecta y basta con regenerarlo.
- `src/api/cliente.ts`:
  - agrega la cabecera `X-CSRF-Token`, tomada de la cookie `sma_csrf`, a toda petición que cambia datos;
  - convierte toda respuesta de error en un `ErrorApi`, con el mensaje y el identificador de incidencia del formato común (4.4). Una respuesta que no tiene ese formato, o un fallo de red, da un mensaje genérico, sin mostrar el cuerpo.
- **Cambio en la API para la interfaz:** `GET /caso` incluye el catálogo de hitos de la configuración vigente, porque el formulario de carga necesita ofrecerlos y ninguna ruta del caso los daba.

## 4. Mismo dominio que la API

- La interfaz llama a `/api/...`, y Vite (en desarrollo y en `vite preview`) lo reenvía a la API sin el prefijo. En producción lo hará Caddy de la misma forma (T21).
- Con un solo origen, la cookie de sesión (`Secure`, `SameSite=Lax`, `HttpOnly`) funciona sin CORS. Los navegadores aceptan cookies `Secure` en `http://localhost` y `http://127.0.0.1`.
- El prefijo evita que una ruta de la interfaz (por ejemplo, `/panel`) choque con una de la API.
- **En desarrollo:** `docker compose --profile interfaz up -d interfaz` sirve la interfaz en `http://127.0.0.1:5173` frente a la API de Compose.

## 5. Pantallas y rutas

| Ruta | Rol | Contenido |
| --- | --- | --- |
| `/entrar` | sin sesión | Código de cuenta y contraseña |
| `/contrasena` | cualquier sesión | Cambio de la contraseña inicial, obligatorio antes de seguir (RF-18) |
| `/panel` | caso (A1) | Datos del caso, versión vigente por hito, invitación a cargar la primera versión, carga (hito y .docx) con los mensajes de la API, y lista de versiones |
| `/investigador` | investigador (A2) | Casos y temas con sus contadores; crear un tema y registrar un caso. Las credenciales iniciales se muestran una sola vez |

- Las rutas se protegen por rol en la interfaz.
- La API autoriza igual cada petición: la protección de la interfaz solo evita mostrar pantallas que no corresponden.
- Las secciones del borrador y la formulación de solicitudes son de T29.

## 6. Pruebas

- **Unitarias (Vitest):** cliente (CSRF, errores, fallo de red), rutas protegidas y el inicio de sesión con su error.
- **Extremo a extremo (Playwright, `e2e/flujo.spec.ts`):** frente a la API y la base reales:
  1. el investigador ingresa, cambia su contraseña, crea un tema y registra dos casos;
  2. el caso A ingresa, cambia su contraseña, carga `valido.docx` y ve su versión vigente; luego un archivo que no es .docx se rechaza con su motivo, sin crear versión;
  3. el caso B no ve nada del caso A ni la pantalla del investigador;
  4. el inicio de sesión se recorre con el tabulador en orden.
- **Accesibilidad automática:** axe-core con las reglas de WCAG 2.2 A y AA en cada pantalla. Falla con cualquier infracción grave o crítica; las menores quedan anotadas para la revisión manual.
- **Cómo se ejecutan:**
  - **En local:** `scripts/e2e.ps1`, en un proyecto de Compose aislado (`sma_e2e`) que se borra al terminar.
  - **En la CI:** con PostgreSQL de servicio y la API instalada en el ejecutor.
- **Contraseña del investigador de prueba:** se lee de la salida del comando y queda en memoria (en local, en un archivo temporal que se borra). Nunca se imprime.

## 7. Pendientes y riesgos

- **Prueba manual con teclado y lector de pantalla:** la hoja de ruta la pide. Queda para el equipo, con NVDA en Windows y en estas pantallas.
- **Herramientas en contenedor:** `node_modules` se instala para Linux. Quien quiera trabajar el frontend fuera del contenedor necesita Node 24.22.2 y volver a ejecutar `npm ci`.
- **Tamaño del paquete:** 146 KB comprimido, sobre todo React Aria y React Router. Se revisará si crece con las pantallas de T29.

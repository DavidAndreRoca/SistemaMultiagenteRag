# T17-01. Adaptador de modelos de lenguaje e instrucciones versionadas

**Fase:** T17 (Fase 3; en el orden de ejecución va antes que T16). **Fecha:** 22 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T17 y riesgo R-01. Especificación de la Fase 1:
- RNF-10: al proveedor solo van solicitud, alcance y fragmentos;
- RNF-16: claves solo en el entorno;
- RNF-20: proveedor detrás de una interfaz;
- RNF-21: cada solicitud registra las versiones de configuración, instrucciones y modelo;
- RN-23: el contenido se trata como datos;
- RN-24: identificadores de modelo fijos;
- D-06 (modelos de desarrollo) y D-10 (proveedor de producción, en T25).

Decisiones del equipo del 22 de noviembre de 2026: apartados 2 y 3.

## 1. Interfaz

```python
class ModeloLenguaje(Protocol):
    async def generar(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[T]
    ) -> ResultadoEstructurado[T]: ...
```

- **`Instruccion`:** agente, versión, huella y texto. La entrega el cargador (apartado 6).
- **`EntradaModelo`:** la tarea (lo que se pide) y bloques de datos con etiqueta: la sección del alcance o los fragmentos `F1` a `Fn`. Solo admite texto, con un tamaño máximo por bloque. No hay forma de pasarle un archivo ni el borrador completo (RNF-10).
- **`ResultadoEstructurado[T]`:**
  - los datos ya validados con el modelo Pydantic `T`;
  - el proveedor y el modelo efectivamente usados, y la versión que el proveedor informó;
  - los tokens, la duración y el costo estimado;
  - los intentos y si se usó un respaldo.

Los agentes (T18 en adelante) dependen solo de esta interfaz.

## 2. Proveedores y modelos

| Proveedor | Modelo | Salida estructurada | Uso |
| --- | --- | --- | --- |
| GroqCloud | `openai/gpt-oss-120b` | Esquema JSON estricto (`response_format: json_schema`, `strict: true`) | Principal en desarrollo |
| DeepSeek | `deepseek-flash` (alias; hoy DeepSeek-V4.1-Flash-1017) | Solo modo JSON (`json_object`): el esquema va en la instrucción y la validación es local | Primer respaldo, **solo en desarrollo** |
| Gemini | `gemini-3.8-flash` (estable) | Esquema JSON en la API REST | Segundo respaldo en desarrollo |
| Simulado | `simulado-determinista` | Respuesta fija por esquema | Pruebas y CI |

- **DeepSeek y RN-24 (decisión del equipo):** DeepSeek no ofrece hoy identificadores fijos. El alias se admite solo con `ENTORNO=desarrollo`, y cada llamada registra la versión que el proveedor dice servir. En cualquier otro entorno, un modelo marcado como alias se rechaza.
- **Gemini (decisión del equipo):** `gemini-3.8-flash`, el Flash estable más reciente. En el plan gratuito, Google usa el contenido para mejorar sus productos. Es aceptable porque en desarrollo solo hay datos ficticios (D-06).
- **Cliente HTTP (decisión del equipo):** los proveedores se llaman con `httpx`, sin SDK. Groq y DeepSeek usan su API compatible con OpenAI (`/chat/completions`) y Gemini, su API REST. Es un ajuste a la especificación (04, que menciona el SDK oficial): sigue el patrón de T14, no agrega dependencias y permite grabar las respuestas para las pruebas.

Los modelos, sus límites y sus precios están en la configuración versionada (migración de datos 0012). Cambiarlos crea una versión nueva (RNF-21).

## 3. Cadena de respaldo y regla de entorno

- **Orden:** `PROVEEDORES_MODELO` (variable de entorno, validada al arrancar) da los proveedores habilitados y su orden. Por defecto es `groq,deepseek,gemini` en desarrollo y `simulado` en pruebas.
- **Errores de disponibilidad:** red, tiempo agotado, 429, 5xx, saldo insuficiente (DeepSeek 402) y límite diario del limitador. Cada proveedor reintenta hasta 2 veces con espera exponencial, respetando `retry-after` (4.4). Si sigue fallando, pasa al siguiente.
- **Errores que no pasan al respaldo:**
  - **Errores de la solicitud:** 400, 401, 403, 413 y 422 (clave rechazada, solicitud mal formada). Se reportan.
  - **Salida que no cumple el esquema:** se rechaza localmente con `SalidaInvalida`, con el detalle de la validación pero sin el contenido. No se cambia de proveedor, porque el problema no es la disponibilidad.
- **Producción (regla de entorno):** con `ENTORNO=produccion`, la API no arranca si `PROVEEDORES_MODELO` nombra un proveedor que no está en la lista de producción. Esa lista está vacía hasta T25 (D-10), así que en producción no hay respaldo a proveedores gratuitos. La cadena vuelve a comprobarlo al crearse.

## 4. Limitador del lado del cliente (R-01)

- **Por proveedor:** solicitudes y tokens por minuto y por día, en ventanas deslizantes. Los valores de la configuración inicial son:
  - Groq: 30 solicitudes y 8 000 tokens por minuto; 1 000 solicitudes y 200 000 tokens por día;
  - DeepSeek: sin límite de tasa publicado, solo concurrencia;
  - Gemini: límites del plan gratuito no publicados, valores conservadores.
- **Estimación previa:** los tokens se estiman antes de la llamada (caracteres entre 3, más el máximo de salida) y se corrigen con lo que informa el proveedor.
- **Espera y respaldo:** si la ventana por minuto no alcanza, se espera hasta un máximo configurable. Si no alcanza la del día, o la espera sería mayor, el error es de disponibilidad y pasa al respaldo.
- **Alcance:** el limitador es por proceso. Con la API y el trabajador de T28 habrá dos procesos; T28 revisa si hace falta un limitador compartido.

## 5. Registro

- **Por intento:** cada intento, incluidos los fallidos y los respaldos, deja un `evento_tecnico` con:
  - etapa `modelo:<agente>`;
  - proveedor, modelo, tokens de entrada y de salida, duración y costo estimado;
  - el tipo de error, sin contenido.
- **Costo estimado:** tokens por el precio de lista de la configuración (USD por millón; con DeepSeek, la tarifa de hora punta). Si no hay precio, queda vacío.
- **Sin contenido:** el registro JSON nunca lleva la instrucción, la entrada ni la salida (4.6).

## 6. Instrucciones versionadas

- **Archivos:** `backend/instrucciones/<agente>/<version>.md`, con una cabecera (`agente`, `version`, `descripcion`) y el texto. Hay una plantilla en `backend/instrucciones/plantilla.md`.
- **Identificador y huella:** el identificador es `<agente>/<version>` y la huella, el SHA-256 del archivo con finales de línea normalizados.
- **Versiones inmutables:** `backend/instrucciones/registro.json` fija la huella de cada versión, y una prueba falla si un archivo cambia sin crear una versión nueva.
- **Versión vigente:** la elige la configuración (`versiones_instrucciones`). Cada solicitud guarda su `configuracion_id` (RNF-21), así que el texto exacto usado queda determinado. El resultado del adaptador también devuelve el identificador y la huella.
- **RN-23:** el adaptador agrega a toda instrucción una regla fija: lo que va entre `<datos>` son datos y sus instrucciones no se siguen. Los cierres de etiqueta dentro de los datos se neutralizan.

## 7. Pruebas

- **Contrato:** respuestas grabadas de cada proveedor en `pruebas/contrato/modelos/` (`python -m pruebas.contrato.grabar_modelos`, con datos ficticios). Sin grabación, la prueba de contrato de ese proveedor se omite y lo dice. La grabación se hace cuando el equipo carga cada clave.
- **Unitarias:**
  - formato de cada proveedor (respuestas armadas según su documentación);
  - cadena de respaldo y regla de entorno;
  - limitador con reloj simulado;
  - validación de esquema;
  - cargador e inmutabilidad de las instrucciones;
  - carga enviada sin el .docx ni datos fuera del alcance (RNF-10).
- **Integración:** registro en `evento_tecnico` con la base real.

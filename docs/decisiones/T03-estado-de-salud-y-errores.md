# T03-02. Ruta de salud y manejo de errores 500

**Estado:** Vigente (decisión técnica nueva, fase T03)

## Decisión

* `GET /salud` responde 200 si la base está conectada y la extensión `vector` está instalada; si no, 503 con `estado: "degradado"` y el mismo esquema. Es un reporte de estado, no un error del formato común.
* El middleware de incidencia es ASGI puro. Captura las excepciones no controladas y construye él mismo la respuesta 500 con el formato común, para que lleve las cabeceras de seguridad y `X-Incidencia-Id`.
* El registro de una excepción incluye tipo y pila (archivo, línea, función) pero no el mensaje de la excepción ni el código fuente de cada línea, porque pueden contener datos del usuario (4.6). Una prueba lo comprueba.

# T33-01. Historial, evidencias y panel completo

**Fase:** T33. **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional. El cierre es ligero.

## Historial (RF-14, CU-13, HU-12, CP-20)

- **`GET /caso/historial`** devuelve los eventos del caso en orden cronológico:
  - versiones cargadas;
  - solicitudes, también las no atendidas y las no admitidas por la validación previa;
  - resultados entregados con su etiqueta, el del último intento;
  - decisiones, marcando las reemplazadas;
  - fuentes aportadas.
- **Hito de cada evento:** el de la versión sobre la que se pidió la solicitud.
- **Filtros:**
  - `hito`;
  - `desde` y `hasta`: fechas de Lima, inclusive; un periodo invertido responde 422.
- **Arquitectura:** `app/registro/historial.py` arma los eventos sin acceso a la base. La API lee con el caso del contexto mediante los repositorios de siempre (4.5).
- **Orden:** a igual instante, versión, solicitud, resultado, decisión y aporte.

## Resumen para la declaración de herramientas

`GET /caso/historial/resumen`, con los mismos filtros, devuelve texto plano como adjunto. Contiene:

- el caso, el tema, el periodo y la fecha de generación;
- qué es la herramienta;
- los modelos de lenguaje usados, tomados de la salida de cada resultado;
- las solicitudes pedidas y entregadas por tipo;
- las decisiones vigentes por opción;
- el detalle cronológico.

No lleva el texto del borrador ni las salidas de los agentes. Sí lleva las consultas de evidencia, que escribió el propio estudiante.

## Evidencias (RF-21)

Cada cita de una búsqueda de evidencia muestra:

- el fragmento, la sección y la página;
- el documento: autores abreviados, año y DOI;
- el enlace de acceso abierto, si está comprobado.

Si la fuente es de la colección personal, muestra además los datos que aportó el caso (título, autores, año, DOI y fecha del aporte). Las citas de las otras pantallas ya se desplegaban desde T23 a T27.

## Panel (RF-19)

- Las solicitudes recientes llevan la etiqueta de su resultado (`etiquetas_finales`, sin cargar la salida).
- Cada tipo de pedido tiene una guía con ejemplos desplegables.
- Hay un enlace al historial.
- Lo demás ya estaba: versión vigente por hito (T13), uso mínimo por hito (T31) e invitación a cargar la primera versión.

## Provisional, sin revisión humana

- El contenido y la redacción del resumen para la declaración de herramientas, incluidos la descripción de la herramienta y el detalle cronológico.
- Los ejemplos de la guía de cada tipo.
- Las fechas del filtro se escriben como AAAA-MM-DD en campos de texto.
- Las solicitudes no admitidas por la validación previa figuran en el historial.

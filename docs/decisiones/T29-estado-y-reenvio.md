# T29-01. Estado en tiempo real, reenvío y mismo alcance

**Fase:** T29 (Bloque 3). **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico (textos y disposición de las pantallas) y lo anota como provisional. El cierre es ligero.

## Canal de eventos (RF-22, F-16)

- **`GET /caso/solicitudes/{id}/eventos`** (eventos enviados por el servidor, `text/event-stream`):
  - transmite el estado (recibida, asignada, recuperando, generando, verificando, reintentando, entregada, no atendida), el motivo y los intentos técnicos;
  - transmite solo lo que cambia y termina en un estado final.
- **Aislamiento:** el `ContextoAcceso` se valida antes de transmitir. Una solicitud de otro caso o inexistente responde 404, sin abrir el canal. La ruta está en la matriz de autorización.
- **Reconexión:** el servidor indica `retry: 3000` y, al conectarse, envía primero el estado actual. `EventSource` reconecta solo y parte de ese estado.
- **Duración y sesión:** el canal se cierra a los 5 minutos y el navegador vuelve a conectarse, con la sesión validada de nuevo. Cada 15 s sin cambios envía un latido.
- **Cómo se entera de los cambios:** el trabajador es otro proceso, así que el canal consulta la base cada segundo con una unidad de trabajo propia (no la de la petición) y el mismo contexto. Es una lectura indexada por la clave primaria; `LISTEN/NOTIFY` queda como mejora si hiciera falta más escala.
- **Estado "generando":** el contrato de agentes suma `al_generar`, que se llama solo con evidencia suficiente, justo antes de llamar al modelo. Antes, la espera del limitador de Groq se veía como "buscando". Una abstención no lo dispara.

## Reenvío y mismo alcance (F-06; Fase 1, 7.2)

- **`POST /caso/solicitudes/{id}/reenvio`:** solo para una solicitud "no atendida" (otra responde 409).
  - Crea una solicitud nueva con el mismo tipo, versión y alcance, la configuración vigente (RNF-21) y `solicitud_origen_id` apuntando a la original.
  - La lista "Sus solicitudes" lleva ese enlace.
- **`POST /caso/solicitudes/{id}/mismo-alcance` con `{tipo}`:** otra revisión de un tipo distinto sobre el mismo alcance, para pedidos de varias dimensiones.
  - Se admite si el tipo acepta ese alcance y su ejecutor trabaja por alcance; hoy, estructura y metodología de una misma sección.
  - Se valida como cualquier solicitud nueva sobre la versión vigente, y no se enlaza como reenvío.
  - Un tipo igual, o uno que no admite el alcance, responde 422.

## Interfaz (provisional, sin revisión humana)

- **Formulario:**
  - el panel ofrece cada tipo con su guía breve ("Qué puede pedir");
  - cada pantalla muestra solo los alcances válidos del tipo: sección, párrafo, hito o consulta libre solo en evidencia;
  - por eso no se agregó otro formulario genérico, que repetiría esas pantallas.
- **`AvanceSolicitud`:** muestra los pasos del avance (en cola, asignada, buscando en las guías y fuentes, preparando la respuesta, verificando, entregada).
  - El paso actual tiene `aria-current` y el estado se anuncia en una región `status`.
  - Si el servicio del modelo no respondió, avisa que el sistema lo intentará de nuevo y en qué intento va.
  - Al terminar, la pantalla pide el resultado de inmediato. Sin `EventSource`, la pantalla sigue con su consulta periódica.
- **`NoAtendida`:** muestra el motivo y el botón "Volver a pedir", que sigue a la solicitud nueva.
- **`OtraRevision`:** "Revisar también la metodología de esta sección" en el diagnóstico de estructura, y su inverso en el de metodología.

## Verificación

- Pruebas de integración:
  - secuencia de estados del canal, que solo avanza;
  - reconexión con el estado actual;
  - aislamiento;
  - reenvío enlazado y atendido, y 409 si no corresponde;
  - mismo alcance válido y rechazado;
  - aviso de "generando" solo con evidencia suficiente.
- Pruebas de la interfaz con un `EventSource` simulado.
- En el prototipo, con el modelo real y el trabajador, a través del proxy de Vite:
  - la revisión metodológica mostró el avance en vivo y se entregó en 90 s;
  - desde ella se pidió la estructura de la misma sección, que se entregó con 3 hallazgos.

**Pendiente:**
- el avance "n de m referencias" con el trabajador (podría viajar como evento);
- el reintento con evaluador (T30), que usará el estado "reintentando".

# T28-01. Orquestación, cola y trabajador

**Fase:** T28 (Bloque 3). **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional. Lo técnico sensible se preguntó: las trazas en la nube.

## Un solo camino para toda solicitud

- **Grafo de LangGraph 1.2** (`app/orquestacion/grafo.py`): validar → enrutar → ejecutar → verificar → etiquetar → registrar → entregar. Con abstención, de ejecutar pasa directo a entregar. Ante cualquier falla, a `no_atendida`.
- **Enrutamiento por tabla fija** (`enrutamiento.py`; tabla 9 de la tesis; RN-02, CP-03): sin modelo. Un tipo desconocido es un error de validación.
- **Ejecutores** (`app/agentes/ejecucion.py`): cada tipo tiene uno, con los pasos `ejecutar`, `verificar` y `registrar`, que el grafo recorre como nodos distintos.
  - `ejecutar` recupera, decide la suficiencia y genera, con el contrato de T18.
  - `verificar` aplica las comprobaciones del tipo. T30 agregará ahí el evaluador y el reintento.
  - Las tres atenciones anteriores (por alcance, evidencia y referencias) se convirtieron en ejecutores. Perdieron su propia tarea en segundo plano y su manejo de "interrumpida".
- **Una fábrica por proceso** (`fabrica.py`): la usan la API y el trabajador. Comparte una sola cadena de modelos, así el limitador de Groq cuenta las llamadas de todos los agentes juntos; antes, cada pantalla tenía la suya.
- **Estado del grafo:** solo identificadores, tipo, agente, nombres de comprobaciones, etiqueta y motivo de falla. El texto del borrador y la salida viajan en el contexto de la ejecución (`Runtime.context`), que no se guarda (4.6).
  - Una prueba comprueba que las tablas del checkpointer no tienen texto de la salida.

## Checkpointer, cola y trabajador

- **Checkpointer en PostgreSQL** (`langgraph-checkpoint-postgres` 3.2, `thread_id` = id de la solicitud). Sus tablas las crea la migración 0021 con la propia `setup()` de la biblioteca, en un bloque con confirmación automática por sus índices `CONCURRENTLY`. La aplicación nunca la llama.
- **Cola** (`app/repositorios/cola.py`): sobre `solicitud.estado`, con `SELECT ... FOR UPDATE SKIP LOCKED` y el índice parcial `ix_solicitud_cola`, que ya existía. Es el único repositorio que lee solicitudes de todos los casos.
  - Devuelve solo identificadores y la cuenta del caso.
  - El trabajador arma con esa cuenta el `ContextoAcceso` del caso y lee todo lo demás con los repositorios de caso, como la API (4.5).
- **Trabajador** (`python -m app.orquestacion.trabajador`, servicio `trabajador` de Compose):
  - toma hasta `CONCURRENCIA_TRABAJADOR` solicitudes a la vez (2 por omisión; 1 en el prototipo, por el límite de tokens de Groq);
  - cada minuto recupera las huérfanas: en curso y sin cambios durante `ESPERA_HUERFANA_S` (600 s).
- **Errores del proveedor (CP-07):**
  - una caída (`ErrorDisponibilidad`, después de los reintentos de la cadena) devuelve la solicitud a la cola con `intentos_tecnicos + 1`;
  - vuelve a tomarse tras `ESPERA_REINTENTO_S` (30 s) por intento;
  - al tercero queda "no atendida", recuperable con el reenvío (T29);
  - antes de reintentar, el grafo borra los fragmentos y el resultado que dejó el intento cortado;
  - cualquier otra falla deja "no atendida" con su motivo.
- **Parámetros funcionales:** el trabajador los lee al arrancar; un cambio de configuración se aplica al reiniciarlo.

## La API ya no ejecuta

- Las rutas `POST` validan y crean la solicitud, que queda "recibida" para el trabajador. Las rutas `GET` ya no marcan "interrumpida": la API no sabe si el trabajador la está atendiendo.
- **Invocación directa solo para pruebas:** con `EJECUCION_EN_PROCESO=true`, admitido solo en el entorno de pruebas, la API recorre el mismo grafo en su proceso, con un checkpointer en memoria. Así las pruebas de cada pantalla pasan por el orquestador.
- **Pantallas:** consideran en curso también "verificando" y "reintentando" (`frontend/src/solicitudes.ts`).
- **Avance de referencias:** el "n de m referencias" solo se ve si el grafo corre en el proceso de la API. Con el trabajador, la pantalla muestra el mensaje general. Volverá con los eventos de estado de T29.

## Trazas en la nube

Pospuestas por decisión del equipo (27 de noviembre de 2026; Fase 1, n.° 17).
- LangGraph instala el cliente de LangSmith, pero la imagen fija `LANGSMITH_TRACING=false`.
- La configuración no arranca si alguien enciende `LANGSMITH_TRACING` o `LANGCHAIN_TRACING_V2`.
- El registro propio ya guarda, por solicitud, los estados, la duración (evento técnico `orquestacion`), los tokens y las comprobaciones.

## Dependencias

`langgraph` 1.2.24 y `langgraph-checkpoint-postgres` 3.2.1, con su árbol de 23 paquetes en `restricciones-corpus.txt`. Se resolvió con las restricciones vigentes, sin cambiar ninguna versión anterior.

## Pruebas y verificación

- **Pruebas del orquestador:**
  - CP-03: los seis tipos llegan a su agente y a ninguno más;
  - CP-04: dos trabajadores nunca toman la misma solicitud;
  - CP-07: la caída reencola hasta agotar los intentos;
  - la espera tras una caída y la recuperación de huérfanas;
  - el trabajador con el checkpointer real y sin texto guardado;
  - la API deja la solicitud en cola.
- **Con el modelo real**, en el prototipo, el trabajador atendió el plan de tarea (37 s) y una revisión de estructura pedida desde el navegador (43 s, 3 hallazgos).

**Pendiente:** el formulario único, los eventos de estado y el reenvío (T29); el verificador completo con reintento (T30).

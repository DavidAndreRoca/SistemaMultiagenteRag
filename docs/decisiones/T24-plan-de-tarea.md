# T24-01. Plan de tarea del hito (agente D1, segundo tipo)

**Fase:** T24 (Bloque 2). **Fecha:** 26 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional, sin revisión humana. El cierre es ligero.

## Alcance y estado del borrador

- **Alcance de hito** (`alcance_tipo = hito`, sin `alcance_ref`, como exige la base): el estudiante elige un hito con versión vigente y la solicitud se asocia a esa versión.
- **Atención común:** `AtencionPorAlcance` suma `version_para` y `referencia_guardada`, y pasa el hito de la versión en `EstadoAgente.hito`.
- **Qué va al modelo:** el estado del borrador, no su texto. Es el árbol de títulos con sus palabras, los elementos detectados (problema, objetivos e hipótesis, con `estructura_borrador` de T12) y si hay lista de referencias. Es lo que el plan compara con las instrucciones del hito (RF-05, paso 2) y reduce lo que sale hacia el proveedor (RNF-10).

## Instrucciones del hito y abstención

- **Herramienta `instrucciones_del_hito`:** lee del corpus de guías el apartado del hito, por su nombre completo ("Avance 1: Planteamiento") o solo por el nombre ("Entrega final del plan"). Una guía oficial debe titular sus apartados así.
- **Sin instrucciones del hito:** el agente se abstiene sin recuperar ni llamar al modelo (RF-05, flujo alternativo).
  - El contrato suma `falta_insumo`, y `ServicioEvidencia.abstener` registra la abstención como las otras, con el paso nuevo `herramienta` y su motivo.
  - La pantalla muestra el motivo: "El corpus de guías no tiene instrucciones del hito ...".
- **Consulta de recuperación:** el hito y lo que pide entregar, sin el criterio de logro.
  - Trae primero las instrucciones del hito y después las pautas de las guías para esas partes.
  - Con el texto completo de las instrucciones, solo ellas superaban el umbral y el sistema se abstenía. Con "qué debe entregar el estudiante", traía también las instrucciones de los otros hitos.
  - Con la consulta final, los 8 hitos tienen su instrucción primera y una pauta pertinente sobre 0,5.
- **Guía provisional nueva:** `guia-estado-del-arte-y-plan.md`, sobre el estado del arte, la primera versión del método y la integración del plan de tesis. Sin ella, el avance 2 y la entrega del plan no tenían pautas en el corpus.

## Salida y comprobaciones

- **Esquema `PlanTarea`:** el sistema pone el nombre del hito y numera las tareas en orden desde 1.
- **Comprobaciones:** 1 (esquema), 2 (no reescritura, que ahora incluye `tarea` y `criterio_de_logro`) y 3 (citas).
- **El plan no modifica el borrador:** es un resultado más de la solicitud.

## Pantalla `/panel/plan`

- Ofrece solo los hitos con versión cargada, y por defecto el último.
- Muestra las tareas en orden con su criterio de logro y la instrucción desplegable.
- Botones "Copiar el plan" y "Descargar en texto" (`plan-de-tarea.txt`). El texto se arma en el navegador.
- La tarjeta del panel queda activa: ya no hay agentes pendientes en el panel.

## Prueba con el modelo real

Groq, 26 de noviembre de 2026, provisional. Avance 1 del borrador de demostración:
- 9 tareas en orden: título, contexto, problema como brecha, objetivo general, objetivos específicos, hipótesis, ubicación de objetivos e hipótesis, citas y coherencia entre título, problema y objetivos;
- cada tarea con su criterio y sus citas a las instrucciones del hito y a la guía IMRaD;
- 21 s, con las tres comprobaciones superadas.

## Provisional, sin revisión humana

- La instrucción `plan/v1`.
- La guía `guia-estado-del-arte-y-plan.md`.
- Los textos de la pantalla.
- La prueba real.

**Pendiente:** el reintento con los motivos de falla, en T30.

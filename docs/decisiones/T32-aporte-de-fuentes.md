# T32-01. Aporte de fuentes y colección personal

**Fase:** T32. **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional. El cierre es ligero.

## Flujo (RF-13, CU-12)

`POST /caso/solicitudes/{id}/aporte` recibe un formulario con título, autores (apellidos, uno por línea), año, DOI opcional y PDF opcional.

- **Cuándo se admite:** solo sobre una búsqueda de evidencia entregada como "Sin evidencia suficiente" del propio caso. Otra solicitud responde 409 `aporte_no_admitido`; una de otro caso, 404.
- **Decisión:** el aporte registra la decisión "aportar" sobre la abstención (CU-12 extiende CU-11).
- **Proceso en la misma petición** (`app/aportes/servicio.py`), en este orden:
  1. **Existencia** (`existencia.py`):
     - con DOI, Crossref y luego OpenAlex. Un DOI que ningún servicio resuelve no se confirma (CP-16): no se busca por metadatos una obra cuyo DOI declarado no existe;
     - sin DOI, búsqueda por metadatos con el comparador de T14: título, al menos un autor y año, con un año de tolerancia (CP-15);
     - un servicio caído da `no_comprobable`: no se indexa ni se declara inexistente (RN-18).
  2. **Duplicado:** mismo DOI o mismo texto en la colección personal. No se duplica, y se sigue con la nueva recuperación (CP-17).
  3. **Texto:**
     - el PDF, procesado con el canal de T09;
     - sin PDF, o si el PDF se excluye (por ejemplo, escaneado), el resumen de Crossref u OpenAlex (CP-15);
     - sin texto, la obra no se indexa (motivo `sin_texto`), pero se propone la cita.
  4. **Coherencia** con la afirmación: modelo con la instrucción `coherencia/v1`. Es informativa y no bloquea; si el modelo no responde, queda "no evaluada". Al modelo van la consulta y el resumen o los primeros fragmentos (RNF-10).
  5. **Cita propuesta** en la norma del caso: registro del DOI o formateador CSL, nunca un modelo (RN-17).
  6. **Indexación** solo en la colección personal: `RepositorioColeccionPersonal` toma la colección del caso del contexto, nunca de un identificador externo.
  7. **Nueva búsqueda** con la misma consulta, enlazada a la abstención (`solicitud_origen_id`), que la API encola.
- **Registro:**
  - `fuente_aportada` guarda la existencia, el método, la coherencia, la indexación con su motivo, la cita propuesta y la nueva solicitud (migración 0023);
  - el registro técnico guarda solo desenlaces;
  - el nombre original del PDF no se guarda.

## Resumen de los registros bibliográficos

- `MetadatosBibliograficos` gana `resumen`:
  - de Crossref, el JATS en texto plano;
  - de OpenAlex, reconstruido desde el índice invertido.
- La búsqueda de Crossref no lo trae, así que se pide la obra por DOI a cada servicio.
- Las entradas viejas de la caché no tienen resumen y se leen como `None`.

## D4 y RN-14

Las fuentes aportadas se recomiendan aunque no tengan acceso abierto comprobado, y no pasan por la comprobación 5: RN-14 no se aplica a los aportes (Fase 1, contexto).

## Opciones de decisión

Tras una abstención de otro tipo (estructura, metodología, redacción o plan), la única opción es "continuar": la colección personal la recupera solo D4. Aportar ya no figura como pendiente.

## Provisional, sin revisión humana

- **Segmentar el resumen** en fragmentos de oraciones completas de unas 60 palabras. Un resumen en un solo fragmento nunca llega a los `suficiencia_n` fragmentos pertinentes de RN-04, y no se cambia la regla. Los tokens del resumen se estiman (1,4 por palabra), sin el tokenizador.
- **Procesar el aporte en la petición** (unos segundos sin PDF; con PDF, lo que tarde Docling), como la subida del corpus del investigador, en lugar de la cola, que solo maneja solicitudes.
- **La afirmación es la consulta original** de la búsqueda, no un campo aparte que se pueda editar.
- **Textos de la interfaz:** mensajes de existencia, coherencia e indexación.
- **No guardar la explicación de la coherencia:** se muestra en la respuesta y no queda en la base.

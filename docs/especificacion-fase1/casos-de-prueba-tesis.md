# Casos de prueba de la tesis

**Fuente:** tesis *Taller de Investigacion 14-11-2026*, apartado 7.2.7.1 (casos de prueba representativos por caso de uso y pruebas del sistema integrado). Texto transcrito sin cambios de contenido.

**Uso:** cada fase que implemente un caso de uso debe contrastar sus pruebas con esta tabla. Si una prueba del repositorio difiere del resultado esperado, manda esta tabla y la diferencia se registra en `docs/decisiones/`.

Nota de numeración: el texto de la tesis llama "Tabla 20" a los casos de prueba y "Tabla 21" a las pruebas del sistema integrado; en los títulos de la versión del 14 de noviembre aparecen como Tabla 21 y Tabla 22. El contenido es el mismo.

## 1. Casos de prueba por caso de uso (CP-01 a CP-23)

| ID | Caso de uso | Escenario | Entrada | Resultado esperado |
| --- | --- | --- | --- | --- |
| CP-01 | CU-01 | Carga válida del borrador | Archivo .docx de un caso registrado | Se registra una nueva versión con fecha y hora; las versiones anteriores se conservan |
| CP-02 | CU-01, E1 | Archivo con formato no admitido | Archivo en un formato distinto de .docx o dañado | La carga se rechaza, se informa el motivo y no se registra ninguna versión |
| CP-03 | CU-02 | Asignación a un solo agente | Una solicitud de cada uno de los seis tipos | Cada solicitud se asigna al agente que indica la Tabla 9 y a ningún otro |
| CP-04 | CU-02, flujo principal | Propuesta verificada | Solicitud con evidencia suficiente en la colección | Se entrega una propuesta con su fuente y la etiqueta "Verificada"; la solicitud, la propuesta y la verificación quedan registradas |
| CP-05 | CU-02, A1; CU-09, A1 | Abstención por evidencia insuficiente | Consulta sobre un tema sin documentos pertinentes en la colección | No se genera contenido; se entrega el aviso "Sin evidencia suficiente"; la abstención queda registrada |
| CP-06 | CU-02, A2 y A3 | Reintento y etiqueta "Con advertencias" | Solicitud cuya propuesta no supera la verificación en dos intentos | Se regenera la propuesta una sola vez; tras la segunda verificación no superada se entrega con la etiqueta "Con advertencias"; se registran ambos intentos |
| CP-07 | CU-02, E1 | Proveedor sin respuesta | Solicitud válida con el proveedor del modelo de lenguaje sin respuesta | Se informa que la solicitud no pudo atenderse y se registra como no atendida; no se entrega contenido |
| CP-08 | CU-03, CU-05 | Diagnóstico sin reescritura | Sección del borrador | El resultado contiene diagnóstico y recomendaciones y no contiene una versión reescrita de la sección |
| CP-09 | CU-06, A4 | Fragmento que excede el límite | Fragmento de más de un párrafo o de más de unas 250 palabras | El sistema pide seleccionar un fragmento más corto y no procesa la solicitud |
| CP-10 | CU-06; CU-10 | Propuesta que excede 1.2 veces el original | Fragmento válido cuya propuesta generada supera la extensión permitida | La verificación no se supera por límites y se activa el reintento |
| CP-11 | CU-07; CU-10 | Fuente recomendada que no es de acceso abierto | Consulta cuya evidencia recuperada incluye un documento que no es de acceso abierto | El documento no se entrega como fuente recomendada; si la propuesta lo cita, la verificación no se supera |
| CP-12 | CU-08 | Referencias con estados distintos | Borrador con una referencia existente, una con datos discrepantes y una inexistente | El informe marca cada referencia como "verificada", "con discrepancias" y "no localizada", y señala las citas sin entrada en la lista |
| CP-13 | CU-08, E2 | Servicios externos sin respuesta | Verificación de referencias con las bases bibliográficas externas sin respuesta | Se informa que la verificación no pudo completarse y ninguna referencia se marca como inexistente |
| CP-14 | CU-12 | Fuente aportada con DOI | Fuente en PDF con DOI válido después de una abstención | El sistema solicita el DOI, confirma la existencia en las bases bibliográficas externas, evalúa la coherencia, genera la propuesta de cita, indexa la fuente y recupera de nuevo para la misma solicitud |
| CP-15 | CU-12 | Fuente aportada sin DOI, verificada por búsqueda por metadatos | Fuente sin DOI y sin PDF, solo con los datos bibliográficos de una publicación existente | El sistema confirma la existencia mediante la búsqueda por metadatos, al coincidir el título, al menos un autor y el año; evalúa la coherencia, genera la propuesta de cita e indexa el resumen obtenido de las bases bibliográficas |
| CP-16 | CU-12, A1 | Fuente cuya existencia no se confirma | Fuente con DOI que no se resuelve o con datos bibliográficos que no se localizan | El sistema informa que la existencia no se confirmó, no indexa la fuente y registra el intento |
| CP-17 | CU-12, A2 | Fuente ya indexada | Fuente que ya está en la colección personal del caso | El sistema lo informa, no la duplica y continúa con la nueva recuperación |
| CP-18 | CU-11 | Registro de decisiones | Aceptar, modificar y rechazar tres propuestas distintas | Cada decisión queda asociada a su propuesta y los contadores se incrementan en uno por tipo |
| CP-19 | CU-11, A1 | Continuar sin aportar fuente | Resultado "Sin evidencia suficiente" y elección de continuar | Se registran la abstención y la elección del estudiante |
| CP-20 | CU-13 | Aislamiento del historial | Dos casos con interacciones registradas | Cada caso ve solo sus versiones, solicitudes, resultados y decisiones, en orden cronológico |
| CP-21 | CU-14, E1 | Documento duplicado en el corpus | Documento ya indexado en la misma colección | El documento se rechaza y se informa el motivo |
| CP-22 | CU-15, E1 | Código de caso repetido | Registro de un código existente | No se crea un caso duplicado y se informa el motivo |
| CP-23 | CU-16 | Exportación sin datos personales | Exportación de todos los casos en un periodo | El archivo contiene los registros identificados solo por código, con los campos necesarios para la ficha de registro de métricas |

**Tabla 9 de la tesis (referida en CP-03):** asignación de tipo de solicitud a agente. Corresponde a la tabla 3 de `docs/insumos/insumos-modelo-de-datos-y-configuracion.md`: revisión de estructura y plan de tarea al agente D1; revisión metodológica al D2; propuesta de redacción al D3; búsqueda de evidencia y verificación de referencias al D4.

## 2. Pruebas del sistema integrado (PI-01 a PI-09)

Se ejecutan al cierre del bloque 3, con el sistema configurado como se usará en la posprueba.

| ID | Prueba | Procedimiento | Resultado esperado |
| --- | --- | --- | --- |
| PI-01 | Flujo completo por tipo de solicitud | Un caso de prueba carga una versión y formula una solicitud de cada uno de los seis tipos | Las seis solicitudes recorren asignación, recuperación, generación o abstención, verificación, etiqueta, entrega y registro |
| PI-02 | Colección por tipo de solicitud | Revisión de los fragmentos recuperados en cada solicitud de PI-01 | Cada solicitud consulta solo la colección que le corresponde |
| PI-03 | Ciclo de abstención y aporte | Solicitud sin evidencia, aporte de una fuente con existencia confirmada y nueva recuperación | La misma solicitud pasa de "Sin evidencia suficiente" a un resultado con la fuente aportada |
| PI-04 | Etiquetado universal | Revisión de todos los resultados generados durante PI-01 a PI-03 | Todo resultado tiene una y solo una de las tres etiquetas |
| PI-05 | Trazabilidad de extremo a extremo | Exportación del registro después de PI-01 a PI-03 | Cada resultado puede rastrearse hasta su versión del borrador, su solicitud, sus verificaciones y su decisión |
| PI-06 | Aislamiento entre casos | Dos casos de prueba trabajan con temas distintos | Ningún caso accede a la información ni a la colección personal del otro |
| PI-07 | Versionado continuo | Un caso carga varias versiones e incorpora propuestas entre cargas | Todas las versiones se conservan y cada solicitud queda asociada a la versión vigente |
| PI-08 | Completitud del registro para las métricas | Cálculo de prueba de los seis indicadores técnicos sobre el registro exportado | Los seis indicadores pueden calcularse con los campos exportados |
| PI-09 | Desempeño, disponibilidad y capacidad | 28 sesiones simultáneas de casos de prueba formulan solicitudes de los seis tipos | Todas las solicitudes se atienden dentro del tiempo de respuesta objetivo de cada tipo, sin caídas del servicio |

## 3. Condiciones de las pruebas (tesis, 7.2.7.1)

- Se usan casos de prueba ficticios identificados por código; ningún participante de la muestra interviene antes de la posprueba.
- Los borradores de prueba son de dos tipos: borradores elaborados por el equipo y artículos de acceso abierto en español con errores introducidos a propósito (de estructura, de método, de redacción y de referencias), de modo que se sabe de antemano qué debe detectar cada agente.
- Cada caso de prueba se ejecuta al cierre del sprint en que se construye la funcionalidad y se repite en los sprints siguientes para comprobar que no hubo regresiones.

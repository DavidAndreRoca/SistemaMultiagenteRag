# 1. Resumen ejecutivo

Este documento traduce la tesis "Sistema multiagente con generación aumentada por recuperación para la asistencia inteligente en la producción de artículos científicos empíricos de una universidad privada de Ica" en una especificación de software lista para desarrollarse por incrementos. Parte de la versión del documento de tesis del 3 de noviembre de 2026 (de la Introducción a la Metodología Marco), de los artefactos de modelado registrados en el proyecto y de las decisiones vigentes, y la complementa con investigación tecnológica verificada en fuentes oficiales al 4 de noviembre de 2026.

El software es la variable independiente X del diseño GE: O1 X O2. Su propósito no es redactar el artículo, sino asistir al caso (autoría individual o en pareja) en la elaboración del segundo artículo, con seis tipos de solicitud asociados a las cuatro dimensiones de la variable dependiente, recuperando evidencia de colecciones verificables antes de generar, absteniéndose cuando la evidencia no alcanza, verificando cada propuesta antes de entregarla y registrando cada decisión del estudiante.

Las decisiones técnicas principales que propone este documento son las siguientes:

- **Arquitectura:** un orquestador determinista que enruta por tipo de solicitud (sin consenso entre agentes), cuatro agentes especializados con colecciones, herramientas y esquemas de salida distintos, y un módulo de integración y verificación independiente de los agentes que generan. Se mantiene la arquitectura conceptual de la tesis.
- **Stack:** Python 3.12 con FastAPI en el backend; React con TypeScript en el frontend; LangGraph 1.x para el grafo de orquestación; PostgreSQL con pgvector como base única para el registro de interacciones, los metadatos y los vectores; bge-m3 como modelo de embeddings multilingüe local con bge-reranker-v2-m3 como reordenador; Docling, GROBID y python-docx para el procesamiento documental; Crossref, la negociación de contenido de doi.org, Unpaywall y OpenAlex para la verificación bibliográfica.
- **Modelo de lenguaje:** un proveedor comercial con API de pago cuyas condiciones excluyen el entrenamiento con los datos enviados, como ya exige la tesis. Se recomienda la API de Claude (Sonnet 5.5 para los agentes y Haiku 5.5 para tareas auxiliares), con un adaptador que permite cambiar de proveedor, y se fija una prueba comparativa breve antes de congelar la versión estable. El costo estimado de la API durante O2 va de unos USD 10 a USD 200 según la configuración (unos USD 90 a 120 en la recomendada), y el presupuesto total del software, incluido el servidor, de USD 170 a 455.
- **Cambios respecto a decisiones previas:** se reemplaza Chroma y SQLite por PostgreSQL con pgvector, y Streamlit por una aplicación React, por razones de aislamiento entre casos, concurrencia, trazabilidad y control de la interfaz. Se mantienen LangGraph, Crossref como fuente principal y OpenAlex como complemento, ahora con clave de API obligatoria.
- **Escenario recomendado:** el escenario híbrido (B). El escenario de mínimo costo (A) es útil para el desarrollo con datos ficticios, pero no cumple las condiciones de la tesis para O2.

El documento también identifica contradicciones que deben corregirse en la tesis porque afectan al software (asignación de temas en O1, duración de cada ciclo, número de fases), propone requisitos complementarios de ingeniería que no estaban en la Metodología Marco y cierra con una lista de decisiones pendientes, cada una con su recomendación.

> **Convención de este documento.** Se marca con **[V]** un hecho verificado en una fuente citada (sección 25), con **[R]** una recomendación de diseño y con **[S]** un supuesto que debe confirmarse. Los códigos RF-01 a RF-17, RNF-01 a RNF-14, RN-01 a RN-14, CU-01 a CU-16, HU-01 a HU-15, CP-01 a CP-23 y PI-01 a PI-09 son los de la tesis; los códigos nuevos continúan esas series y se identifican como complementarios.

# 2. Análisis integral de la tesis y del problema

## 2.1. Fuentes revisadas y límites del análisis

Se revisaron íntegramente, en el espacio del proyecto, los siguientes documentos: "Taller de Investigacion 03-11-2026" (versión más reciente, que contiene desde la Introducción hasta la Metodología Marco y la bibliografía), "Modelo-Casos-de-Uso" (versión 2 del 3 de noviembre), "Decisiones-Pendientes-6.2" y las notas de proyecto que resumen decisiones de conversaciones anteriores (por ejemplo, el calendario del 3 de noviembre, la decisión sobre el DOI y la conformación del corpus).

Límites que deben declararse:

- Las figuras de la tesis (BPMN, cursogramas, diagramas UML, arquitectura y modelo de datos) están en el documento como imágenes; su texto no es legible. El análisis se basa en las descripciones escritas de cada figura y en las tablas, que son detalladas. No se accedió a los archivos de Bizagi ni al código PlantUML original más allá de lo registrado en el proyecto.
- No se tuvo acceso directo a las transcripciones de conversaciones anteriores; solo a los documentos del proyecto y a las notas de decisiones registradas. Si alguna decisión se tomó en una conversación y no quedó registrada, no está reflejada aquí.
- Los anexos (matriz de consistencia, matriz de operacionalización completa e instrumentos) se consultaron de forma parcial mediante búsqueda en el documento; los indicadores de las dimensiones se tomaron del apartado 6.1.4, que los enumera completos.
- No se revisaron los documentos más antiguos de marco teórico y antecedentes, porque su contenido ya está integrado en la versión del 3 de noviembre.

## 2.2. Problema, objetivos e hipótesis

**Tabla 1. Síntesis de la formulación de la investigación**
| Elemento | Contenido vigente (tesis del 03-11-2026) |
|---|---|
| Problema general | ¿De qué manera un sistema multiagente con generación aumentada por recuperación optimiza la producción de artículos científicos empíricos en los estudiantes de una universidad privada de Ica, 2027? |
| Objetivo general | Diseñar y construir un sistema multiagente con RAG para optimizar la producción de artículos científicos empíricos (redacción exigida por el asesor). Se evidencia en el artefacto funcional y su evaluación técnica. |
| OE1 / HE1 | Estructura y coherencia textual (D1): alineación problema-objetivos-hipótesis; secuencia lógica discursiva; cohesión entre apartados. |
| OE2 / HE2 | Rigor metodológico y de contenido (D2): justificación del diseño; validez de técnicas e instrumentos; precisión en el análisis de datos. |
| OE3 / HE3 | Sintaxis y redacción académica (D3): registro formal; fluidez discursiva y precisión léxica; corrección gramatical y claridad sintáctica. |
| OE4 / HE4 | Normativa y referenciación (D4): aplicación de la norma de citación; calidad de las fuentes; verificabilidad de las referencias. |
| Optimizar | Obtener con el sistema puntajes de calidad del manuscrito significativamente superiores a los del proceso actual, por dimensión o en el total de la rúbrica, con α = 0.05. |
| Variable independiente (medición técnica) | Calidad de la recuperación documental (cobertura, precisión contextual, completitud) y fidelidad y precisión de la respuesta generada (fidelidad respuesta-fuente, relevancia, tasa de referencias no verificables), más usabilidad y confianza percibida por cuestionario. |

## 2.3. Causas, consecuencias y su traducción al software

La tesis identifica cuatro causas y tres consecuencias. Cada una tiene una respuesta concreta en el software; esta correspondencia es la columna vertebral de la matriz de trazabilidad de la sección 11.

**Tabla 2. Del problema a la respuesta del software**
| Causa o consecuencia (apartado 2) | Evidencia citada en la tesis | Respuesta del software |
|---|---|---|
| C1. Escaso dominio de fuentes y dispersión de herramientas | [24]: solo 22.24 % usa Scopus; búsqueda, gestión y redacción en recursos separados | Búsqueda de evidencia con referencia asociada en el mismo entorno (CU-07), aporte de fuentes (CU-12) y propuesta de cita |
| C2. Retroalimentación de utilidad insuficiente y dependiente de la sesión semanal | [25]: la utilidad percibida de los comentarios predice el desempeño | Atención de la solicitud cuando el caso la formula (CU-02), con diagnóstico específico por dimensión |
| C3. Uso de IA generativa sin orientación | [26]: 94.1 % de docentes sin política institucional | Propuestas acotadas, sin reescritura de secciones, verificadas y etiquetadas (CU-06, CU-10) |
| C4. Ausencia de diagnóstico por componente del manuscrito | [27]: dificultades múltiples y relacionadas | Seis tipos de solicitud atendidos por un solo agente por dimensión (CU-03 a CU-08) |
| K2. Deterioro de la trazabilidad de la información | [29]: más de 80 % de DOI alucinados en ciertos contextos | Recuperación previa, citas por identificador cerrado, verificación de existencia y abstención (CU-08 a CU-10) |
| K3. Pérdida de trazabilidad de la autoría | [30]: la sospecha de uso de IA altera la calificación | Versionado del borrador, registro de solicitudes, resultados y decisiones; historial del caso (CU-01, CU-11, CU-13) |
| K1. Brecha entre instituciones | [28] | No tiene respuesta directa en el software; es contexto del problema |

## 2.4. Fundamentos que condicionan el diseño

De los antecedentes y las bases teóricas se derivan cinco principios de diseño que el software debe respetar, porque son los que la tesis declara como sustentados:

1. **Selección y no consenso** [46]: el orquestador elige un solo agente por solicitud; no hay votación ni fusión de respuestas de varios agentes.
2. **Recuperación con verificación de citas** [42]: ninguna referencia llega al estudiante sin comprobación de existencia.
3. **Participación humana en el ciclo** [41]: el estudiante decide sobre cada propuesta; el sistema no escribe por él.
4. **Retroalimentación diferenciada por dimensión** [47]: los agentes diagnostican y recomiendan; solo el estilístico propone redacción y con límites.
5. **La recuperación no basta por sí sola** [31], [48]: hacen falta abstención, verificación independiente y un diseño pedagógico, no un "proveedor de respuestas".

Además, Radeva et al. [46] advierten que la sobrecarga de coordinación degrada el desempeño cuando los agentes solo se diferencian por la instrucción de sistema. Por eso la especificación de la sección 6 diferencia a los agentes por colección, herramientas, esquema de salida y reglas de verificación, no solo por el texto de sus instrucciones.

## 2.5. Diseño metodológico y su impacto en el software

- **Diseño:** preexperimental GE: O1 X O2. El sistema se usa solo en O2. La misma rúbrica evalúa O1 y O2 a ciegas; el cuestionario y la ficha de métricas se aplican solo en O2.
- **Unidad de análisis:** el artículo; cada caso es una autoría individual o en pareja. Población estimada de 30 y muestra de 28 (pendiente de la nómina oficial).
- **Calendario (decisión del 3 de noviembre):** el periodo 2027-1 inicia en mayo de 2027; O1 en las semanas 1 a 10, transición en la semana 11 y O2 en las semanas 12 a 22. El desarrollo empieza en noviembre de 2026 y la versión estable se congela en la semana 8, cuatro semanas antes de O2.
- **Temas:** en O1 cada caso elige libremente su tema; en O2 esos temas rotan para que ningún caso repita el suyo.
- **Corpus científico:** se forma con las referencias de acceso abierto del artículo O1 de cada tema. Por ello el corpus definitivo solo existe al final de O1, y la semana 11 se reserva para completar la carga y medir las métricas técnicas sin modificar el código.
- **Implicaciones directas para el software:** (a) debe existir una herramienta de importación de referencias desde el artículo O1 de cada tema, porque cargar a mano hasta 28 corpus en pocas semanas no es viable; (b) la versión estable debe poder congelarse y versionarse; (c) el registro debe permitir calcular todos los indicadores técnicos sin datos personales; (d) el artículo O1 en sí no debe indexarse ni mostrarse a otro caso.

## 2.6. Metodología Marco: lo que ya está definido

La Metodología Marco ya produjo la línea base funcional del sistema, que este documento respeta y no reemplaza: el límite del sistema; los actores A1 Estudiante, A2 Investigador, A3 Proveedor del modelo de lenguaje y A4 Bases bibliográficas externas; los casos de uso CU-01 a CU-16 con generalización (CU-02 abstracto con seis hijos), inclusión (CU-09, CU-10) y extensión (CU-12 sobre CU-11); las historias HU-01 a HU-15; los requisitos RF-01 a RF-17 y RNF-01 a RNF-14; las reglas RN-01 a RN-14; la tabla de roles; el modelo de datos de diez entidades; el plan de 16 sprints en tres bloques; los casos de prueba CP-01 a CP-23 y las pruebas integradas PI-01 a PI-09; el protocolo de evaluación técnica con umbrales (tasa de referencias no verificables menor o igual a 0.05, fidelidad mayor o igual a 0.90, precisión contextual mayor o igual a 0.80) y la matriz de trazabilidad.

Queda pendiente, por decisión explícita de la tesis, todo lo que el apartado 6.2.5.1 delega al proyecto de software: la base de datos vectorial, los marcos de desarrollo, la interfaz, el modelo de representación concreto, el proveedor del modelo de lenguaje y los parámetros de calibración. Este documento cierra esas decisiones.

## 2.7. Decisiones confirmadas, propuestas anteriores y pendientes

**Tabla 3. Estado de las decisiones relevantes para el software**
| Decisión | Estado | Comentario para el software |
|---|---|---|
| Orquestador sin dimensión propia más cuatro agentes D1 a D4 y módulo de integración y verificación | Confirmada | Base de la arquitectura lógica |
| Coordinación por selección, no por consenso | Confirmada | El grafo no tiene nodos de fusión de respuestas |
| Seis tipos de solicitud elegidos por el estudiante | Confirmada | La clasificación no la hace un modelo; ver sección 7.2 |
| Recuperación antes de generar; abstención con "Sin evidencia suficiente" | Confirmada | Nodo de suficiencia en dos pasos |
| Un reintento y tres etiquetas | Confirmada | "Verificada", "Con advertencias", "Sin evidencia suficiente" |
| Redacción fuera del sistema; carga de .docx versionada | Confirmada | No hay editor de texto en la aplicación |
| DOI no obligatorio; existencia por DOI o metadatos (título, al menos un autor, año) | Confirmada (nov. 2026) | Verificación en cascada; ver sección 18 |
| Fuentes recomendadas de acceso abierto (RN-14); no aplica a fuentes aportadas | Confirmada | Comprobación con Unpaywall u OpenAlex |
| Corpus científico = referencias OA del artículo O1 del tema | Confirmada (3 nov. 2026) | Requiere importador de referencias (RF-20) |
| Temas libres en O1 y rotación en O2 | Confirmada (31 oct. 2026) | Hasta 28 corpus; principal riesgo de cobertura |
| Proveedor LLM comercial con API de pago sin entrenamiento | Confirmada como tipo | Se recomienda proveedor concreto en la sección 17 |
| Modelo de representación multilingüe; segmentación por secciones IMRaD | Confirmada como tipo | Se elige bge-m3 [R] |
| LangGraph como orquestador | Propuesta previa | Se mantiene [R] |
| Chroma como base vectorial; SQLite como registro | Propuesta previa | Se reemplazan por PostgreSQL con pgvector [R] |
| Streamlit como interfaz | Propuesta previa | Se reemplaza por React [R] |
| Crossref principal y OpenAlex complementario | Propuesta previa | Se mantiene, con Unpaywall para acceso abierto [R] |
| Norma de citación del artículo | Pendiente | El sistema la configura como estilo CSL; falta la del programa |
| Tiempo de respuesta objetivo (RNF-12) | Pendiente | Se proponen valores iniciales en la sección 9 |
| Alojamiento durante O2 | Pendiente | Se recomienda en la sección 13 |

## 2.8. Contradicciones e información incompleta que afectan al software

**Tabla 4. Inconsistencias detectadas y su efecto**
| Hallazgo | Dónde | Efecto en el software y recomendación |
|---|---|---|
| El apartado 6.1.2 (fase 3 y control de amenazas) dice que en O1 se sortea un tema de un banco común; el apartado 6.2.2.1 y la decisión del 31 de octubre dicen que el tema se elige libremente | Tesis, 6.1.2 frente a 6.2.2.1 | Con temas libres puede haber hasta 28 corpus de tamaño variable. El software lo soporta, pero la tesis debe unificar la redacción del 6.1.2 |
| La fase 4 indica "durante 22 semanas" y la fase 5 "durante 6 semanas"; el calendario vigente fija O1 en las semanas 1 a 10 y O2 en las 12 a 22. También se mantiene que "el intervalo no supera 6 semanas" | Tesis, 6.1.2 | La disponibilidad exigida (RNF-13) es de las semanas 12 a 22. Corregir las duraciones en la tesis |
| "La ejecución del diseño se organiza en ocho fases sucesivas", pero se enumeran siete | Tesis, 6.1.2 | Sin efecto técnico; corrección documental |
| La población figura como 30 artículos estimados; las notas del proyecto indicaban usar marcadores hasta tener la nómina | Tesis 6.1.3 y notas | La capacidad (RNF-14) se diseña para 28 casos simultáneos con margen; ver sección 9 |
| La Tabla 1 de la tesis menciona RN-01 a RN-13, mientras los casos de uso v2 y el 6.2.5.1 ya usan RN-14 | Tesis, Tabla 1 | Actualizar a RN-01 a RN-14 |
| El enunciado de esta fase propone que "el estudiante confirma la clasificación" del orquestador; la tesis establece que el estudiante elige el tipo y el orquestador no decide por él | Enunciado de la fase frente a RN-01, RN-02 | Se mantiene la tesis: no hay clasificación automática en la versión estable. Una sugerencia opcional queda como decisión pendiente |
| El proveedor del modelo debe figurar en el consentimiento informado, pero aún no está elegido | Aspectos éticos | Bloquea el trámite ante el comité de ética; debe cerrarse en el primer bloque de sprints |
| La norma de citación no está fijada ("la que establecen las instrucciones del programa") | 6.2.5.1 | Afecta a CU-08 (análisis de citas en el texto) y a la propuesta de cita. Se diseña configurable |
| El corpus científico depende del artículo O1 de otro caso; si ese artículo tiene pocas referencias de acceso abierto, el corpus será pequeño | Decisión del 3 de noviembre | Riesgo alto de abstenciones y baja cobertura; se mitiga con el aporte de fuentes (CU-12) y se reporta por tema |
| No está definido cómo se identifica cada sección del borrador para fijar el alcance de una solicitud | CU-02, CU-03 | Se propone detectar secciones por los estilos de título del .docx, con selección manual de respaldo (RF-02) |

# 3. Descripción de la solución software

## 3.1. Qué problema concreto resuelve

El software resuelve un problema de proceso: en el AS-IS, entre la búsqueda de fuentes y la inserción de citas no existe ninguna inspección, la retroalimentación depende de la sesión semanal, la revisión docente es global y el proceso no deja rastro de cómo se produjo el texto. El sistema añade un punto de control verificable y bajo demanda, separado por dimensión, sin quitarle al estudiante la redacción ni la decisión.

## 3.2. Qué hace y qué no hace

**Tabla 5. Alcance funcional del sistema**
| El sistema sí | El sistema no |
|---|---|
| Recibe versiones .docx del borrador y las conserva | Edita el borrador ni ofrece un procesador de textos |
| Atiende seis tipos de solicitud con un solo agente cada vez | Mantiene un chat libre de propósito general |
| Recupera evidencia de colecciones autorizadas antes de generar | Genera contenido sin evidencia suficiente |
| Entrega diagnósticos, planes, propuestas de un párrafo y evidencia con su fuente | Reescribe secciones completas ni redacta el artículo |
| Verifica existencia, acceso abierto y fidelidad de cada propuesta | Entrega propuestas sin verificar |
| Verifica las referencias del borrador y su correspondencia con las citas | Califica el artículo con la rúbrica |
| Registra solicitudes, resultados, verificaciones y decisiones | Guarda datos personales |
| Exporta el registro para la ficha de métricas | Calcula los resultados del experimento ni almacena la rúbrica o el cuestionario |
| Permite al investigador conformar el corpus y registrar los casos | Se integra con Canvas, Turnitin o el docente |

## 3.3. Actividades del TO-BE apoyadas y responsabilidades

**Tabla 6. Reparto de actividades del subproceso TO-BE**
| Actividad TO-BE | Responsable | Tipo de tarea |
|---|---|---|
| Redactar o corregir, insertar citas, incorporar cambios aceptados | Caso (fuera del sistema) | Humana; agrega valor |
| Cargar la versión del borrador (T3) | Caso en el sistema | Humana con registro automático |
| Formular la solicitud y elegir su tipo (T4) | Caso | Humana; el sistema valida el alcance |
| Asignar la solicitud (T5) | Orquestador | Automatizada y determinista |
| Recuperar evidencia y evaluar suficiencia (T6) | Agente asignado | Automatizada |
| Generar la propuesta (T7) | Agente con el proveedor LLM | Automatizada |
| Verificar, etiquetar y entregar (T8, T9) | Módulo de integración y verificación | Automatizada |
| Revisar el resultado y decidir (T10) | Caso | Humana obligatoria |
| Registrar la decisión (T11) | Sistema | Automatizada |
| Aportar una fuente tras una abstención (T13) | Caso | Humana |
| Comprobar existencia e indexar la fuente aportada (T14) | Módulo de verificación y agente D4 | Automatizada |
| Revisión docente semanal, subida a Canvas | Docente y caso (fuera del sistema) | Humana |
| Conformar el corpus, registrar casos, exportar el registro | Investigador | Humana asistida por el sistema |

## 3.4. Resultados concretos que produce

- Un **resultado etiquetado** por solicitud: diagnóstico con recomendaciones, plan de tarea editable, propuesta de redacción junto al original, evidencia con referencia asociada o informe de verificación de referencias.
- Un **historial del caso** que sirve para demostrar el aporte propio y elaborar la declaración de herramientas.
- Un **registro exportable** identificado por código, del que se calculan los seis indicadores técnicos, los contadores de propuestas aceptadas, modificadas y rechazadas y el cumplimiento del uso mínimo orientativo.
- Un **informe técnico** de la versión estable (pruebas y métricas) que evidencia el cumplimiento del objetivo general.

# 4. Usuarios y necesidades

**Tabla 7. Usuarios, necesidades y criterios de éxito**
| Usuario | Necesidades | Criterio de éxito del software |
|---|---|---|
| A1 Estudiante (caso) | Retroalimentación por dimensión sin esperar la sesión semanal; evidencia verificable para sus afirmaciones; detectar referencias inexistentes o mal citadas; mejorar párrafos sin perder la autoría; saber cuándo puede confiar en una salida; demostrar su aporte | Resultado útil con etiqueta clara; ninguna referencia inventada; decisión registrada en un clic; historial completo de su caso y solo de su caso |
| A2 Investigador | Conformar y mantener hasta 28 corpus temáticos y el corpus de guías; registrar casos sin datos personales; congelar la versión estable; exportar datos para la ficha de métricas; vigilar errores y costos | Importación de referencias por tema en minutos; exportación sin intervención manual; configuración versionada; tablero de errores y gasto |
| Docente del taller, evaluadores, Canvas | No usan el sistema | El sistema no expone ni almacena información de la evaluación ciega |
| A3 Proveedor LLM y A4 bases bibliográficas | Sistemas externos | Envío acotado de datos (RNF-10); respeto de límites de uso |

Una autoría en pareja comparte una sola cuenta por caso (RN-13). Como ambos integrantes pueden trabajar a la vez, el sistema debe admitir dos sesiones simultáneas de la misma cuenta sin conflictos; esto se resuelve porque cada solicitud es independiente y se asocia a la versión vigente en el momento de formularla.

# 8. Requisitos funcionales

Se conservan los diecisiete requisitos de la tesis (RF-01 a RF-17) con el mismo código, para no crear una segunda numeración, y se detallan al nivel que exige la implementación. Se añaden diez requisitos complementarios (RF-18 a RF-27) derivados de esta especificación; si se aceptan, deben incorporarse a la Tabla 6 de la tesis con su origen. Cada requisito es verificable con al menos un caso de prueba de la sección 21.

**Tabla 18. Resumen de requisitos funcionales**
| Código | Nombre | Prioridad | Origen | Módulo / CU |
|---|---|---|---|---|
| RF-01 | Cargar y versionar el borrador .docx | Alta | Tesis | Versiones / CU-01 |
| RF-02 | Formular solicitud con tipo y alcance | Alta | Tesis | Solicitudes / CU-02 |
| RF-03 | Asignar a un solo agente según el tipo | Alta | Tesis | Orquestador / CU-02 |
| RF-04 | Diagnóstico de estructura y coherencia | Alta | Tesis | Agente D1 / CU-03 |
| RF-05 | Plan de tarea editable | Media | Tesis | Agente D1 / CU-04 |
| RF-06 | Diagnóstico metodológico | Alta | Tesis | Agente D2 / CU-05 |
| RF-07 | Propuesta de redacción acotada | Alta | Tesis | Agente D3 / CU-06 |
| RF-08 | Evidencia con referencia asociada | Alta | Tesis | Agente D4 / CU-07 |
| RF-09 | Estado de referencias y correspondencia | Alta | Tesis | Agente D4 / CU-08 |
| RF-10 | Recuperación, suficiencia y abstención | Alta | Tesis | RAG / CU-09 |
| RF-11 | Verificación previa, reintento y etiqueta | Alta | Tesis | Verificación / CU-10 |
| RF-12 | Registro de decisiones y contadores | Alta | Tesis | Registro / CU-11 |
| RF-13 | Aporte, comprobación e indexación de fuente | Media | Tesis | Verificación y D4 / CU-12 |
| RF-14 | Historial del caso | Media | Tesis | Registro / CU-13 |
| RF-15 | Gestión de corpus de guías y científico | Alta | Tesis | Corpus / CU-14 |
| RF-16 | Gestión de casos participantes | Alta | Tesis | Casos / CU-15 |
| RF-17 | Exportación del registro por código | Alta | Tesis | Exportación / CU-16 |
| RF-18 | Autenticación, roles y sesiones | Alta | Complementario | Seguridad |
| RF-19 | Panel del caso con ayuda contextual | Alta | Complementario | Interfaz |
| RF-20 | Importación de referencias del artículo O1 | Alta | Complementario | Corpus / CU-14 |
| RF-21 | Visualización de evidencias | Alta | Complementario | Interfaz / CU-07 |
| RF-22 | Estado de la solicitud y reenvío | Alta | Complementario | Solicitudes / CU-02 |
| RF-23 | Configuración versionada y congelamiento | Alta | Complementario | Administración |
| RF-24 | Monitoreo técnico y de costos | Media | Complementario | Observabilidad |
| RF-25 | Arnés de evaluación técnica | Alta | Complementario | Evaluación (6.2.7.2) |
| RF-26 | Eliminación de datos al cierre de O2 | Alta | Complementario | Administración / RNF-11 |
| RF-27 | Exportación RIS o BibTeX de la cita | Baja | Complementario | Agente D4 |

## 8.1. Especificación detallada

### RF-01. Cargar y versionar el borrador

| Campo | Detalle |
|---|---|
| Descripción | Permite cargar el borrador en .docx; cada carga crea una versión nueva con fecha, hora e hito, sin eliminar las anteriores |
| Actor | A1 |
| Precondiciones | Sesión A1 activa; caso habilitado |
| Flujo principal | 1) Elige hito. 2) Adjunta .docx. 3) El sistema valida extensión, tipo MIME, firma del contenedor, tamaño y tamaño descomprimido. 4) Guarda el archivo con nombre aleatorio. 5) Extrae texto y secciones (RF-02). 6) Registra la versión y la marca como vigente del hito |
| Alternativos | Primera versión del hito: lo informa. Archivo inválido, con macros (.docm), cifrado o dañado: rechaza sin crear versión (CP-02). Archivo sin estilos de título: crea la versión y pide marcar secciones manualmente |
| Resultado | Versión registrada y vigente |
| Prioridad | Alta |

### RF-02. Formular solicitud con tipo y alcance

| Campo | Detalle |
|---|---|
| Descripción | Permite elegir uno de los seis tipos y el alcance: sección (de la lista detectada), fragmento (un párrafo) o consulta (texto libre, solo CU-07) |
| Actor | A1 |
| Precondiciones | Existe una versión vigente |
| Flujo principal | 1) Elige tipo. 2) La interfaz muestra solo los alcances válidos para el tipo. 3) Selecciona el alcance. 4) El sistema valida límites (CU-06: un párrafo hasta unas 250 palabras) y pertinencia de la consulta. 5) Crea la solicitud asociada a la versión vigente y la encola |
| Alternativos | Alcance fuera de límites: pide uno menor (CP-09). Consulta ambigua o fuera de alcance: no se encola; se explica qué puede pedir |
| Resultado | Solicitud en estado "recibida" |
| Prioridad | Alta |

### RF-03. Asignar a un solo agente según el tipo

| Campo | Detalle |
|---|---|
| Descripción | Asigna la solicitud al agente que indica la Tabla 9 de la tesis, sin modificar el tipo |
| Actor | Sistema (orquestador) |
| Precondiciones | Solicitud validada |
| Flujo principal | 1) Lee el tipo. 2) Aplica la tabla fija. 3) Registra agente y dimensión |
| Alternativos | Tipo desconocido: error de validación, solicitud no atendida |
| Resultado | Solicitud asignada a exactamente un agente (CP-03) |
| Prioridad | Alta |

### RF-04. Diagnóstico de estructura y coherencia

| Campo | Detalle |
|---|---|
| Descripción | Entrega hallazgos y recomendaciones sobre los tres indicadores de D1 para la sección indicada, sin reescribir |
| Actor | A1; agente estructural |
| Precondiciones | Solicitud asignada al agente D1 |
| Flujo principal | 1) Recupera del corpus de guías. 2) Evalúa suficiencia. 3) Genera hallazgos con ubicación, severidad, recomendación y citas. 4) Verificación. 5) Entrega |
| Alternativos | Abstención; reintento; "Con advertencias" |
| Resultado | Diagnóstico etiquetado (CP-08) |
| Prioridad | Alta |

### RF-05. Plan de tarea editable

| Campo | Detalle |
|---|---|
| Descripción | Genera una lista ordenada de tareas para el hito, con criterio de logro, a partir de las instrucciones del programa y del estado del borrador |
| Actor | A1; agente estructural |
| Precondiciones | Instrucciones y sílabo del programa indexados en el corpus de guías |
| Flujo principal | 1) Recupera las instrucciones del hito. 2) Compara con las secciones presentes. 3) Genera el plan. 4) Verificación. 5) Entrega; el caso puede copiarlo o descargarlo en texto |
| Alternativos | Sin instrucciones del hito en el corpus: abstención |
| Resultado | Plan etiquetado |
| Prioridad | Media |

### RF-06. Diagnóstico metodológico

| Campo | Detalle |
|---|---|
| Descripción | Entrega hallazgos sobre los tres indicadores de D2 y preguntas sobre información faltante, sin reescribir ni inventar datos |
| Actor | A1; agente metodológico |
| Precondiciones | Solicitud asignada al agente D2 |
| Flujo principal | Igual a RF-04, con la lista de comprobación según el diseño declarado |
| Alternativos | Diseño no identificable: lo pregunta en `preguntas_al_estudiante` |
| Resultado | Diagnóstico etiquetado |
| Prioridad | Alta |

### RF-07. Propuesta de redacción acotada

| Campo | Detalle |
|---|---|
| Descripción | Propone una versión de un párrafo de hasta unas 250 palabras, con extensión de hasta 1.2 veces el original, presentada junto al original con los cambios explicados |
| Actor | A1; agente estilístico |
| Precondiciones | Párrafo dentro del límite |
| Flujo principal | 1) Recupera pautas. 2) Genera propuesta y lista de cambios. 3) Verificación de límites y de conservación del contenido. 4) Entrega en vista comparada |
| Alternativos | Propuesta excede 1.2 veces: falla y reintento (CP-10) |
| Resultado | Propuesta etiquetada |
| Prioridad | Alta |

### RF-08. Evidencia con referencia asociada

| Campo | Detalle |
|---|---|
| Descripción | Responde una consulta o sustenta una afirmación con fragmentos del corpus científico del tema y de la colección personal, citando cada afirmación; recomienda solo fuentes de acceso abierto |
| Actor | A1; agente RAG bibliográfico |
| Precondiciones | Tema del caso con corpus indexado |
| Flujo principal | 1) Recupera de ambas colecciones. 2) Suficiencia. 3) Genera afirmaciones con citas a fragmentos. 4) El sistema arma las referencias desde los metadatos. 5) Verificación. 6) Entrega con evidencias navegables (RF-21) |
| Alternativos | Abstención con opción de aporte (CU-12); fuente cerrada citada: verificación falla (CP-11) |
| Resultado | Evidencia etiquetada |
| Prioridad | Alta |

### RF-09. Estado de referencias y correspondencia

| Campo | Detalle |
|---|---|
| Descripción | Informa cada referencia de la versión como verificada, con discrepancias, no localizada o no comprobable, y la correspondencia entre las citas del texto y la lista |
| Actor | A1; agente RAG bibliográfico |
| Precondiciones | La versión contiene una lista de referencias |
| Flujo principal | 1) Extrae la lista con GROBID y las citas del texto según el estilo configurado. 2) Para cada referencia: DOI en Crossref; si no hay DOI, búsqueda bibliográfica por metadatos en Crossref y OpenAlex; para libros, ISBN [S, servicio por confirmar]. 3) Compara título, autores y año. 4) Cruza citas y lista. 5) Verificación del informe. 6) Entrega |
| Alternativos | Servicios caídos: "no comprobable" y aviso, nunca "inexistente" (CP-13). Lista no detectada: pide indicar la sección de referencias |
| Resultado | Informe etiquetado (CP-12) |
| Prioridad | Alta |

### RF-10. Recuperación, suficiencia y abstención

| Campo | Detalle |
|---|---|
| Descripción | Recupera de la colección que corresponde al tipo y se abstiene si la evidencia no es suficiente |
| Actor | Sistema |
| Precondiciones | Solicitud asignada |
| Flujo principal | 1) Filtro de colecciones por tipo y caso. 2) Búsqueda densa y léxica. 3) Fusión RRF. 4) Reranking. 5) Filtro: mínimo N fragmentos con puntaje mayor o igual a tau. 6) Juicio del modelo de suficiencia. 7) Entrega fragmentos con ID o abstención |
| Alternativos | Abstención: no hay generación (CP-05) |
| Resultado | Contexto cerrado o abstención registrada |
| Prioridad | Alta |

### RF-11. Verificación previa, reintento y etiqueta

| Campo | Detalle |
|---|---|
| Descripción | Aplica las seis comprobaciones de la sección 6.7; regenera una sola vez; asigna una de tres etiquetas |
| Actor | Sistema (módulo de integración y verificación) |
| Precondiciones | Existe propuesta o abstención |
| Flujo principal | Ver Figura 7 |
| Alternativos | Segunda falla: "Con advertencias" (CP-06) |
| Resultado | Resultado etiquetado y verificaciones registradas por intento (PI-04) |
| Prioridad | Alta |

### RF-12. Registro de decisiones y contadores

| Campo | Detalle |
|---|---|
| Descripción | Registra aceptar, modificar o rechazar (o continuar o aportar tras una abstención) y actualiza contadores |
| Actor | A1 |
| Precondiciones | Resultado entregado sin decisión |
| Flujo principal | 1) Elige opción. 2) El sistema registra con fecha y hora. 3) Confirma |
| Alternativos | Cambio de decisión: no se permite editar; se registra una decisión nueva que reemplaza a la anterior conservando ambas [R] |
| Resultado | Decisión asociada al resultado (CP-18, CP-19) |
| Prioridad | Alta |

### RF-13. Aporte, comprobación e indexación de fuente

| Campo | Detalle |
|---|---|
| Descripción | Tras una abstención, permite aportar PDF con datos bibliográficos o solo datos; comprueba existencia, evalúa coherencia, propone cita e indexa en la colección personal si la existencia se confirma |
| Actor | A1; módulo de verificación; agente D4 |
| Precondiciones | Solicitud con abstención |
| Flujo principal | Según CU-12 de la tesis; el PDF se procesa con Docling y GROBID; si no hay PDF, se indexa el resumen de Crossref u OpenAlex |
| Alternativos | No confirmada: no indexa (CP-16). Duplicada: no duplica (CP-17). Servicios caídos: no indexa ni declara inexistente |
| Resultado | Fuente indexada y nueva recuperación (CP-14, CP-15) |
| Prioridad | Media |

### RF-14. Historial del caso

| Campo | Detalle |
|---|---|
| Descripción | Muestra en orden cronológico versiones, solicitudes, resultados con etiqueta y decisiones del caso |
| Actor | A1 |
| Precondiciones | Sesión A1 |
| Flujo principal | Filtra por hito o periodo; abre el detalle; permite descargar un resumen para la declaración de herramientas |
| Alternativos | Sin registros: lo informa |
| Resultado | Historial solo del caso (CP-20) |
| Prioridad | Media |

### RF-15. Gestión de corpus de guías y científico

| Campo | Detalle |
|---|---|
| Descripción | Carga, indexa y retira documentos; registra por tema las referencias excluidas por no tener acceso abierto |
| Actor | A2 |
| Precondiciones | Sesión A2 |
| Flujo principal | Según CU-14, con Docling, segmentación IMRaD, embeddings bge-m3 e índice en pgvector |
| Alternativos | Documento ilegible, escaneado sin texto o duplicado: rechazo con motivo (CP-21) |
| Resultado | Colecciones actualizadas |
| Prioridad | Alta |

### RF-16. Gestión de casos participantes

| Campo | Detalle |
|---|---|
| Descripción | Registra cada caso con código, tipo de autoría y tema de O2; crea colección personal y cuenta; permite desactivar |
| Actor | A2 |
| Precondiciones | Corpus del tema existente |
| Flujo principal | Según CU-15; la contraseña inicial se genera aleatoria y se muestra una sola vez |
| Alternativos | Código repetido: rechazo (CP-22) |
| Resultado | Caso habilitado |
| Prioridad | Alta |

### RF-17. Exportación del registro por código

| Campo | Detalle |
|---|---|
| Descripción | Exporta, para los casos y el periodo elegidos, las tablas del registro en CSV (abrible en Excel) y JSON, sin datos personales |
| Actor | A2 |
| Precondiciones | Interacciones registradas |
| Flujo principal | Selecciona filtros; el sistema genera un paquete con un archivo por entidad y un diccionario de datos |
| Alternativos | Sin datos: no genera archivo |
| Resultado | Paquete exportado (CP-23, PI-08) |
| Prioridad | Alta |

### RF-18. Autenticación, roles y sesiones (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Inicio y cierre de sesión con código y contraseña; dos roles (A1 caso, A2 investigador); bloqueo temporal tras intentos fallidos; cambio de contraseña inicial |
| Actor | A1, A2 |
| Precondiciones | Cuenta creada |
| Flujo principal | Credenciales, verificación de hash Argon2, cookie de sesión HttpOnly, Secure y SameSite, expiración por inactividad |
| Alternativos | Credenciales inválidas; cuenta desactivada; bloqueo tras 5 intentos en 15 minutos [R, ajustable] |
| Resultado | Sesión con rol; toda ruta valida rol y caso |
| Prioridad | Alta |

### RF-19. Panel del caso con ayuda contextual (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Muestra versión vigente, hito, solicitudes recientes con su etiqueta, cumplimiento del uso mínimo orientativo por hito y una guía breve de cada tipo de solicitud con ejemplos |
| Actor | A1 |
| Precondiciones | Sesión A1 |
| Flujo principal | Carga resumida desde el registro |
| Alternativos | Caso sin versiones: invita a cargar la primera |
| Resultado | Panel; soporta la sesión de inducción de O2 |
| Prioridad | Alta |

### RF-20. Importación de referencias del artículo O1 (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Para un tema, extrae la lista de referencias del .docx del artículo O1 (o acepta una lista de DOI), resuelve cada referencia, comprueba acceso abierto, obtiene el PDF legal cuando es posible e indexa |
| Actor | A2 |
| Precondiciones | Tema creado; artículo O1 o lista disponible |
| Flujo principal | 1) Carga. 2) Extracción con GROBID. 3) Resolución por DOI o metadatos. 4) Unpaywall: estado y mejor ubicación OA. 5) Descarga del PDF si el enlace es directo. 6) Indexación. 7) Resumen: referencias totales, OA, excluidas, pendientes de PDF |
| Alternativos | Sin enlace directo: "pendiente de PDF" para carga manual. Referencia no localizada: excluida con motivo |
| Resultado | Corpus del tema y conteos que alimentan la entidad Colección |
| Prioridad | Alta |
| Regla clave | El artículo O1 no se almacena tras la extracción ni se indexa (RN-19) |

### RF-21. Visualización de evidencias (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Junto a cada afirmación del resultado muestra el fragmento citado, el documento, la sección, la página y el enlace de acceso abierto |
| Actor | A1 |
| Precondiciones | Resultado con citas |
| Flujo principal | Al pulsar la cita, despliega el fragmento y sus metadatos |
| Alternativos | Fuente de la colección personal: muestra los datos que aportó el caso |
| Resultado | Evidencia inspeccionable |
| Prioridad | Alta |

### RF-22. Estado de la solicitud y reenvío (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Informa en tiempo real el estado de la solicitud y permite reenviar una solicitud no atendida por error técnico |
| Actor | A1 |
| Precondiciones | Solicitud creada |
| Flujo principal | Eventos SSE: recibida, asignada, recuperando, generando, verificando, reintentando, entregada |
| Alternativos | Desconexión: la interfaz consulta el estado al reconectar. No atendida: botón de reenvío que crea una solicitud nueva enlazada |
| Resultado | Estado visible y reenvío registrado |
| Prioridad | Alta |

### RF-23. Configuración versionada y congelamiento (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Administra umbrales (tau, N, fidelidad), estilo CSL de citación, modelos y versiones fijas, límites de tamaño y de extensión, versiones de las instrucciones de cada agente; cada cambio crea una versión de configuración; el congelamiento bloquea cambios funcionales |
| Actor | A2 |
| Precondiciones | Sesión A2 |
| Flujo principal | Edita, guarda con comentario, el sistema asocia cada solicitud a la versión de configuración vigente |
| Alternativos | Tras el congelamiento solo se permite una corrección crítica, que crea una versión nueva registrada |
| Resultado | Toda solicitud es reproducible con su versión de configuración |
| Prioridad | Alta |

### RF-24. Monitoreo técnico y de costos (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Registra por solicitud la latencia por etapa, tokens de entrada y salida por modelo, costo estimado y errores; muestra un tablero y alerta al superar umbrales |
| Actor | A2 |
| Precondiciones | Ninguna |
| Flujo principal | Agregación diaria; alertas por correo o en el panel al superar el gasto diario o la tasa de errores |
| Alternativos | Tope de gasto alcanzado: modo protegido que rechaza nuevas solicitudes con aviso [R] |
| Resultado | Control de RNF-12 a RNF-14 y del presupuesto |
| Prioridad | Media |

### RF-25. Arnés de evaluación técnica (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Ejecuta el conjunto de solicitudes de prueba (60: diez por tipo) contra una versión y calcula las seis métricas de la ficha, con la evidencia de referencia construida a mano |
| Actor | A2 (línea de comandos) |
| Precondiciones | Conjunto de prueba cargado; corpus provisional o definitivo |
| Flujo principal | Ejecuta, guarda resultados por versión de código y configuración, exporta muestra aleatoria del 20 al 30 % para revisión humana y calcula concordancia |
| Alternativos | Métrica bajo umbral: informe con detalle por tipo |
| Resultado | Informe técnico para declarar la versión estable |
| Prioridad | Alta |

### RF-26. Eliminación de datos al cierre (complementario)

| Campo | Detalle |
|---|---|
| Descripción | Tras la exportación final de O2, elimina borradores, PDF aportados y colecciones personales, y deja constancia |
| Actor | A2 |
| Precondiciones | Exportación final realizada |
| Flujo principal | Confirmación doble; borrado de archivos y registros asociados; los respaldos que los contengan se eliminan al vencer su rotación |
| Alternativos | Exportación no realizada: bloquea la eliminación |
| Resultado | Cumplimiento de RNF-11 |
| Prioridad | Alta |

### RF-27. Exportación RIS o BibTeX de la cita (complementario, opcional)

| Campo | Detalle |
|---|---|
| Descripción | Descarga la fuente propuesta en RIS o BibTeX para importarla en Mendeley |
| Actor | A1 |
| Precondiciones | Fuente con DOI |
| Flujo principal | Negociación de contenido en doi.org |
| Alternativos | Sin DOI: genera el archivo desde los metadatos almacenados |
| Resultado | Archivo importable |
| Prioridad | Baja |

# 9. Requisitos no funcionales

Los catorce requisitos de la tesis se mantienen. La tabla siguiente añade, para cada uno, la métrica de verificación y el momento en que se fija el valor, y propone requisitos complementarios (RNF-15 a RNF-24). Los valores numéricos propuestos son iniciales: se justifican y se confirman en las pruebas del bloque 3.

**Tabla 19. Requisitos no funcionales con métrica y criterio**
| Código | Atributo | Requisito y métrica | Justificación del valor y momento de fijarlo |
|---|---|---|---|
| RNF-01 | Trazabilidad | 100 % de resultados rastreables hasta versión, solicitud, verificaciones y decisión | Comprobado por PI-05; no es negociable porque sostiene la ficha de métricas |
| RNF-02 | Privacidad | Ningún campo de nombre, correo o DNI en el modelo de datos ni en las exportaciones | Revisión del esquema y prueba CP-23 |
| RNF-03 | Aislamiento | 0 accesos cruzados entre casos en pruebas de autorización | PI-06 y pruebas automáticas por ruta |
| RNF-04 | Abstención | 0 generaciones cuando el nodo de suficiencia decide abstención | CP-05; garantizado por el grafo |
| RNF-05 | Verificación previa | 0 resultados entregados sin registro de verificación (salvo abstenciones) | PI-04 |
| RNF-06 | Límites | 100 % de propuestas estilísticas dentro de 1.2 veces; 0 reescrituras en D1 y D2 | CP-08, CP-10 |
| RNF-07 | Control del estudiante | El sistema solo actúa ante una solicitud; no hay acciones automáticas sobre el borrador | Revisión de diseño |
| RNF-08 | Acceso abierto | 100 % de fuentes recomendadas con estado OA comprobado | CP-11 |
| RNF-09 | Independencia de la evaluación | La rúbrica no figura en ninguna colección | Revisión del corpus de guías |
| RNF-10 | Envío acotado | Al proveedor solo viajan solicitud, alcance y fragmentos; nunca el .docx completo | Inspección de cargas en PI-01 |
| RNF-11 | Retención | Eliminación al cierre (RF-26) | Plazo del registro: el que fije el comité |
| RNF-12 | Tiempo de respuesta | Propuesta inicial, percentil 95: 60 s para D1, D2, D3 y evidencia; 120 s para verificación de 40 referencias | Una solicitud incluye recuperación, una o dos generaciones y una evaluación; la verificación de referencias está limitada por Crossref (3 consultas de búsqueda por segundo en el pool cortés [V, T18]). Se fija tras medir en el sprint 12 |
| RNF-13 | Disponibilidad | 99 % mensual durante las semanas 12 a 22, medido por sondeo externo cada 5 minutos | Equivale a unas 7 horas de caída por mes; suficiente para un uso asíncrono. Exige un servidor que no se suspenda por inactividad |
| RNF-14 | Capacidad | 28 sesiones simultáneas con solicitudes de los seis tipos sin errores (PI-09) | Se diseña con 2 workers concurrentes por núcleo para no saturar el límite de tasa del proveedor; se confirma con prueba de carga |
| RNF-15 | Seguridad | HTTPS obligatorio; contraseñas con Argon2; cookies seguras; cabeceras de seguridad; dependencias sin vulnerabilidades críticas conocidas | Buenas prácticas OWASP; escaneo de dependencias en cada sprint |
| RNF-16 | Gestión de secretos | Claves de API solo en variables de entorno o archivo de secretos fuera del repositorio; nunca en el frontend | Revisión automática de secretos en el repositorio |
| RNF-17 | Usabilidad | Tarea "cargar versión y pedir una revisión" completada sin ayuda en menos de 3 minutos por 4 de 5 estudiantes en la prueba piloto | Coherente con la dimensión de usabilidad del cuestionario; se mide en la prueba piloto de las semanas 8 y 9 |
| RNF-18 | Accesibilidad | Pautas WCAG 2.2 nivel AA en contraste, foco visible, etiquetas y navegación por teclado | Estándar de referencia; se verifica con herramientas automáticas y revisión manual |
| RNF-19 | Mantenibilidad | Cobertura de pruebas automáticas de al menos 70 % en servicios y agentes; código tipado; formato y linter en integración continua | El desarrollo con asistente de programación exige pruebas que detecten regresiones; el valor se revisa en el bloque 1 |
| RNF-20 | Modularidad | Proveedor LLM, modelo de embeddings y servicios bibliográficos detrás de interfaces; cambiar de proveedor no toca los agentes | Mitiga riesgos de precio y disponibilidad |
| RNF-21 | Reproducibilidad | Toda solicitud registra versión de código, de configuración, de instrucciones y del modelo (identificador fijo con fecha) | Necesario para declarar que todos los casos usaron el mismo artefacto |
| RNF-22 | Interoperabilidad | Exportaciones en CSV UTF-8 y JSON con diccionario de datos; API documentada con OpenAPI | Excel y SPSS leen CSV |
| RNF-23 | Calidad de respuestas | En el conjunto de prueba: tasa de referencias no verificables menor o igual a 0.05, fidelidad mayor o igual a 0.90 y precisión contextual mayor o igual a 0.80 | Umbrales de la tesis (6.2.7.2) |
| RNF-24 | Costo | Tope mensual de gasto en API configurado en el proveedor y en el sistema; alerta al 50 % y al 80 % | Evita sorpresas; el valor depende del presupuesto aprobado (sección 17.4) |

# 10. Reglas de negocio

**Tabla 20. Reglas de negocio**
| Código | Regla | Origen |
|---|---|---|
| RN-01 | El sistema actúa solo a solicitud del estudiante | Tesis |
| RN-02 | El orquestador asigna cada solicitud a un solo agente según su tipo; no hay consenso; no decide por el estudiante | Tesis, [46] |
| RN-03 | Cada tipo consulta solo la colección que le corresponde | Tesis |
| RN-04 | Sin evidencia suficiente no se genera contenido; suficiencia en dos pasos (umbral y número mínimo, luego juicio del modelo) | Tesis |
| RN-05 | Toda propuesta se verifica antes de entregarse; un solo reintento; si falla de nuevo, "Con advertencias" | Tesis |
| RN-06 | Todo resultado lleva exactamente una de tres etiquetas | Tesis |
| RN-07 | D1 y D2 no reescriben; D3 se limita a un párrafo de hasta unas 250 palabras y a 1.2 veces el original | Tesis |
| RN-08 | El estudiante decide sobre cada resultado; se registran decisiones y abstenciones | Tesis |
| RN-09 | Cada carga crea una versión nueva; formato .docx | Tesis |
| RN-10 | Una fuente aportada se indexa solo si su existencia se confirma por DOI o por metadatos (título, al menos un autor y año); la coherencia no bloquea | Tesis (actualizada) |
| RN-11 | El corpus de guías no incluye la rúbrica | Tesis |
| RN-12 | Casos identificados solo por código; sin datos personales | Tesis |
| RN-13 | Una cuenta por caso; cada caso accede solo a su información | Tesis |
| RN-14 | Las fuentes recomendadas son de acceso abierto; no aplica a fuentes aportadas | Tesis |
| RN-15 | Las contraseñas se almacenan solo como hash; la sesión expira por inactividad | Complementaria |
| RN-16 | Se aceptan .docx de hasta 15 MB y PDF de hasta 25 MB y 60 páginas; se rechazan .docm, archivos cifrados y contenedores con tamaño descomprimido anómalo | Complementaria [R, ajustable] |
| RN-17 | Los agentes citan solo identificadores de fragmentos recuperados; las referencias que ve el estudiante las arma el sistema con los metadatos almacenados, nunca el modelo | Complementaria |
| RN-18 | Si un servicio bibliográfico no responde, la fuente queda "no comprobable" y nunca "inexistente" | Complementaria (de CU-08 E2) |
| RN-19 | Del artículo O1 de un tema solo se usan sus referencias; el artículo no se almacena ni se indexa | Complementaria |
| RN-20 | Las exportaciones no incluyen texto de los borradores salvo el alcance de cada solicitud, que se puede excluir; los datos se purgan al cierre | Complementaria |
| RN-21 | Tras el congelamiento no hay cambios funcionales; toda corrección crítica crea una versión de configuración o de código registrada | Tesis (6.2.7.2) |
| RN-22 | Al alcanzar el tope de gasto el sistema deja de aceptar solicitudes y lo informa | Complementaria |
| RN-23 | El contenido de borradores y documentos se trata como datos; las instrucciones que contengan no se ejecutan | Complementaria (seguridad) |
| RN-24 | Durante O2 el identificador del modelo es fijo (versión con fecha); no se usan alias que cambian de modelo automáticamente | Complementaria |

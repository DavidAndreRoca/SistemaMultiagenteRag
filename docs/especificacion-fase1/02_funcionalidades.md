# 5. Catálogo de funcionalidades

## 5.1. Evaluación de los módulos propuestos

Cada módulo de la lista inicial se evaluó contra el problema, los objetivos, el TO-BE y el diseño O1 X O2. El criterio fue: un módulo es necesario si sin él no se cumple algún caso de uso o algún requisito de la tesis; es opcional si aporta valor sin ser condición de la intervención; y es contraproducente si introduce comportamientos que la tesis excluye o confusores en la medición.

**Tabla 8. Evaluación de módulos**
| Módulo | Decisión | Justificación |
|---|---|---|
| 1. Gestión de usuarios y sesiones | Necesario (mínimo) | Una cuenta por caso y una por investigador (RN-13). No se necesita registro abierto, recuperación de contraseña por correo ni perfiles: no se guardan datos personales |
| 2. Gestión de proyectos o trabajos | Necesario como "caso" | Cada caso tiene un único artículo de O2 con sus hitos. Un gestor de múltiples proyectos sería complejidad sin uso |
| 3. Panel principal del estudiante | Necesario | Punto de entrada: versión vigente, hito, solicitudes recientes, estado del uso mínimo orientativo |
| 4. Asistente conversacional multiagente | Contraproducente como chat libre | Un chat abierto mezcla dimensiones, incentiva pedir textos completos y dificulta la trazabilidad por tipo. Se reemplaza por solicitudes tipificadas con alcance explícito; la consulta libre existe solo dentro de CU-07 |
| 5. Orquestación y clasificación | Necesario (orquestación); clasificación automática no | El estudiante elige el tipo (RN-01, RN-02). Clasificar con un modelo añadiría errores de asignación como confusor. Una sugerencia no vinculante queda para después de O2 |
| 6 a 9. Agentes D1 a D4 | Necesarios | Son la diferenciación funcional que la tesis somete a contraste |
| 10. Gestión y recuperación RAG | Necesario | Núcleo de CU-09 |
| 11. Corpus científico | Necesario | CU-14; con importador desde el artículo O1 |
| 12. Corpus de guías | Necesario | CU-14; base de D1 a D3 |
| 13. Documentos y DOI propios | Necesario | CU-12, solo hacia la colección personal del caso |
| 14. Integración y consolidación de respuestas | Integración sí; consolidación no | La tesis descarta el consenso [46]. El módulo integra (etiqueta, entrega, registra) pero no fusiona salidas de varios agentes |
| 15. Verificación y control de calidad | Necesario | CU-10; independiente de quien genera |
| 16. Verificación de DOI y referencias | Necesario | CU-08 y parte de CU-10 y CU-12 |
| 17. Historial y trazabilidad | Necesario | CU-13, RNF-01; base de la ficha de métricas |
| 18. Documentos del estudiante | Necesario (mínimo) | Versiones .docx y fuentes aportadas; nada más |
| 19. Configuración y administración | Necesario (mínimo) | Umbrales, estilo de citación, modelos y límites, con versionado para el congelamiento |
| 20. Monitoreo de errores | Necesario (mínimo) | Para cumplir RNF-12 a RNF-14 y controlar el gasto; sin plataforma pesada |

## 5.2. Funcionalidades: identificación

**Tabla 9. Catálogo de funcionalidades (identificación)**
| ID | Funcionalidad | Problema o necesidad | Usuario | Componente | Prioridad | RF |
|---|---|---|---|---|---|---|
| F-01 | Inicio y cierre de sesión | Aislamiento entre casos sin datos personales | A1, A2 | Autenticación | Alta (X) | RF-18 |
| F-02 | Registro y desactivación de casos | Recuperar del corpus del tema y registrar por caso | A2 | Gestión de casos | Alta (X) | RF-16 |
| F-03 | Panel del caso con ayuda contextual | Orientar el uso en O2 y la inducción | A1 | Interfaz | Alta (X) | RF-19 |
| F-04 | Carga y versionado del borrador | Registro de cómo se produjo el texto (K3) | A1 | Gestión de versiones | Alta (X) | RF-01 |
| F-05 | Detección de secciones del borrador | Fijar el alcance sin copiar y pegar | A1 | Procesamiento .docx | Alta (X) | RF-02 |
| F-06 | Formulación de la solicitud | Retroalimentación cuando se necesita (C2) | A1 | Interfaz y API | Alta (X) | RF-02 |
| F-07 | Enrutamiento por tipo | Un solo agente por dimensión (C4) | Sistema | Orquestador | Alta (X) | RF-03 |
| F-08 | Revisión de estructura y coherencia | Diagnóstico de D1 | A1 | Agente estructural | Alta (X) | RF-04 |
| F-09 | Plan de tarea del hito | Organizar el avance según el programa | A1 | Agente estructural | Media (X) | RF-05 |
| F-10 | Revisión metodológica | Diagnóstico de D2 | A1 | Agente metodológico | Alta (X) | RF-06 |
| F-11 | Propuesta de redacción | Mejorar D3 sin ceder la autoría | A1 | Agente estilístico | Alta (X) | RF-07 |
| F-12 | Búsqueda de evidencia y fuentes | Fuentes dispersas y no verificadas (C1) | A1 | Agente RAG bibliográfico | Alta (X) | RF-08 |
| F-13 | Verificación de referencias del borrador | Referencias inexistentes o mal citadas (K2) | A1 | Agente RAG bibliográfico | Alta (X) | RF-09 |
| F-14 | Recuperación y evaluación de suficiencia | Contenido sin sustento | Sistema | Recuperador y agentes | Alta (X) | RF-10 |
| F-15 | Verificación, reintento y etiquetado | IA sin orientación (C3); alucinación | Sistema | Módulo de verificación | Alta (X) | RF-11 |
| F-16 | Seguimiento del estado de la solicitud | La solicitud tarda decenas de segundos | A1 | API y worker | Alta (X) | RF-22 |
| F-17 | Decisión sobre el resultado | Autoría del caso | A1 | Registro | Alta (X) | RF-12 |
| F-18 | Aporte de una fuente | Vacío del corpus | A1 | Verificación y agente D4 | Media (X) | RF-13 |
| F-19 | Historial del caso | Demostrar el aporte; declarar herramientas | A1 | Registro | Media (X) | RF-14 |
| F-20 | Visualización de evidencias | Comprobar de dónde sale cada afirmación | A1 | Interfaz | Alta (X) | RF-21 |
| F-21 | Gestión del corpus de guías y científico | Recuperar de fuentes verificables | A2 | Gestión de corpus | Alta (X) | RF-15 |
| F-22 | Importación de referencias del artículo O1 | Conformar hasta 28 corpus a tiempo | A2 | Gestión de corpus | Alta (X) | RF-20 |
| F-23 | Exportación del registro | Ficha de registro de métricas | A2 | Exportación | Alta (X) | RF-17 |
| F-24 | Configuración versionada y congelamiento | Un solo artefacto para todos los casos | A2 | Administración | Alta (X) | RF-23 |
| F-25 | Monitoreo técnico y de costos | Disponibilidad, tiempos y presupuesto | A2 | Observabilidad | Media (X) | RF-24 |
| F-26 | Arnés de evaluación técnica | Calcular métricas antes del congelamiento | A2 | Evaluación | Alta (X) | RF-25 |
| F-27 | Eliminación de datos al cierre | Retención mínima (RNF-11) | A2 | Administración | Alta (X) | RF-26 |
| F-28 | Exportar la cita propuesta en RIS o BibTeX | Llevar la fuente al gestor de referencias | A1 | Agente RAG bibliográfico | Baja (opcional) | RF-27 |
| F-29 | Sugerencia de tipo de solicitud | Estudiante que no sabe qué tipo elegir | A1 | Orquestador | Posterior a O2 | No aplica |

## 5.3. Funcionalidades: operación

**Tabla 10. Catálogo de funcionalidades (entradas, proceso, resultado, reglas y dependencias)**
| ID | Entradas | Proceso | Resultado | Reglas | Depende de |
|---|---|---|---|---|---|
| F-01 | Código de cuenta y contraseña | Valida credenciales con hash Argon2, emite sesión en cookie segura, aplica rol | Sesión activa con rol A1 o A2 | RN-12, RN-13, RN-15 | Ninguno |
| F-02 | Código, tipo de autoría, tema | Crea caso, colección personal vacía y cuenta; asocia el corpus del tema | Caso habilitado | RN-12, RN-13 | F-21 |
| F-03 | Sesión A1 | Muestra versión vigente, hito, solicitudes, estado del uso mínimo y guía de cada tipo | Panel | RN-13 | F-04, F-19 |
| F-04 | Archivo .docx e hito | Valida formato y tamaño, guarda archivo, extrae texto y secciones, crea versión | Nueva versión con fecha y hora | RN-09, RN-16 | F-01 |
| F-05 | Versión .docx | Lee estilos de título con python-docx; si no hay títulos, propone selección manual | Lista de secciones y párrafos con identificador | RN-09 | F-04 |
| F-06 | Tipo, alcance (sección, fragmento o consulta) | Valida el alcance según el tipo y lo asocia a la versión vigente | Solicitud en cola | RN-01, RN-07 | F-05 |
| F-07 | Solicitud validada | Tabla fija tipo a agente; registra la asignación | Solicitud asignada a un solo agente | RN-02, RN-03 | F-06 |
| F-08 | Sección, fragmentos del corpus de guías | Recupera criterios; genera diagnóstico estructurado por indicador de D1 | Hallazgos, recomendaciones y fuentes | RN-04, RN-07 | F-14, F-15 |
| F-09 | Hito, estado del borrador, instrucciones del programa | Recupera las instrucciones del hito; genera lista de tareas editable | Plan de tarea | RN-04, RN-07 | F-14, F-15 |
| F-10 | Sección, fragmentos de guías | Genera diagnóstico por indicador de D2 | Hallazgos y recomendaciones | RN-04, RN-07 | F-14, F-15 |
| F-11 | Párrafo de hasta unas 250 palabras | Recupera pautas de redacción; propone una versión de hasta 1.2 veces | Propuesta junto al original con cambios explicados | RN-07 | F-14, F-15 |
| F-12 | Consulta o afirmación | Recupera del corpus del tema y de la colección personal; responde citando fragmentos | Evidencia con referencia asociada | RN-03, RN-04, RN-14, RN-17 | F-14, F-15 |
| F-13 | Citas y lista de referencias de la versión | Extrae referencias con GROBID, consulta por DOI o metadatos, compara y cruza citas con lista | Informe por referencia y correspondencia | RN-10, RN-18 | F-15 |
| F-14 | Consulta del agente, colección permitida | Búsqueda híbrida, reranking, filtro por umbral y juicio de suficiencia | Fragmentos con ID o abstención | RN-03, RN-04 | F-21 |
| F-15 | Propuesta, fragmentos | Seis comprobaciones; un reintento; etiqueta | Resultado etiquetado y verificación registrada | RN-05, RN-06 | F-14 |
| F-16 | Identificador de solicitud | Emite eventos de estado por SSE | Estado visible: asignada, recuperando, generando, verificando, entregada | RN-05 | F-06 |
| F-17 | Resultado y opción elegida | Registra decisión y actualiza contadores | Decisión registrada | RN-08 | F-15 |
| F-18 | PDF o datos bibliográficos, DOI opcional, afirmación | Comprueba existencia, evalúa coherencia, propone cita, indexa si existe | Fuente indexada en la colección personal y nueva recuperación | RN-10, RN-14, RN-17 | F-14, F-15 |
| F-19 | Hito o periodo | Consulta cronológica del registro del caso | Historial | RN-13 | F-17 |
| F-20 | Resultado | Muestra cada fragmento citado con documento, sección, página y enlace de acceso abierto | Evidencia inspeccionable | RN-17 | F-12 |
| F-21 | Documentos, colección | Comprueba acceso abierto, extrae, limpia, segmenta e indexa | Documentos indexados y excluidos registrados | RN-11, RN-14, RN-19 | Ninguno |
| F-22 | .docx del artículo O1 o lista de DOI, tema | Extrae la lista de referencias, resuelve DOI, comprueba acceso abierto, descarga o solicita el PDF, indexa | Corpus del tema con conteo de incluidas y excluidas | RN-14, RN-19 | F-21 |
| F-23 | Casos y periodo | Genera CSV y JSON identificados por código | Archivos para Excel y SPSS | RN-12, RN-20 | F-17 |
| F-24 | Parámetros | Guarda un conjunto de configuración con número de versión; bloquea cambios tras el congelamiento | Configuración vigente y su historial | RN-21 | Ninguno |
| F-25 | Eventos técnicos | Registra errores, latencias, tokens y costo; alerta al superar umbrales | Tablero y alertas | RN-22 | Todos |
| F-26 | Conjunto de 60 solicitudes de prueba con referencia | Ejecuta el flujo completo y calcula las seis métricas | Informe de métricas por versión | RN-21 | Todos |
| F-27 | Confirmación del investigador | Tras exportar, elimina borradores y colecciones personales | Constancia de eliminación | RN-20 | F-23 |
| F-28 | Fuente con DOI | Obtiene RIS o BibTeX por negociación de contenido | Archivo importable en Mendeley | RN-10 | F-12, F-18 |

## 5.4. Funcionalidades adicionales propuestas y su justificación

- **Importación de referencias del artículo O1 (F-22).** La decisión del 3 de noviembre convierte el corpus de cada tema en una derivación del artículo O1. Sin esta herramienta, el investigador tendría que procesar a mano decenas de referencias por tema entre las semanas 2 y 11. Reutiliza el mismo flujo de extracción y verificación de referencias de CU-08, por lo que su costo de desarrollo es bajo. Regla asociada: del artículo O1 solo se usan sus referencias; el artículo mismo no se indexa ni se muestra (RN-19), para no exponer el trabajo de un caso a otro.
- **Visualización de evidencias (F-20).** La confianza percibida es una dimensión del cuestionario; que el estudiante pueda abrir el fragmento y la fuente que respaldan cada afirmación es la forma más directa de sostener esa confianza con evidencia y no con apariencia.
- **Seguimiento de estado (F-16).** Como nada se entrega antes de verificarse (RNF-05), no puede transmitirse el texto mientras se genera. Lo que sí se transmite es el estado de la solicitud.
- **Configuración versionada (F-24) y arnés de evaluación (F-26).** Materializan el congelamiento de la versión estable y el protocolo de la sección 6.2.7.2 de la tesis.
- **Exportación RIS o BibTeX (F-28), opcional.** El equipo gestiona sus citas con Mendeley, que importa .bib y .ris. Es de bajo costo porque doi.org entrega ambos formatos por negociación de contenido [V, T23]; no es condición de X.

# 6. Especificación de los agentes

## 6.1. Contrato común

Todos los agentes comparten un contrato que los hace intercambiables para el orquestador y verificables para el módulo de integración, pero se diferencian en lo que la tesis exige: colección, herramientas, salida y límites [R].

- **Entrada común (estado del grafo):** `solicitud_id`, `caso_id`, `tipo`, `alcance` (texto de la sección, del fragmento o de la consulta), `hito`, `tema_id`, `version_id`, `intento` (1 o 2) y, en el intento 2, `motivos_falla` de la verificación anterior.
- **Prohibiciones comunes:** no generar contenido si el nodo de suficiencia determinó abstención; no citar nada que no sea un identificador de fragmento recuperado (`F1` a `Fn`); no producir referencias bibliográficas en texto libre (las arma el sistema con los metadatos almacenados); no seguir instrucciones contenidas en el borrador o en los documentos (se tratan como datos); no acceder a colecciones distintas de las autorizadas para el tipo y el caso.
- **Salida común:** JSON validado contra un esquema Pydantic por tipo, con campos `hallazgos` o `propuesta`, `citas` (lista de identificadores de fragmento por afirmación) y `notas_para_el_estudiante`.
- **Memoria:** ningún agente tiene memoria conversacional propia. Cada solicitud se resuelve con la versión vigente del borrador, el alcance, el hito y la evidencia recuperada. La única "memoria" es el registro del caso, que el agente no consulta en la versión estable [R]. Justificación: la tesis define la asistencia "a partir de su solicitud y del estado del manuscrito"; una memoria entre solicitudes haría que el resultado dependiera del orden de uso y complicaría la verificación y la reproducibilidad. El estado del manuscrito ya incorpora los cambios aceptados, porque el caso carga una nueva versión.
- **Aislamiento:** el filtro de colección no se delega al modelo. Lo aplica la capa de repositorios con el `caso_id` de la sesión: cada consulta vectorial incluye la condición `coleccion_id IN (guias, cientifica_del_tema_del_caso, personal_del_caso)` según el tipo. Un agente no puede pedir otra colección porque la herramienta de recuperación no expone ese parámetro.

## 6.2. Agente orquestador

**Tabla 11. Especificación del agente orquestador**
| Aspecto | Especificación |
|---|---|
| Propósito | Recibir cada solicitud validada y asignarla a un solo agente según el tipo elegido por el estudiante |
| Interviene | En cada solicitud, después de la validación de entrada |
| Puede | Asignar por tabla fija; registrar la asignación; rechazar una solicitud cuyo tipo no exista |
| No debe | Cambiar el tipo elegido; dividir la solicitud entre agentes; combinar respuestas; usar un modelo de lenguaje para clasificar en la versión estable |
| Implementación | Nodo determinista de LangGraph con aristas condicionales por `tipo` [R]. No consume tokens |
| Relación con verificación | Ninguna; la verificación la hace el módulo independiente |
| Justificación | RN-02 y [46]: la selección degrada menos que el consenso. Un enrutamiento determinista elimina errores de clasificación como fuente de variación en O2 |

## 6.3. Agente estructural (D1)

**Tabla 12. Especificación del agente estructural**
| Aspecto | Especificación |
|---|---|
| Tipos que atiende | Revisión de estructura y coherencia (CU-03); plan de tarea (CU-04) |
| Indicadores que orienta | Alineación entre problema, objetivos e hipótesis; secuencia lógica discursiva; cohesión entre apartados |
| Interviene | Cuando el estudiante elige uno de sus dos tipos |
| Información que necesita | Sección o secciones indicadas; títulos del borrador; hito; para el plan, las instrucciones del hito |
| Colección | Corpus de guías (incluye instrucciones y sílabo del programa, guía de investigación, artículos metodológicos sobre IMRaD) |
| Herramientas | `recuperar(coleccion="guias")`; `estructura_borrador()` que devuelve el árbol de títulos y la ubicación de problema, objetivos e hipótesis detectados en la versión |
| Puede | Señalar movimientos retóricos ausentes, desalineaciones, saltos lógicos y problemas de cohesión, con ubicación en el texto; proponer acciones concretas; armar un plan de tareas editable |
| No debe | Reescribir párrafos o secciones; evaluar metodología o estilo; calificar con puntajes |
| Salida (revisión) | `{hallazgos:[{indicador, ubicacion, descripcion, severidad, recomendacion, citas:[F..]}], fortalezas:[...], notas}` |
| Salida (plan) | `{hito, tareas:[{orden, tarea, criterio_de_logro, citas:[F..]}], notas}` |
| Verificación aplicable | Formato; ausencia de reescritura (ningún fragmento de salida mayor de 40 palabras que no sea cita del texto del estudiante [S, calibrar]); citas válidas; fidelidad |

## 6.4. Agente metodológico (D2)

**Tabla 13. Especificación del agente metodológico**
| Aspecto | Especificación |
|---|---|
| Tipo que atiende | Revisión metodológica (CU-05) |
| Indicadores que orienta | Justificación del diseño metodológico; validez de técnicas e instrumentos descritos; precisión en el análisis de datos |
| Información que necesita | Sección de métodos o resultados indicada; objetivos e hipótesis detectados en la versión, para comprobar coherencia entre diseño y análisis |
| Colección | Corpus de guías (artículos metodológicos y guía de investigación) |
| Herramientas | `recuperar(coleccion="guias")`; `estructura_borrador()`; `lista_de_comprobacion(diseno)` que devuelve criterios mínimos según el tipo de diseño declarado (experimental, cuasiexperimental, correlacional, descriptivo), almacenados como documento del corpus de guías |
| Puede | Detectar inconsistencias entre diseño, muestra, instrumentos y pruebas estadísticas; preguntar por información faltante; recomendar qué reportar |
| No debe | Inventar datos, resultados o valores estadísticos; reescribir; prescribir pruebas sin sustento en el corpus |
| Salida | `{hallazgos:[{indicador, ubicacion, descripcion, severidad, recomendacion, citas:[F..]}], preguntas_al_estudiante:[...], notas}` |
| Verificación aplicable | Formato; ausencia de reescritura; ningún número o resultado que no esté en el texto del estudiante o en un fragmento citado; fidelidad |

## 6.5. Agente estilístico (D3)

**Tabla 14. Especificación del agente estilístico**
| Aspecto | Especificación |
|---|---|
| Tipo que atiende | Propuesta de redacción (CU-06) |
| Indicadores que orienta | Registro formal; fluidez discursiva y precisión léxica; corrección gramatical y claridad sintáctica |
| Información que necesita | Un párrafo de hasta unas 250 palabras seleccionado de la versión |
| Colección | Corpus de guías (pautas de redacción científica y del manual de estilo) |
| Herramientas | `recuperar(coleccion="guias")`; `contar_palabras()` |
| Puede | Proponer una versión del mismo párrafo, de hasta 1.2 veces su extensión, conservando el contenido; explicar cada cambio con la pauta que lo justifica |
| No debe | Añadir ideas, datos o citas nuevas; cambiar el sentido; trabajar sobre más de un párrafo |
| Salida | `{original, propuesta, cambios:[{tipo, antes, despues, razon, citas:[F..]}], notas}` |
| Verificación aplicable | Límite de entrada (antes de generar) y de salida (1.2 veces); conservación del contenido: el evaluador comprueba que la propuesta no introduce afirmaciones ausentes en el original; citas válidas para las razones |

## 6.6. Agente RAG bibliográfico (D4)

**Tabla 15. Especificación del agente RAG bibliográfico**
| Aspecto | Especificación |
|---|---|
| Tipos que atiende | Búsqueda de evidencia y fuentes (CU-07); verificación de referencias (CU-08); además indexa las fuentes aportadas confirmadas (CU-12) |
| Indicadores que orienta | Aplicación de la norma de citación; calidad de las fuentes; verificabilidad de las referencias |
| Colecciones | CU-07: corpus científico del tema del caso y colección personal del caso. CU-08: bases bibliográficas externas |
| Herramientas | `recuperar(coleccion="cientifica" o "personal")`; `extraer_referencias(version)` con GROBID; `extraer_citas_en_texto(version, estilo)`; `buscar_doi(doi)` en Crossref; `buscar_metadatos(titulo, autores, anio)` en Crossref y OpenAlex; `estado_acceso_abierto(doi)` en Unpaywall; `formatear_cita(doi, estilo)` por doi.org; `indexar_fuente(caso_id, fuente)` |
| Puede | Responder con evidencia citando fragmentos; recomendar solo fuentes de acceso abierto; informar el estado de cada referencia; señalar citas sin entrada en la lista y entradas no citadas; proponer la cita en el estilo configurado |
| No debe | Escribir referencias de memoria; recomendar fuentes cerradas; declarar inexistente una referencia cuando un servicio externo no respondió; indexar en colecciones compartidas |
| Salida (evidencia) | `{respuesta:[{afirmacion, citas:[F..]}], fuentes:[{documento_id}], evidencia_divergente:[...], notas}` (las referencias se arman desde la base de datos, no desde el texto del modelo) |
| Salida (verificación) | `{referencias:[{indice, texto_original, estado: verificada o con_discrepancias o no_localizada o no_comprobable, metodo: doi o metadatos, discrepancias:[campo, valor_borrador, valor_fuente], doi_encontrado}], citas_sin_entrada:[...], entradas_no_citadas:[...]}` |
| Particularidad | Gran parte de CU-08 es determinista: extracción, consulta, comparación y cruce de citas. El modelo solo redacta, si se configura, una explicación breve de cada discrepancia. Esto reduce el riesgo de alucinación en la dimensión más sensible [R] |

## 6.7. Módulo de integración y verificación

**Tabla 16. Especificación del módulo de integración y verificación**
| Aspecto | Especificación |
|---|---|
| Propósito | Comprobar cada propuesta antes de entregarla, comprobar la existencia de toda fuente, etiquetar, entregar y registrar |
| Comprobaciones (orden) | 1) esquema del tipo; 2) límites de extensión y ausencia de reescritura; 3) citas solo a fragmentos recuperados; 4) existencia de fuentes (DOI en Crossref o doi.org; si no, metadatos con título, al menos un autor y año); 5) acceso abierto de fuentes recomendadas; 6) fidelidad respuesta-fuente |
| Fidelidad | Un modelo evaluador con rol e instrucción propios divide la salida en afirmaciones y clasifica cada una como respaldada, no respaldada o contradicha por los fragmentos citados. Valor = respaldadas / total. Umbral inicial para superar la verificación: 0.90, igual al criterio de aceptación de la tesis [R, calibrar] |
| Reintento | Si alguna comprobación falla en el intento 1, devuelve al agente los motivos y solicita un único reintento; si vuelve a fallar, etiqueta "Con advertencias" y entrega la lista de comprobaciones fallidas |
| Abstención | Recibe la decisión de abstención del agente, no genera nada y etiqueta "Sin evidencia suficiente" |
| Independencia | Código separado de los agentes; no comparte instrucciones con ellos; puede usar un modelo distinto [R] |
| Salida | `{etiqueta, verificaciones:[{intento, formato_ok, limites_ok, citas_ok, n_fuentes_citadas, n_fuentes_confirmadas, metodo, acceso_abierto_ok, fidelidad, superada}], advertencias:[...]}` |

## 6.8. Cómo se evita que un agente sea "un chatbot con otra instrucción"

La diferenciación es estructural y comprobable: cada agente tiene (a) un conjunto de tipos que atiende y ningún otro, (b) una colección y herramientas propias, (c) un esquema de salida distinto, (d) reglas de verificación específicas y (e) un conjunto de casos de prueba propio con borradores que contienen errores introducidos a propósito en su dimensión (sección 21). La prueba de aceptación de cada agente es que detecte los errores de su dimensión y no comente los de otras.

# 7. Flujos principales y alternativos

## 7.1. Flujo principal de una solicitud de asistencia

1. El caso inicia sesión y carga la versión vigente del borrador (CU-01). El sistema detecta las secciones.
2. El caso elige uno de los seis tipos e indica el alcance: una sección, un párrafo o una consulta (CU-02).
3. El sistema valida el alcance (por ejemplo, que el párrafo no supere el límite) y encola la solicitud. La interfaz muestra el estado.
4. El orquestador asigna la solicitud al agente que corresponde al tipo y lo registra.
5. El agente recupera evidencia solo de su colección autorizada y evalúa la suficiencia en dos pasos.
6. Si la evidencia es suficiente, el agente genera una propuesta estructurada que cita identificadores de fragmentos.
7. El módulo de integración y verificación aplica las seis comprobaciones; si falla, pide un único reintento.
8. El módulo etiqueta el resultado y lo entrega; la interfaz muestra la propuesta, la etiqueta y las evidencias navegables.
9. El caso acepta, modifica o rechaza (CU-11); el sistema registra la decisión y actualiza los contadores.
10. Si aceptó o modificó, el caso incorpora el cambio en su procesador de textos y, cuando lo decida, carga una nueva versión.

*[Figura 1. Diagrama de secuencia de una solicitud de asistencia: ver diagramas Mermaid de la Fase 1]*

## 7.2. Escenarios alternativos

**Tabla 17. Comportamiento del sistema en escenarios alternativos**
| Escenario | Comportamiento | Estado / etiqueta | Registro |
|---|---|---|---|
| Solicitud "clasificada" incorrectamente | No hay clasificación automática: el tipo lo eligió el caso. Si el contenido no corresponde al tipo (por ejemplo, pide revisar redacción en una revisión metodológica), el agente responde solo dentro de su dimensión y lo indica en `notas`, con sugerencia del tipo adecuado | Etiqueta normal | Solicitud y nota |
| Solicitud ambigua (consulta de CU-07 sin afirmación clara) | La validación pide precisar antes de encolar, con un ejemplo de consulta bien formulada. No se consume el modelo | No encolada | Evento de validación |
| Solicitud de más de una dimensión | El caso formula solicitudes separadas. La interfaz ofrece "crear otra solicitud con el mismo alcance" para hacerlo con un clic | Una por solicitud | Una por solicitud |
| Sin información relevante en el corpus | Abstención; se ofrece aportar una fuente (CU-12) | "Sin evidencia suficiente" | Abstención y elección posterior |
| Fuente no verificable (no se confirma existencia) | En CU-07 la fuente no se entrega como recomendada y la verificación falla; en CU-08 se informa "no localizada"; en CU-12 no se indexa | Según caso | Verificación con método y resultado |
| Servicio bibliográfico caído | No se declara inexistente; se marca "no comprobable" y se informa que la verificación no pudo completarse | "Con advertencias" si afecta a la propuesta | Error externo |
| Error durante la ejecución de un agente o del proveedor LLM | Reintento técnico automático con espera exponencial (hasta 2 veces, distinto del reintento de verificación); si persiste, la solicitud queda "no atendida" y el caso puede reenviarla | No atendida | Error con tipo y duración |
| Respuesta que no supera la verificación | Un único reintento con los motivos; si falla de nuevo, se entrega con la lista de comprobaciones fallidas | "Con advertencias" | Dos verificaciones |
| Reintento de generación | Incluye los motivos de falla en la instrucción; usa los mismos fragmentos; no repite la recuperación | Según resultado | Intento 2 |
| Fuera del alcance del sistema (por ejemplo, pedir que redacte la introducción completa o una consulta ajena al artículo) | La validación lo detecta por reglas (longitud, patrones como "redacta", "escribe la sección") y, en la consulta libre, por un clasificador barato de pertinencia; se responde con lo que el sistema sí puede hacer | No atendida, motivo "fuera de alcance" | Evento con motivo [propuesta: atributo `motivo` en Solicitud] |
| Documento .docx dañado o con macros | Se rechaza la carga (CP-02) | Sin versión | Evento de validación |
| Evidencia divergente entre fragmentos | El agente la presenta como tal en `evidencia_divergente`, con ambas fuentes; no elige por el estudiante | Etiqueta normal | Resultado |

## 7.3. Flujo del investigador: conformación del corpus de un tema

1. Al registrarse un tema en O1, el investigador crea su colección científica.
2. Desde el Avance 2, carga el .docx del artículo O1 (o una lista de DOI); el sistema extrae la lista de referencias, resuelve cada DOI y consulta su estado de acceso abierto.
3. Para cada referencia de acceso abierto, el sistema descarga el PDF desde la ubicación legal informada por Unpaywall cuando el enlace es directo; si no lo es, la marca "pendiente de PDF" para que el investigador lo suba.
4. Indexa las incluidas, registra las excluidas por no tener acceso abierto y muestra el resumen por tema.
5. En la semana 11 se cierra la carga y se ejecuta el arnés de evaluación técnica con el corpus definitivo, sin cambiar el código.

## 7.4. Grafo de orquestación

*[Figura 2. Grafo de estados de la orquestación (LangGraph): ver diagramas Mermaid de la Fase 1]*

# 20. Plan de implementación

El plan respeta el orden de bloques de la tesis (corpus y agente RAG bibliográfico; luego D1, D2 y D3; al final orquestador, verificación y flujo completo) y su calendario: 16 sprints de dos semanas desde noviembre de 2026 hasta el congelamiento en la semana 8 de 2027-1. Dentro de cada bloque se ordenan las tareas técnicas por dependencia. Las fechas son aproximadas y se ajustan al calendario académico.

**Tabla 44. Etapas y sprints**
| Etapa | Sprints (fechas aprox.) | Objetivo | Actividades y componentes | Herramientas | Dependencias | Entregables | Criterio de terminado |
|---|---|---|---|---|---|---|---|
| 0. Preparación | Antes del sprint 1 (nov. 2026) | Entorno y cuentas listos | Repositorio privado, estructura de carpetas, Docker Compose con PostgreSQL y pgvector, integración continua con formato, linter y pruebas; cuenta del proveedor con tope de gasto; correo institucional del proyecto; clave de OpenAlex; plantilla de instrucciones de los agentes | Git, GitHub, Docker, Claude Code | Ninguna | Repositorio que compila y pasa CI vacío | `docker compose up` levanta la base y una API de salud |
| Bloque 1 | S1 (16 nov.) | Núcleo de datos y acceso | Modelo de datos (15 tablas) con migraciones; autenticación y roles (RF-18); gestión de casos (RF-16) | FastAPI, SQLAlchemy, Alembic, Argon2 | Etapa 0 | API de cuentas y casos | CP-22 superado; pruebas de autorización por rol |
| Bloque 1 | S2 (30 nov.) | Borrador y versiones | Carga y validación .docx; versiones; detección de secciones (RF-01, RF-02 parcial); SPA con inicio de sesión, panel y carga | python-docx, React, Vite | S1 | Primera interfaz usable | CP-01, CP-02 superados |
| Bloque 1 | S3 (14 dic.) | Ingesta del corpus | Docling, limpieza, segmentación IMRaD, bge-m3, índices HNSW y léxico; corpus provisional con artículos de acceso abierto en español (RF-15) | Docling, bge-m3, pgvector | S1 | Colecciones indexadas | CP-21; consulta de prueba devuelve fragmentos con metadatos |
| Bloque 1 | S4 (11 ene. 2027) | Integraciones bibliográficas | Clientes de Crossref, doi.org, Unpaywall, OpenAlex y GROBID con limitador y caché; importador de referencias del artículo O1 (RF-20) | httpx, GROBID | S3 | Importación por tema | Importa un .docx de prueba con al menos 20 referencias y reporta incluidas y excluidas |
| Bloque 1 | S5 (25 ene.) | Recuperación y agente D4 (evidencia) | Recuperador híbrido, RRF, reranking, suficiencia en dos pasos (RF-10); adaptador LLM; agente D4 para CU-07 sin orquestador (RF-08) | LangGraph, bge-reranker-v2-m3, SDK del proveedor | S3, S4 | Búsqueda de evidencia funcional | CP-05 y CP-11 superados |
| Bloque 1 | S6 (8 feb.) | Agente D4 (verificación de referencias) | Extracción de citas y lista, consulta por DOI y metadatos, informe (RF-09) | GROBID, Crossref, OpenAlex | S4, S5 | **MVP técnico**: carga, evidencia y verificación de referencias | CP-12, CP-13 superados; casos del bloque sin regresión |
| Bloque 2 | S7 (22 feb.) | Corpus de guías y D1 | Conformar el corpus de guías; agente estructural, revisión (RF-04) | Docling | S5 | Diagnóstico D1 | CP-08 para D1 |
| Bloque 2 | S8 (8 mar.) | Plan de tarea y prueba comparativa | Plan de tarea (RF-05); prueba comparativa de modelos con 30 solicitudes; decisión de proveedor y modelos | DeepEval, hoja de valoración | S7 | Informe de la prueba comparativa | Proveedor elegido y nombrado para el consentimiento |
| Bloque 2 | S9 (22 mar.) | Agente D2 | Agente metodológico y listas de comprobación por diseño (RF-06) | LangGraph | S7 | Diagnóstico D2 | CP-08 para D2 |
| Bloque 2 | S10 (5 abr.) | Agente D3 | Agente estilístico con límites (RF-07) | LangGraph | S7 | Propuesta comparada | CP-09, CP-10; bloque 1 sin regresión |
| Bloque 3 | S11 (19 abr.) | Orquestación y cola | Grafo completo con validación y enrutamiento (RF-02, RF-03); cola en PostgreSQL; worker; SSE (RF-22) | LangGraph, checkpointer PostgreSQL | Bloques 1 y 2 | Flujo de extremo a extremo | CP-03, CP-04, CP-07 |
| Bloque 3 | S12 (3 may.) | Verificación completa | Seis comprobaciones, evaluador de fidelidad, reintento y etiquetas (RF-11); medición de latencias | Ragas (como referencia del método) | S11 | Resultados etiquetados | CP-06, PI-04 |
| Bloque 3 | S13 (17 may.) | Decisión, aporte e historial | RF-12, RF-13, RF-14, RF-21; calibración de tau, N, ventana y k con el corpus provisional | Arnés | S12 | Ciclo completo de una solicitud | CP-14 a CP-20; parámetros calibrados |
| Bloque 3 | S14 (31 may.) | Administración y evaluación | Exportación (RF-17), configuración versionada (RF-23), monitoreo y costos (RF-24), arnés (RF-25), purga (RF-26) | Ragas, DeepEval | S13 | Paquete de exportación y primer informe de métricas | CP-23, PI-05, PI-08 |
| Bloque 3 | S15 (14 jun.) | Pruebas del sistema integrado y despliegue | PI-01 a PI-09; prueba de carga con 28 sesiones; accesibilidad y seguridad; despliegue en el VPS; respaldo y restauración | Playwright, herramienta de carga, Caddy | S14 | Versión candidata | Todas las PI superadas en el servidor |
| Reserva | S16 (28 jun., semana 8 de 2027-1) | Congelamiento | Corrección de defectos; métricas con corpus provisional dentro de umbrales; congelamiento | Todas | S15 | **Versión estable X** | Las tres condiciones del 6.2.7.2 de la tesis |
| Operación | Semanas 8 a 22 de 2027-1 | Prueba piloto, carga del corpus definitivo y O2 | Piloto del cuestionario (semanas 8 y 9); carga progresiva desde el Avance 2 y cierre en la semana 11; métricas con corpus definitivo; soporte durante O2 solo con correcciones críticas | Monitoreo | X | Registro de O2 | Exportación final y purga (RF-26) |

## 20.1. Producto mínimo viable y funcionalidades posteriores

- **MVP técnico (fin del sprint 6):** inicio de sesión, carga de versiones, corpus provisional indexado, búsqueda de evidencia con abstención y verificación de referencias. Sirve para validar temprano la parte más riesgosa (recuperación y bibliografía) y para mostrar avances al asesor.
- **Versión estable X (sprint 16):** todos los casos de uso CU-01 a CU-16 y los requisitos RF-01 a RF-26. No es un MVP: es el artefacto completo que exige la tesis, porque todos los casos de O2 deben usar el mismo sistema.
- **Después de O2 o fuera de X:** exportación RIS o BibTeX (RF-27) si no se alcanzó antes; sugerencia no vinculante del tipo de solicitud (F-29); observabilidad con Langfuse autoalojado; seguridad a nivel de filas como segunda barrera; panel de estadísticas para el investigador más allá de la exportación.

## 20.2. Método de trabajo con Claude Code

Como el equipo no programa, cada historia se implementa con Claude Code a partir de esta especificación, siguiendo un ciclo fijo: (1) se le entrega la historia, sus requisitos y sus casos de prueba; (2) primero escribe las pruebas; (3) implementa hasta que pasen; (4) la integración continua ejecuta todas las pruebas anteriores; (5) el equipo revisa el comportamiento en la interfaz con los casos de prueba de la tesis. Las pruebas automáticas son la garantía de que un cambio posterior no rompe lo construido.

# 21. Estrategia de pruebas

**Tabla 45. Niveles de prueba**
| Nivel | Qué comprueba | Herramientas | Relación con la tesis |
|---|---|---|---|
| Unitarias | Servicios, validadores, segmentador, comparación de metadatos, cálculo de etiquetas | pytest | Base de CP-01 a CP-23 |
| Contrato con servicios externos | Clientes de Crossref, doi.org, Unpaywall, OpenAlex, GROBID y proveedor LLM con respuestas grabadas; simulación de caídas y límites | pytest con respuestas grabadas | CP-07, CP-13 |
| Integración | API con base de datos real en contenedor; repositorios con filtro por caso | pytest, Docker | CP-20, PI-06 |
| Comportamiento de agentes | Detecta los errores introducidos de su dimensión; no reescribe; no inventa datos; respeta límites | DeepEval (G-Eval y reglas), borradores de prueba | CP-08 a CP-11 |
| Evaluación RAG | Seis métricas de la ficha sobre 60 solicitudes con referencia; concordancia con revisión humana del 20 al 30 % | Ragas, arnés RF-25 | 6.2.7.2 |
| Extremo a extremo | Flujos completos desde la interfaz | Playwright | PI-01 a PI-07 |
| Carga | 28 sesiones simultáneas con los seis tipos | Herramienta de carga (por definir) | PI-09 |
| Seguridad | Autorización por ruta, cargas maliciosas, secretos, dependencias | pytest, escáner de dependencias y de secretos | RNF-15, RNF-16 |
| Accesibilidad | Contraste, foco, etiquetas, teclado | Revisión automática y manual | RNF-18 |
| Usabilidad | Tarea guiada en la prueba piloto | Observación y cuestionario piloto | RNF-17 |

Datos de prueba, según la tesis: borradores elaborados por el equipo y artículos de acceso abierto en español con errores introducidos a propósito en estructura, método, redacción y referencias, de modo que se sabe de antemano qué debe detectar cada agente; casos ficticios identificados por código; ningún participante de la muestra interviene antes de O2. Para la verificación de referencias se mezclan referencias reales, con errores y fabricadas a propósito.

El criterio de terminado de cada sprint es el de la tesis: superar los casos de prueba del incremento, mantener superados los anteriores y registrar los resultados. La integración continua lo automatiza.

# 22. Validación y relación con la investigación

## 22.1. Funcionalidades relevantes para la intervención X

Todas las funcionalidades F-01 a F-27 forman parte de X porque materializan CU-01 a CU-16 o los controles que la tesis exige (congelamiento, exportación, aislamiento). La única que se ofrece de forma opcional es F-28, y la sugerencia de tipo (F-29) se excluye de X para no introducir un confusor.

## 22.2. Origen de los datos de cada indicador

**Tabla 46. Indicadores, instrumentos y fuente de datos**
| Indicador | Instrumento | Medición | Fuente de datos |
|---|---|---|---|
| 12 indicadores de D1 a D4 (rúbrica analítica, 1 a 5) | Rúbrica | O1 y O2 | **Externa**: evaluadores ciegos sobre los artículos entregados. El sistema no la almacena ni la calcula |
| Verificabilidad de las referencias (indicador de D4 en la rúbrica) | Rúbrica | O1 y O2 | Externa. Los evaluadores pueden usar un procedimiento equivalente, pero no el sistema, para no revelar la medición de procedencia |
| Facilidad de uso, claridad de las salidas, utilidad percibida | Cuestionario | O2 | Externa: formulario fuera del sistema, un integrante por caso |
| Confianza en la exactitud, disposición a incorporar, necesidad percibida de verificación | Cuestionario | O2 | Externa |
| Cobertura del corpus documental | Ficha de métricas | O2 | **Sistema**: estado de las solicitudes y abstenciones |
| Precisión contextual de los fragmentos | Ficha de métricas | O2 | Sistema: fragmentos recuperados con pertinencia evaluada por el modelo evaluador y muestra humana |
| Completitud de la recuperación | Ficha de métricas | O2 (y conjunto de prueba) | Sistema: juicio del evaluador en O2; evidencia de referencia en el conjunto de prueba |
| Fidelidad respuesta-fuente | Ficha de métricas | O2 | Sistema: verificación final de cada resultado |
| Relevancia de la respuesta | Ficha de métricas | O2 | Sistema: evaluación sobre resultado y solicitud |
| Tasa de referencias no verificables | Ficha de métricas | O2 | Sistema: fuentes citadas frente a confirmadas |
| Propuestas aceptadas, modificadas y rechazadas; uso mínimo por hito | Registro (descriptivo) | O2 | Sistema |
| Herramientas empleadas en cada artículo | Declaración (no es instrumento) | O1 y O2 | Externa: el caso puede apoyarse en su historial (RF-14) |

## 22.3. Datos por momento del diseño

- **O1:** el sistema no lo usan los casos. Solo participa el investigador, que importa las referencias de cada artículo O1 para conformar el corpus del tema (RF-20). El artículo O1 no se almacena ni se indexa (RN-19), y su calificación se hace fuera del sistema.
- **Semana 11:** cierre del corpus definitivo y cálculo de métricas técnicas con el arnés; no se modifica el código.
- **O2:** el sistema registra todo lo necesario para la ficha de métricas y los contadores; la rúbrica y el cuestionario se aplican fuera.
- **Cierre:** exportación final, entrega al análisis en Excel y SPSS, y purga de borradores y colecciones personales (RF-26).

## 22.4. Cómo no confundir registros técnicos con resultados de los instrumentos

- **Dos almacenes separados:** el sistema guarda solo datos de uso y métricas técnicas; la rúbrica, el cuestionario y la tabla que relaciona códigos con personas y con códigos de evaluación ciega se guardan en el repositorio de acceso restringido de la investigación, fuera del sistema.
- **Dos espacios de códigos:** el código del caso en el sistema no es el código que ven los evaluadores en los artículos; la correspondencia la custodia el investigador.
- **Dos tipos de tablas en la exportación:** el registro metodológico (versiones, solicitudes, resultados, verificaciones, decisiones) y el evento técnico (latencias, tokens, errores, costos) salen en archivos distintos, con un diccionario de datos que indica qué alimenta la ficha de métricas.
- **Las métricas técnicas no son hipótesis:** se describen como evaluación del artefacto, como establece el apartado 6.1.6 de la tesis.

# 23. Riesgos técnicos y recomendaciones

**Tabla 47. Registro de riesgos**
| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Corpus pequeño en temas cuyo artículo O1 tiene pocas referencias de acceso abierto | Alta | Alto | Importación temprana desde el Avance 2; aviso al investigador si un tema queda por debajo de un mínimo; aporte de fuentes; reportar la cobertura por tema como limitación |
| Plazo corto entre el fin de O1 (semana 10) y O2 (semana 12) para cerrar 28 corpus | Media | Alto | Carga progresiva; importador automático; la semana 11 solo completa y mide |
| Cambio de precio, de condiciones o retiro del modelo durante O2 | Baja | Alto | Identificador de modelo fijo con fecha (RN-24); revisar el calendario de retiros del proveedor antes de O2; adaptador para cambiar de proveedor como plan de contingencia, documentado como corrección crítica |
| Límites de tasa de Crossref u OpenAlex en momentos de alta demanda | Media | Medio | Caché por DOI; limitador por servicio; estado "no comprobable" en lugar de "inexistente" |
| Servidor gratuito reclamado o sin capacidad | Media | Alto | VPS de pago para O2; Oracle solo para demostración |
| Inyección de instrucciones desde borradores o PDF | Media | Medio | RN-23; herramientas sin escritura; verificación de límites; pruebas con documentos maliciosos |
| Fuga de datos entre casos | Baja | Muy alto | Filtro por caso en repositorios; pruebas de autorización en CI; RLS opcional |
| Juez LLM con sesgos al medir fidelidad y relevancia | Media | Medio | Revisión humana del 20 al 30 % y reporte de concordancia, como prevé la tesis |
| Variabilidad de formato de los .docx de los estudiantes (sin estilos de título, referencias manuales o con campos de Mendeley) | Alta | Medio | Selección manual de secciones de respaldo; GROBID sobre el texto de la lista; pruebas con borradores reales anonimizados del equipo |
| Dependencia del asistente de programación en un equipo que no programa | Media | Alto | Pruebas automáticas obligatorias; especificación detallada por historia; CI; revisión de comportamiento con casos de prueba |
| Licencias de las versiones de acceso abierto | Media | Medio | Mostrar fragmentos breves y enlazar a la fuente; no redistribuir PDF; consultar a la universidad |
| GROBID o modelos sin imagen para ARM | Media | Bajo | Usar VPS x86 en producción |
| Costo mayor por tokenizador o por reintentos | Media | Bajo | Columna de sensibilidad; tope de gasto; caché de instrucciones |
| Retraso de sprints por carga académica | Alta | Alto | Sprint de reserva; MVP técnico al final del bloque 1 para detectar desvíos temprano |

# 24. Decisiones pendientes y recomendaciones

**Tabla 48. Preguntas pendientes con recomendación**
| N.° | Decisión | Recomendación | Bloquea |
|---|---|---|---|
| 1 | Proveedor y modelos del LLM | API de Claude (Sonnet 5.5 para agentes, Haiku 5.5 para auxiliares y evaluador), confirmada con la prueba comparativa del sprint 8; alternativa GPT-5 mini | Consentimiento informado y comité de ética |
| 2 | Alojamiento durante la prueba piloto y O2 | VPS de pago x86 de 4 vCPU y 8 GB, o servidor de la universidad si lo facilita | Sprint 15 |
| 3 | Norma de citación del programa | La que indiquen las instrucciones del programa; el sistema la configura como estilo CSL; si no hay una, IEEE para todos los casos en O1 y O2 | Agente D4 (sprint 6) |
| 4 | Reemplazar Streamlit por React | Aceptar; Streamlit queda solo para tableros internos si se desea | Sprint 2 |
| 5 | Reemplazar Chroma y SQLite por PostgreSQL con pgvector | Aceptar | Sprint 1 |
| 6 | Requisitos complementarios RF-18 a RF-27, RNF-15 a RNF-24 y RN-15 a RN-24 | Aceptarlos e incorporarlos a la Metodología Marco con su origen | Actualización de la tesis |
| 7 | Atributo `motivo` y estado "fuera de alcance" en Solicitud | Aceptar como extensión menor del modelo de datos | Sprint 1 |
| 8 | Contexto de memoria de los agentes | Sin memoria entre solicitudes en X; solo versión vigente, alcance e hito | Sprint 5 |
| 9 | Sugerencia automática del tipo de solicitud | No incluirla en X; evaluarla después de O2 | Ninguno |
| 10 | Corregir en la tesis: sorteo frente a tema libre (6.1.2), duraciones de 22 y 6 semanas, "ocho fases" y RN-01 a RN-13 en la Tabla 1 | Unificar con las decisiones vigentes | Revisión del asesor |
| 11 | Tiempos de respuesta objetivo (RNF-12) | Percentil 95 de 60 s por solicitud y 120 s por verificación de 40 referencias, a confirmar en el sprint 12 | Sprint 12 |
| 12 | Límites de tamaño de archivos (RN-16) | .docx hasta 15 MB; PDF hasta 25 MB y 60 páginas | Sprint 2 |
| 13 | Criterio de licencia para almacenar textos de acceso abierto | Indexar y mostrar fragmentos breves con enlace; no redistribuir PDF; confirmar con la universidad | Sprint 3 |
| 14 | Quién sube los PDF que Unpaywall no enlaza directamente | El investigador, en la vista "pendientes de PDF" | Sprint 4 |
| 15 | Correo institucional para Crossref y Unpaywall y cuenta de OpenAlex | Crear una cuenta de proyecto (no personal) para ambos | Etapa 0 |
| 16 | Tope de gasto mensual en el proveedor | USD 60 por mes durante el desarrollo y USD 100 por mes durante O2, con alertas al 50 y al 80 % | Etapa 0 |
| 17 | Uso de plataformas de trazas en la nube | Solo en desarrollo con datos ficticios; en producción, registro propio | Sprint 11 |
| 18 | Duración de la sesión y uso simultáneo por parejas | Sesión de 8 horas con expiración por 60 minutos de inactividad; dos sesiones simultáneas por cuenta | Sprint 1 |

# 25. Fuentes técnicas consultadas

Fuentes consultadas entre el 3 y el 4 de noviembre de 2026. Las marcadas como secundarias resumen una página oficial que no pudo leerse directamente; deben confirmarse en la fuente oficial antes de contratar.

- [T1] LangChain, "LangGraph persistence" (documentación oficial): https://docs.langchain.com/oss/python/langgraph/persistence ; anuncio de la versión 1.0: https://forum.langchain.com/t/langchain-1-0-alpha-feedback-wanted/1436
- [T2] Microsoft, repositorio de AutoGen (modo de mantenimiento y Microsoft Agent Framework): https://github.com/microsoft/autogen
- [T3] CrewAI, repositorio y licencia MIT: https://github.com/crewAIInc/crewAI ; foro oficial: https://community.crewai.com/t/crewais-open-source-status-and-associated-costs/4549
- [T4] LlamaIndex, documentación de agentes y Workflows: https://developers.llamaindex.ai/python/framework/use_cases/agents/index.md
- [T5] Anthropic, "Pricing", Claude Platform Docs: https://platform.claude.com/docs/en/about-claude/pricing
- [T6] Anthropic, Commercial Terms of Service: https://www.anthropic.com/legal/commercial-terms (la retención de 30 días proviene de resúmenes de su centro de privacidad; confirmar en la versión vigente)
- [T7] Secundaria: precios y políticas de la API de OpenAI según https://www.developersdigest.tech/models/gpt-5-mini y https://www.developersdigest.tech/models/data-retention/openai ; oficial: https://openai.com/api/pricing
- [T8] Google, Gemini API billing y pricing: https://ai.google.dev/gemini-api/docs/billing , https://ai.google.dev/pricing ; precio de Gemini 3 Flash según https://benchlm.ai/google/api-pricing (secundaria)
- [T9] Groq, límites del plan gratuito: https://console.groq.com/docs/rate-limits (lectura secundaria en https://benchlm.ai/md/free-tier/groq.md y https://www.developersdigest.tech/models/free-api/groq)
- [T10] Mistral AI, centro de ayuda sobre uso de datos para entrenamiento: https://help.mistral.ai/en/articles/455207
- [T11] DeepSeek, política de privacidad: https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html
- [T12] BAAI, ficha de bge-m3: https://huggingface.co/BAAI/bge-m3
- [T13] Qwen, ficha de Qwen3-Embedding-0.6B: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B ; informe técnico: https://arxiv.org/pdf/2506.05176v3
- [T14] BAAI, ficha de bge-reranker-v2-m3: https://huggingface.co/BAAI/bge-reranker-v2-m3
- [T15] pgvector, repositorio oficial: https://github.com/pgvector/pgvector
- [T16] Chroma, documentación y repositorio: https://docs.trychroma.com , https://github.com/chroma-core/chroma
- [T17] Qdrant, precios y licencia: https://qdrant.tech/pricing , https://github.com/qdrant/qdrant
- [T18] Crossref, cambios en límites de la REST API: https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/ ; actualización de julio de 2026: https://community.crossref.org/t/refining-rest-api-limits-for-improved-stability-and-reliability/16137
- [T19] OpenAlex, autenticación y precios: https://developers.openalex.org/api-reference/authentication.md ; anuncio de claves obligatorias: https://groups.google.com/g/openalex-users/c/rI1GIAySpVQ
- [T20] Semantic Scholar, API: https://www.semanticscholar.org/product/api
- [T21] Unpaywall, REST API: https://unpaywall.org/products/api
- [T22] Europe PMC, RESTful Web Service: https://europepmc.org/RestfulWebService
- [T23] DOI Citation Formatter y negociación de contenido: https://citation.crosscite.org/docs.html
- [T24] Docling, repositorio y documentación: https://github.com/docling-project/docling
- [T25] GROBID, repositorio y documentación: https://github.com/kermitt2/grobid , https://grobid.readthedocs.io
- [T26] PyMuPDF, licencia AGPL o comercial: https://pypi.org/project/PyMuPDF/
- [T27] Ragas, documentación: https://docs.ragas.io
- [T28] DeepEval, repositorio: https://github.com/confident-ai/deepeval
- [T29] Langfuse, precios y autoalojamiento: https://langfuse.com/pricing , https://langfuse.com/pricing-self-host
- [T30] LangSmith, precios: https://www.langchain.com/pricing-langsmith
- [T31] Oracle Cloud Infrastructure, Always Free Resources: https://docs.oracle.com/iaas/Content/FreeTier/resourceref.htm
- [T32] Render, Deploy for Free: https://render.com/docs/free
- [T33] Hugging Face, Spaces overview: https://huggingface.co/docs/hub/en/spaces-overview
- [T34] Streamlit, autenticación de usuarios: https://docs.streamlit.io/develop/concepts/connections/authentication
- [T35] Documentación oficial de FastAPI (https://fastapi.tiangolo.com), React (https://react.dev), python-docx (https://python-docx.readthedocs.io) y Ollama (https://ollama.com)
- [T36] Secundaria: requerimientos de memoria de modelos Qwen3 locales según https://www.premai.io/blog/qwen-3-vs-llama-3-for-local-deployment-which-model-what-hardware-and-when-to-skip-diy/

Las referencias numeradas entre corchetes sin la letra T ([24], [46], etc.) corresponden a la bibliografía de la tesis.

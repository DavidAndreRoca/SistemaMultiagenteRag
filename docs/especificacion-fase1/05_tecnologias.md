# 15. Comparativa de tecnologías

Las tablas siguen el formato solicitado. "Plan gratuito" recoge solo condiciones verificadas en la fuente indicada entre corchetes (sección 25); cuando una condición no pudo verificarse se indica "no verificado". Las licencias de herramientas muy conocidas (FastAPI, React, python-docx) se indican según su documentación oficial.

## 15.1. Lenguaje y backend

**Tabla 27. Backend**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| Python 3.12 | Lenguaje | PSF | Libre | Ecosistema de IA, RAG, NLP y clientes de todas las APIs | Rendimiento de CPU menor que lenguajes compilados (irrelevante aquí) | Total | **Elegido** |
| FastAPI | Framework web | MIT | Libre | Asíncrono, validación con Pydantic, OpenAPI automático, SSE | Requiere disciplina de capas | Nativa con Pydantic y SDK | **Elegido** |
| Flask | Framework web | BSD | Libre | Simple y maduro | Síncrono por defecto; validación y OpenAPI por extensiones | Buena | Descartado |
| Django | Framework completo | BSD | Libre | Panel de administración, ORM, autenticación | Más pesado; asincronía parcial; duplica lo que hace la SPA | Buena | Descartado |

## 15.2. Frontend

**Tabla 28. Frontend**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| React + TypeScript + Vite | SPA | MIT | Libre | Control total de la UI (vista comparada, evidencias desplegables, estados en vivo), tipado, gran ecosistema accesible | Más código que Streamlit; requiere build | Consume la API REST/SSE | **Elegido** |
| Streamlit | Framework de UI en Python | Apache 2.0 | Libre | Muy rápido para prototipos | Autenticación nativa solo OIDC [V, T34]; reejecución por interacción; poco control de diseño y accesibilidad | Directa en Python | Descartado para X; útil para tableros internos |
| Gradio | UI para demos | Apache 2.0 | Libre | Demos de modelos | Orientado a demos, no a aplicaciones con roles | Directa | Descartado |
| Next.js | Framework React con servidor | MIT | Libre | SSR y rutas | Añade un servidor Node sin necesidad | Buena | Descartado (sobredimensionado) |

## 15.3. Frameworks multiagente y orquestación

**Tabla 29. Orquestación**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| LangGraph 1.x | Grafo de estados | MIT | Libre (LangSmith es aparte) | Flujo explícito con aristas condicionales; checkpointers SQLite, PostgreSQL y Redis; API estable desde 1.0 (oct. 2025) [V, T1] | Curva de aprendizaje; documentación orientada al ecosistema LangChain | Nodos como funciones Python; no obliga a usar LangChain | **Elegido** |
| CrewAI | Equipos de agentes + Flows | MIT [V, T3] | Libre; nube comercial aparte | Roles y tareas rápidos de definir; Flows con estado | Su modelo por defecto es de colaboración autónoma, contrario a la selección determinista | Buena | Descartado |
| AutoGen | Conversación multiagente | MIT | Libre | Pionero en patrones multiagente | En mantenimiento: solo correcciones; se recomienda Microsoft Agent Framework para proyectos nuevos [V, T2] | Buena | Descartado |
| Microsoft Agent Framework | Framework de agentes | MIT | Libre | Sucesor de AutoGen con soporte a largo plazo [V, T2] | Orientado a empresa; ecosistema más joven | Buena | Alternativa no elegida |
| LlamaIndex Workflows | Flujos por eventos + RAG | MIT | Libre; LlamaCloud aparte | Muy fuerte en RAG; Workflows como primitiva recomendada [V, T4] | Orquestación por eventos menos explícita que un grafo para este caso | Buena | Descartado como orquestador; no se usa para RAG porque el RAG se implementa directo sobre pgvector |
| Código propio sin framework | Máquina de estados | No aplica | No aplica | Máximo control | Reimplementar persistencia, reanudación y trazas | Total | Descartado |

## 15.4. Embeddings y reranking

**Tabla 30. Modelos de recuperación**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| BAAI/bge-m3 | Embeddings multilingües | MIT [V, T12] | Pesos abiertos | Más de 100 idiomas, 1 024 dimensiones, 8 192 tokens; salida densa, dispersa y multivector en un solo modelo [V, T12] | Unos 568 millones de parámetros; en CPU la ingesta es lenta (se hace fuera de línea) | Local en contenedor | **Elegido** |
| Qwen3-Embedding-0.6B | Embeddings multilingües | Apache 2.0 [V, T13] | Pesos abiertos | 32 000 tokens, dimensión configurable hasta 1 024, 64.33 en MTEB multilingüe [V, T13] | Requiere instrucción en la consulta; sin salida dispersa | Local | Alternativa: se compara en la calibración |
| Embeddings por API (OpenAI, Gemini) | Servicio | Comercial | Variable | Sin hardware | Envía el corpus a un tercero; costo | Simple | Descartado |
| BAAI/bge-reranker-v2-m3 | Cross-encoder multilingüe | Apache 2.0 [V, T14] | Pesos abiertos | Pareja natural de bge-m3; ligero y multilingüe [V, T14] | Unos 568 millones de parámetros; latencia en CPU proporcional al número de candidatos | Local | **Elegido** |
| jina-reranker-v2 | Cross-encoder | CC BY-NC (según su ficha, verificar) | Pesos con uso no comercial | Rápido | Licencia restrictiva | Local | Descartado |

## 15.5. Bases de datos y almacenamiento

**Tabla 31. Persistencia**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| PostgreSQL 16+ con pgvector | Relacional + vectorial | PostgreSQL License | Libre | Una sola base: registro, vectores HNSW, texto completo, cola y checkpoints; transacciones y claves foráneas; un solo respaldo | Requiere afinar índices; menos funciones vectoriales avanzadas que un motor dedicado | SQLAlchemy y checkpointer de LangGraph | **Elegido** |
| Chroma | Base vectorial | Apache 2.0 [V, T16] | Libre | Muy simple, modo persistente local | Segundo almacén; sincronización con el registro | Buena | Descartado |
| Qdrant | Base vectorial | Apache 2.0 [V, T17] | Libre; nube con clúster gratuito de 1 GB RAM [V, T17] | Filtros y búsqueda híbrida potentes | Servicio adicional; la nube gratuita envía datos a un tercero | Buena | Descartado (sobredimensionado para unos 50 000 fragmentos) |
| FAISS | Biblioteca de índices | MIT | Libre | Muy rápido | Sin persistencia ni metadatos gestionados | Requiere código | Descartado |
| SQLite | Relacional embebida | Dominio público | Libre | Cero configuración | Escrituras concurrentes serializadas | Buena | Solo para pruebas unitarias |
| Sistema de archivos cifrado | Almacenamiento de .docx y PDF | No aplica | No aplica | Simple; respaldo junto a la base | Debe cifrarse y rotarse | Directa | **Elegido** |

## 15.6. Procesamiento documental

**Tabla 32. Extracción y preparación de documentos**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| Docling | Conversión de PDF, DOCX y otros | MIT [V, T24] | Libre | Diseño de página, orden de lectura, tablas, OCR y una representación estructurada con títulos [V, T24] | Más lento en CPU; modelos de varios cientos de MB | Python | **Elegido** para el corpus |
| GROBID | Extracción científica a TEI | Apache 2.0 [V, T25] | Libre (servidor propio) | Encabezados, secciones y referencias; análisis de referencias sueltas con F1 cercano a 0.90 [V, T25] | Java en Docker; no corre nativo en Windows | Servicio REST | **Elegido** para metadatos y referencias |
| python-docx | Lectura de .docx | MIT | Libre | Lee estilos de título, párrafos y tablas del borrador | No interpreta campos de Mendeley de forma completa | Python | **Elegido** para borradores |
| PyMuPDF | Lectura de PDF | AGPL-3.0 o comercial [V, T26] | Libre bajo AGPL | Muy rápido | AGPL exige publicar el código del servicio de red | Python | Descartado por licencia |
| pypdf | Lectura de PDF | BSD | Libre | Ligero | Sin estructura de diseño | Python | Respaldo |
| Unstructured | Partición de documentos | Apache 2.0 (núcleo) | Libre; API comercial aparte | Muchos formatos | Duplica a Docling | Python | Descartado |

## 15.7. APIs académicas y bibliográficas

**Tabla 33. Servicios bibliográficos**
| Servicio | Tipo | Modalidad | Acceso y límites verificados | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| Crossref REST API | Metadatos DOI | Gratuito, sin clave | Pool cortés con `mailto`: 10 consultas por segundo de registro individual y 3 de listas o búsquedas; desde julio de 2026 el límite se aplica por correo [V, T18] | Fuente principal de DOI; búsqueda bibliográfica (`query.bibliographic`) | Cobertura limitada a DOI de Crossref | REST JSON | **Principal** |
| doi.org (negociación de contenido) | Resolución y formato | Gratuito | Devuelve CSL-JSON, BibTeX, RIS y cita formateada en estilos CSL como APA o IEEE para DOI de Crossref, DataCite y mEDRA [V, T23] | Cita propuesta determinista, sin modelo | Depende del registro del DOI | HTTP con cabecera Accept | **Elegido** |
| Unpaywall | Estado de acceso abierto | Gratuito con correo | Parámetro `email` obligatorio; uso pedido de hasta 100 000 llamadas por día [V, T21] | Ubicación legal del texto completo y tipo de OA | Solo por DOI | REST JSON | **Elegido** para RN-14 |
| OpenAlex | Grafo académico abierto | Freemium | Clave gratuita obligatoria desde el 13 de febrero de 2026; USD 1 diario de uso gratuito por clave; búsqueda alrededor de USD 1 por 1 000; consulta individual por DOI sin costo [V, T19] | Búsqueda por metadatos sin DOI; OA de respaldo; cobertura amplia | Precio por uso; los valores pueden cambiar | REST JSON | **Complementario** |
| Semantic Scholar | Grafo académico | Gratuito | Sin clave comparte un límite global; con clave, 1 consulta por segundo inicial [V, T20] | Resúmenes y citas | Límite bajo; aprobación de la clave por correo | REST | Opcional, no en X |
| Europe PMC | Literatura biomédica | Gratuito, sin clave | Sin clave [V, T22] | Texto completo OA en biomedicina | Solo ciencias de la vida | REST | Solo si un tema es biomédico |
| Catálogos para ISBN | Libros | Variable | No verificado | Necesario para libros sin DOI | Calidad variable | REST | A definir en el sprint 4 |

## 15.8. Evaluación, observabilidad y pruebas

**Tabla 34. Evaluación y observabilidad**
| Herramienta | Tipo | Licencia | Plan gratuito | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| Ragas | Métricas RAG | Apache 2.0 [V, T27] | Libre (usa un LLM evaluador) | Fidelidad, precisión y exhaustividad de contexto, relevancia de respuesta: corresponden a cuatro indicadores de la ficha | El juez LLM tiene costo y sesgos; validar con revisión humana | Python | **Elegido** en el arnés |
| DeepEval | Pruebas de LLM tipo pytest | Apache 2.0 [V, T28] | Libre; plataforma comercial aparte | Métricas personalizadas (G-Eval) para "no reescribe", "no inventa datos" | Solapa con Ragas | pytest | **Elegido** para pruebas de comportamiento |
| pytest + Playwright | Pruebas unitarias y extremo a extremo | MIT / Apache 2.0 | Libre | Estándar | Ninguna relevante | CI | **Elegido** |
| Langfuse | Trazas y evaluación | MIT (núcleo) | Nube Hobby 50 000 unidades al mes; autoalojado sin límites [V, T29] | Trazas de agentes, tokens y latencia | La nube recibe textos; autoalojar exige varios servicios | SDK y OpenTelemetry | Opcional en desarrollo con datos ficticios |
| LangSmith | Trazas y evaluación | Comercial | Developer: 1 asiento, 5 000 trazas al mes [V, T30] | Integración nativa con LangGraph | Nube de terceros; autoalojado solo empresarial | SDK | Solo en desarrollo con datos ficticios |
| Registro propio (evento técnico) + logs estructurados | Observabilidad mínima | No aplica | No aplica | Sin terceros; datos ya necesarios para la tesis | Menos visualización | Nativa | **Elegido** en producción |

## 15.9. Despliegue

**Tabla 35. Despliegue**
| Opción | Tipo | Modalidad | Condiciones verificadas | Ventajas | Desventajas | Integración | Recomendación |
|---|---|---|---|---|---|---|---|
| Docker Compose | Contenedores | Libre | No aplica | Mismo entorno en local y servidor | Requiere aprender comandos básicos | Total | **Elegido** |
| VPS de pago | IaaS | Pago | Precio no verificado; varía por proveedor | Siempre encendido, x86, control total | Costo mensual | Docker | **Elegido** para O2 |
| Oracle Always Free | IaaS | Gratuito | 2 OCPU y 12 GB ARM; reclamación por inactividad [V, T31] | Sin costo | ARM, capacidad y reclamación | Docker (imágenes arm64) | Demostración |
| Render gratuito | PaaS | Gratuito | Suspensión a los 15 minutos; 512 MB; base que expira a 30 días [V, T32] | Fácil | No sirve para O2 | Docker | Descartado |
| Hugging Face Spaces | PaaS | Gratuito con restricciones | 2 vCPU, 16 GB, disco no persistente; Docker requiere plan de pago para crear [V, T33] | Visibilidad | Sin persistencia | Docker | Descartado |

# 16. Evaluación de modelos de lenguaje y planes gratuitos

## 16.1. Criterio decisivo de la tesis

La tesis ya fijó el tipo de proveedor: un servicio comercial con API de pago cuyas condiciones excluyen el uso de los datos enviados para entrenar modelos, nombrado en el consentimiento informado (apartados 6.1.5 y 6.2.5.1). Esa decisión filtra las opciones gratuitas antes de comparar calidad o precio, porque durante O2 se envían fragmentos de manuscritos de estudiantes.

**Tabla 36. Opciones de modelo de lenguaje**
| Opción | Condiciones verificadas | Precio de referencia por millón de tokens (entrada / salida) | Evaluación para O2 |
|---|---|---|---|
| API de Claude: Sonnet 5.5 | Términos comerciales: no se entrena con el contenido del cliente; supresión en el servidor dentro de 30 días [V, T5, T6] | USD 2 / USD 10; lectura de caché USD 0.10; lote 50 % [V, T5] | Apto. Calidad alta para diagnóstico en español [S, se confirma en la prueba comparativa] |
| API de Claude: Haiku 5.5 | Igual que arriba | USD 0.10 / USD 0.50 para prompts de hasta 100 000 tokens; USD 0.50 / USD 2.50 por encima [V, T5] | Apto para suficiencia, extracción y evaluación; calidad de generación por confirmar |
| OpenAI: GPT-5 mini | La API no se usa para entrenar salvo adhesión explícita; registros de abuso hasta 30 días [V secundaria, T7] | USD 0.25 / USD 2 [V secundaria, T7] | Apto como alternativa |
| Google Gemini (plan de pago) | En el plan de pago los datos no se usan para mejorar productos [V, T8] | Gemini 3 Flash alrededor de USD 0.50 / USD 3 [V secundaria, T8] | Apto como alternativa |
| Google Gemini (plan gratuito) | El contenido se usa para mejorar productos [V, T8] | Gratuito con límites | **No apto** para O2 |
| Mistral (plan gratuito) | En el plan gratuito los datos pueden usarse para entrenamiento salvo exclusión; el plan de pago está excluido por defecto [V, T10] | Gratuito con límites | No apto sin exclusión explícita; mejor el de pago si se elige Mistral |
| Groq (plan gratuito) | No entrena ni retiene por defecto; límites por organización, por ejemplo gpt-oss-120b: 30 por minuto, 1 000 por día, 8 000 tokens por minuto y 200 000 por día [V, T9] | Gratuito | Condiciones de datos aptas, pero el límite diario cubriría solo una decena de solicitudes de unos 16 000 tokens: **apto para desarrollo**, no para O2 |
| DeepSeek (API) | Datos tratados y almacenados en la República Popular China según su política [V, T11] | Muy bajo | **No apto** por riesgo para manuscritos de estudiantes |
| Modelo abierto local (por ejemplo, familia Qwen3 con Ollama) | Sin envío de datos | Hardware propio; un modelo de 30 mil millones de parámetros cuantizado a 4 bits requiere alrededor de 18 a 20 GB de memoria [V secundaria, T36] | Cumple privacidad, pero en CPU la latencia con 28 casos no es aceptable y la calidad en español académico es inferior [S]. Apto para desarrollo |

## 16.2. ¿Conviene usar modelos distintos por función?

Sí, por costo y por independencia [R]:

- **Orquestación:** ningún modelo; es determinista.
- **Generación de los agentes D1 a D4:** el modelo de mayor calidad del presupuesto, porque de él depende la utilidad de la intervención X.
- **Suficiencia, extracción de referencias desde texto mal formado y pertinencia de consultas:** un modelo económico.
- **Evaluación de fidelidad:** un modelo con rol e instrucción separados; puede ser el económico si su concordancia con la revisión humana es aceptable, o el mismo de generación si no lo es.

La familia del evaluador puede coincidir con la del generador; la tesis exige rol e instrucción separados, no proveedor distinto. Usar un segundo proveedor obligaría a nombrarlo también en el consentimiento.

# 17. Stack tecnológico recomendado

## 17.1. Decisiones por componente

**Tabla 37. Stack recomendado y su justificación**
| Tecnología | Por qué y función | Requisitos que satisface | Alternativas descartadas | Limitaciones | Costo |
|---|---|---|---|---|---|
| Python 3.12 + FastAPI + Pydantic 2 + SQLAlchemy 2 + Alembic | API asíncrona tipada; esquemas compartidos con las salidas de los agentes | RF-01 a RF-27, RNF-19, RNF-22 | Flask, Django | Ninguna relevante | 0 |
| React + TypeScript + Vite + biblioteca de componentes accesible | Interfaz real con vista comparada, evidencias y estados | RF-19, RF-21, RF-22, RNF-17, RNF-18 | Streamlit, Gradio, Next.js | Más código de interfaz | 0 |
| LangGraph 1.x con checkpointer PostgreSQL | Grafo explícito: validar, enrutar, recuperar, suficiencia, generar, verificar, etiquetar | RF-03, RF-10, RF-11, RNF-04, RNF-05 | CrewAI, AutoGen, LlamaIndex Workflows | Fijar versión menor para O2 | 0 |
| PostgreSQL 16+ con pgvector | Registro, vectores HNSW, búsqueda léxica, cola y checkpoints | RNF-01, RNF-03, RNF-14 | Chroma, Qdrant, SQLite | Afinar HNSW (`m`, `ef_search`) | 0 |
| bge-m3 + bge-reranker-v2-m3 (local, CPU) | Recuperación multilingüe español-inglés sin enviar datos | RF-10, RNF-10, RNF-23 | Qwen3-Embedding (en evaluación), embeddings por API | RAM de unos 5 GB; latencia de reranking | 0 |
| Docling + GROBID + python-docx | Corpus estructurado por secciones; metadatos y referencias; secciones del borrador | RF-01, RF-09, RF-13, RF-15, RF-20 | PyMuPDF (AGPL), Unstructured | GROBID requiere Docker | 0 |
| Crossref + doi.org + Unpaywall + OpenAlex | Existencia, metadatos, cita formateada y acceso abierto | RF-09, RF-11, RF-13, RF-20, RNF-08 | Semantic Scholar (opcional) | Límites de tasa; clave de OpenAlex | 0 a pocos USD en OpenAlex |
| API de Claude: Sonnet 5.5 (agentes) y Haiku 5.5 (auxiliares y evaluador), detrás de un adaptador | Calidad de generación en español, salidas estructuradas, caché de instrucciones y términos sin entrenamiento | RF-04 a RF-11, RNF-10, RNF-20 | Gemini gratuito, Mistral gratuito, DeepSeek; GPT-5 mini y Gemini de pago quedan como alternativas | Costo por token; cambios de catálogo | Ver 17.4 |
| Ragas + DeepEval + pytest + Playwright | Métricas de la ficha y pruebas de regresión | RF-25, RNF-19, RNF-23 | LangSmith y Langfuse en nube para producción | Juez LLM con costo | Incluido en 17.4 |
| Docker Compose + Caddy + VPS | Despliegue reproducible con HTTPS | RNF-13, RNF-15 | Render, Spaces | Costo del VPS | Ver 17.4 |
| Git + GitHub privado + integración continua | Control de versiones, revisión y pruebas automáticas en cada cambio | RNF-19, RNF-21 | No aplica | Ninguna | 0 |

Sobre la elección del proveedor: la API de Claude, GPT-5 mini y Gemini de pago cumplen la condición de la tesis. Se recomienda la API de Claude porque sus precios y su política de no entrenamiento están verificados en fuentes oficiales al día de hoy [V, T5, T6], porque su nivel Haiku 5.5 abarata las tareas auxiliares y porque el equipo ya usa Claude Code, lo que simplifica la gestión de una sola cuenta. La recomendación queda sujeta a una prueba comparativa en el sprint 8: 30 solicitudes de prueba de los seis tipos con Sonnet 5.5, Haiku 5.5 y GPT-5 mini, valoradas a ciegas por los dos investigadores con una lista de comprobación. Si la diferencia de calidad no justifica el costo, se adopta la opción más económica. El adaptador hace que el cambio no afecte a los agentes.

## 17.2. Escenario A: mínimo costo

- Modelo abierto local (familia Qwen3 u otra con licencia permisiva) servido con Ollama en la computadora del equipo o en Oracle Always Free.
- Groq gratuito como respaldo durante el desarrollo, con datos ficticios.
- Mismos componentes locales del escenario B para embeddings, reranking, base de datos y procesamiento.
- Alojamiento en Oracle Always Free.
- Costo: cero en servicios; solo electricidad y tiempo.

## 17.3. Escenario B: híbrido (recomendado)

- Todos los componentes locales del escenario A, salvo el modelo de lenguaje.
- API de pago del proveedor elegido para generación y evaluación.
- VPS de pago durante la prueba piloto y O2.
- Desarrollo con Groq gratuito o modelo local y datos ficticios para reducir gasto; la calibración y el arnés final con el modelo de producción.

**Tabla 38. Comparación de escenarios**
| Criterio | Escenario A (mínimo costo) | Escenario B (híbrido) |
|---|---|---|
| Cumple la decisión de la tesis sobre el proveedor | No: la tesis fija un proveedor comercial de pago; habría que modificar el 6.2.5.1 y el consentimiento | Sí |
| Calidad en español académico | Inferior con modelos que caben en el hardware disponible [S] | Alta [S, confirmar en la prueba comparativa] |
| Latencia con 28 casos | Inaceptable en CPU; requeriría GPU | Adecuada; la limitan la recuperación y el proveedor |
| Disponibilidad | Riesgo de reclamación y de capacidad en Oracle | VPS siempre encendido |
| Privacidad | Máxima: nada sale | Alta: solo fragmentos acotados a un proveedor sin entrenamiento |
| Costo total estimado | Cercano a cero | Unos USD 170 a 455 en todo el proyecto (17.4) |
| Riesgo para la validez del experimento | Alto: una X de menor calidad sesga el resultado contra la hipótesis | Bajo |

**Recomendación:** escenario B para la versión estable y O2; componentes del escenario A durante el desarrollo.

## 17.4. Estimación de costos

Supuestos [S]: 28 casos; unas 13 solicitudes por hito y caso, es decir, alrededor de 3 000 solicitudes en O2; por solicitud, una generación de 7 000 tokens de entrada y 1 000 de salida, una evaluación de 6 000 y 600, y un juicio de suficiencia de 3 000 y 100; 20 % de reintentos en generación y evaluación. Los modelos de Claude desde la versión 4.7 usan un tokenizador que produce alrededor de 30 % más tokens para el mismo texto [V, T5], por lo que se añade una columna de sensibilidad.

**Tabla 39. Costo estimado de API durante O2 por configuración**
| Configuración | Costo O2 (USD) | Con +30 % de tokens (USD) | Uso recomendado |
|---|---|---|---|
| Sonnet 5.5 genera; Haiku 5.5 evalúa y decide suficiencia | 91 | 118 | **Recomendada** |
| Sonnet 5.5 genera y evalúa; Haiku 5.5 suficiencia | 152 | 198 | Si el evaluador económico no concuerda con la revisión humana |
| Haiku 5.5 para todo | 9 | 11 | Si la prueba comparativa no muestra diferencias relevantes |
| GPT-5 mini para todo (precio de fuente secundaria) | 26 | No aplica | Alternativa |
| Gemini 3 Flash de pago para todo (precio de fuente secundaria) | 46 | No aplica | Alternativa |

Cálculo de la configuración recomendada: generación 3 600 llamadas × 7 000 tokens = 25.2 millones de entrada × USD 2 = USD 50.4, más 3.6 millones de salida × USD 10 = USD 36; evaluación con Haiku 5.5 21.6 millones × USD 0.10 + 2.16 millones × USD 0.50 = USD 3.2; suficiencia 9 millones × USD 0.10 + 0.3 millones × USD 0.50 = USD 1.1. La caché de las instrucciones de sistema reduce el costo de entrada, por lo que la cifra es conservadora.

**Tabla 40. Presupuesto total estimado del software**
| Rubro | Mínimo (USD) | Máximo (USD) |
|---|---|---|
| API del modelo durante el desarrollo, la calibración y el arnés (unas 2 000 solicitudes) | 40 | 130 |
| API del modelo durante la prueba piloto y O2 | 90 | 200 |
| VPS de 4 vCPU y 8 GB durante unos 4 meses [S, precio por confirmar] | 40 | 100 |
| OpenAlex por encima del uso diario gratuito | 0 | 10 |
| Dominio propio (opcional) | 0 | 15 |
| **Total** | **170** | **455** |

Se configura un tope de gasto en la consola del proveedor y en el sistema (RNF-24). Anthropic indica que pueden existir descuentos académicos y de investigación [V, T5]; conviene solicitarlos.

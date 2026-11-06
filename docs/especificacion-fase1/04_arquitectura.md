# 11. Matriz de trazabilidad

La matriz recorre la cadena que pide esta fase: problema, objetivo, dimensión o indicador, necesidad del usuario, funcionalidad, requisito y componente. Complementa, sin reemplazarla, la Tabla 24 de la tesis (dimensión, agente, requisito, caso de uso, historia, sprint y prueba).

**Tabla 21. Matriz de trazabilidad problema a componente**
| Problema (causa o consecuencia) | Objetivo | Dimensión / indicador | Necesidad del usuario | Funcionalidad | Requisito | Componente |
|---|---|---|---|---|---|---|
| C4. Revisión global sin diagnóstico por componente | OE1 | D1: alineación problema-objetivos-hipótesis; secuencia lógica; cohesión | Saber qué falla en la organización de una sección | F-08 | RF-04, RNF-06 | Agente estructural, corpus de guías |
| C2. Retroalimentación atada a la sesión semanal | OE1 | D1: secuencia y cohesión por hito | Organizar el avance cuando lo necesita | F-09 | RF-05 | Agente estructural |
| C4 y C2 | OE2 | D2: justificación del diseño; validez de técnicas e instrumentos; precisión del análisis | Detectar debilidades metodológicas antes de entregar | F-10 | RF-06 | Agente metodológico |
| C3. IA general sin orientación | OE3 | D3: registro formal; fluidez y precisión léxica; corrección gramatical | Mejorar un párrafo sin ceder la autoría | F-11 | RF-07, RNF-06 | Agente estilístico, verificación de límites |
| C1. Dominio escaso de fuentes y herramientas dispersas | OE4 | D4: calidad de las fuentes | Sustentar una afirmación con fuentes de calidad y abiertas | F-12, F-20 | RF-08, RF-21, RNF-08 | Agente D4, recuperador, corpus científico |
| K2. Referencias inexistentes o erróneas | OE4 | D4: verificabilidad de las referencias; aplicación de la norma | Comprobar que lo citado existe y está bien referenciado | F-13 | RF-09 | Agente D4, GROBID, Crossref, OpenAlex |
| Contenido generado sin sustento (alucinación) | OE1 a OE4 | Fidelidad respuesta-fuente; tasa de referencias no verificables (VI) | Confiar en la salida antes de usarla | F-14, F-15 | RF-10, RF-11, RNF-04, RNF-05 | Recuperador, nodo de suficiencia, módulo de verificación |
| Vacío del corpus para la consulta | OE4 | Cobertura del corpus (VI) | Usar una fuente que encontró por su cuenta | F-18 | RF-13 | Módulo de verificación, agente D4, colección personal |
| K3. Pérdida de trazabilidad de la autoría | OG | Decisiones aceptadas, modificadas y rechazadas; uso mínimo | Demostrar su aporte y declarar herramientas | F-04, F-17, F-19 | RF-01, RF-12, RF-14, RNF-01 | Gestión de versiones, registro de interacciones |
| Recuperación desde fuentes verificables (6.1.5) | OG | Calidad de la recuperación documental (VI) | Disponer de corpus por tema a tiempo | F-21, F-22 | RF-15, RF-20 | Gestión de corpus, Docling, GROBID, Unpaywall |
| Medición de la VI (6.1.4) | OG | Seis indicadores de la ficha de métricas | Calcular indicadores sin datos personales | F-23, F-26 | RF-17, RF-25, RNF-02 | Exportación, arnés de evaluación |
| Un solo artefacto para todos los casos (amenaza de instrumentación) | OG | Validez interna del diseño | Garantizar que X no cambia durante O2 | F-24 | RF-23, RNF-21, RN-21, RN-24 | Configuración versionada |
| Aislamiento y ética (aspectos éticos) | OG | Confidencialidad | Que nadie vea su borrador | F-01, F-02, F-27 | RF-16, RF-18, RF-26, RNF-03, RNF-10, RNF-11 | Autenticación, repositorios con filtro por caso |
| Disponibilidad durante O2 | OG | Usabilidad del sistema (cuestionario) | Usar el sistema en cualquier momento de las semanas 12 a 22 | F-03, F-16, F-25 | RF-19, RF-22, RF-24, RNF-12 a RNF-14 | Interfaz, worker, monitoreo, servidor |

# 12. Arquitectura lógica

## 12.1. Evaluación de las decisiones previas

**Tabla 22. Evaluación individual de las decisiones previas**
| Decisión previa | Resultado | Fundamento |
|---|---|---|
| LangGraph para orquestación | Se mantiene | Modela el flujo como grafo de estados explícito con aristas condicionales, persistencia por hilo con checkpointers para SQLite, PostgreSQL y Redis, y es estable desde la versión 1.0 de octubre de 2025 [V, T1]. Ese control explícito es justo lo que exige un flujo con abstención, un reintento y etiquetas fijas |
| Chroma como base vectorial local | Se reemplaza por pgvector | Chroma es Apache 2.0 y adecuado para prototipos [V, T16], pero obliga a mantener una segunda base sincronizada con el registro relacional, y el aislamiento por caso quedaría en el código de la aplicación sobre dos almacenes. Con pgvector, fragmentos, documentos, colecciones y registro viven en una sola base transaccional, con claves foráneas entre `fragmento_recuperado` y `fragmento`, un solo respaldo y filtros SQL por colección |
| Embeddings multilingües | Se mantiene; modelo bge-m3 | Ver sección 15.4 |
| SQLite para el registro | Se reemplaza por PostgreSQL | Con 28 casos simultáneos y un worker que escribe eventos, verificaciones y checkpoints a la vez, SQLite serializa las escrituras. PostgreSQL resuelve concurrencia, cola de trabajos y vectores en un mismo servicio. SQLite se conserva para pruebas unitarias |
| Streamlit como interfaz | Se reemplaza por React | Streamlit ofrece autenticación nativa solo mediante OIDC con proveedores externos [V, T34] y un modelo de reejecución del script por interacción; la tesis exige cuentas por código sin datos personales, vistas comparadas, evidencias desplegables y estados en vivo. Una SPA consume la misma API que prueban las pruebas automáticas |
| Crossref como fuente principal | Se mantiene | Gratuito y sin clave; pool cortés con parámetro `mailto` [V, T18] |
| OpenAlex como complemento | Se mantiene con ajuste | Desde el 13 de febrero de 2026 exige clave gratuita y aplica precio por uso con USD 1 diario gratuito por clave [V, T19]; se usa para búsqueda por metadatos y estado OA de respaldo |
| Un orquestador, cuatro agentes y un módulo de verificación | Se mantiene | Es la arquitectura de la tesis; no se añaden agentes |

## 12.2. Capas y responsabilidades

**Tabla 23. Capas de la arquitectura lógica**
| Capa | Responsabilidad | Componentes |
|---|---|---|
| Presentación | Interacción del estudiante y del investigador; no contiene lógica de recuperación, generación ni verificación (Tabla 17 de la tesis) | SPA React: panel, solicitud, visor de resultado, historial, consola del investigador |
| Aplicación | API, autenticación, autorización por rol y caso, validación de entradas, gestión de versiones, encolado de solicitudes, exportaciones y configuración | FastAPI, servicios de dominio, cola de trabajos |
| Orquestación multiagente | Ejecutar el grafo de cada solicitud: validar, enrutar, recuperar, evaluar suficiencia, generar, verificar, etiquetar y registrar | LangGraph, nodo orquestador |
| Agentes especializados | Resolver el tipo asignado con su colección, herramientas y esquema de salida | Cuatro agentes con instrucciones versionadas |
| Recuperación RAG | Ingesta, segmentación, embeddings, búsqueda híbrida, reranking y suficiencia | Docling, GROBID, python-docx, bge-m3, bge-reranker-v2-m3, pgvector |
| Integración y verificación | Seis comprobaciones, reintento, etiqueta, entrega y registro | Módulo verificador y modelo evaluador |
| Persistencia | Registro de interacciones, colecciones, fragmentos y vectores, configuración, archivos | PostgreSQL con pgvector; volumen de archivos |
| Servicios externos | Generación y evaluación; verificación bibliográfica y de acceso abierto | Proveedor LLM; Crossref, doi.org, Unpaywall, OpenAlex |

*[Figura 3. Diagrama general de arquitectura: ver diagramas Mermaid de la Fase 1]*

## 12.3. Componentes

El código se organiza en un repositorio con módulos que reflejan las capas. Cada módulo de integración externa está detrás de una interfaz para poder sustituirlo y simularlo en pruebas.

*[Figura 4. Diagrama de componentes: ver diagramas Mermaid de la Fase 1]*

## 12.4. Modelo de datos

Se adopta el modelo de diez entidades de la tesis (Caso, Versión del borrador, Solicitud, Fragmento recuperado, Resultado o propuesta, Verificación, Decisión, Fuente aportada, Documento del corpus, Colección) y se añaden, por necesidad técnica, cinco tablas que no alteran la ficha de métricas:

- `fragmento`: cada segmento indexado de un documento, con texto, sección IMRaD, página, orden, vector de 1 024 dimensiones y vector léxico. `fragmento_recuperado` la referencia.
- `cuenta`: credenciales y rol; se enlaza a `caso` o a un investigador; sin datos personales.
- `configuracion`: versiones de parámetros, instrucciones y modelos; cada solicitud guarda la versión vigente.
- `evento_tecnico`: latencias, tokens, costo y errores por etapa (para RF-24, separado del registro metodológico).
- `cache_metadatos`: respuestas de Crossref, OpenAlex y Unpaywall por DOI, para no repetir consultas y respetar los límites.

Se propone además añadir a `solicitud` los atributos `motivo` (para "no atendida" o "fuera de alcance") y `configuracion_id`, y a `documento` los atributos `licencia`, `url_acceso_abierto` y `estado_oa` (gold, green, hybrid, bronze) [R].

# 13. Arquitectura física y de despliegue

## 13.1. Componentes de ejecución

**Tabla 24. Componentes de ejecución, ubicación y recursos estimados**
| Componente | Dónde se ejecuta | Función | Recursos estimados [S] |
|---|---|---|---|
| SPA React | Navegador; archivos estáticos servidos por Caddy | Interfaz | Despreciable en servidor |
| API FastAPI | Servidor (contenedor `api`) | API REST, SSE, autenticación, cargas | 0.5 vCPU, 512 MB |
| Worker | Servidor (contenedor `worker`) | Grafo LangGraph, agentes, verificación | 1 vCPU, 1 GB |
| Modelos locales | Servidor (contenedor `modelos`) | bge-m3 y bge-reranker-v2-m3 en CPU | 2 vCPU, 4 a 5 GB (dos modelos de unos 568 millones de parámetros cada uno) |
| GROBID | Servidor (contenedor `grobid`) | Metadatos y referencias de PDF y cadenas | 1 vCPU, 2 a 4 GB |
| PostgreSQL 16 o superior con pgvector | Servidor (contenedor `db`) | Registro, vectores, cola, checkpoints | 1 vCPU, 1 a 2 GB, 20 GB de disco |
| Caddy | Servidor | Proxy inverso y HTTPS automático | Despreciable |
| Proveedor LLM | Externo | Generación y evaluación | Pago por token |
| Crossref, doi.org, Unpaywall, OpenAlex | Externos | Verificación y acceso abierto | Gratuitos con límites |
| Docling | Servidor o equipo local del investigador | Extracción de PDF durante la ingesta | Ingesta fuera de línea; puede ejecutarse en la computadora del equipo y subir el índice |

Total estimado en producción: 4 vCPU y 8 GB de RAM, con margen. Se puede bajar a 4 o 6 GB si la ingesta (Docling) y GROBID se ejecutan en la computadora del equipo y en producción solo quedan los modelos de consulta [R].

*[Figura 5. Diagrama de despliegue: ver diagramas Mermaid de la Fase 1]*

## 13.2. Local frente a externo

- **Local (equipo o servidor propio):** todo el código, la base de datos, los embeddings, el reranking, GROBID y Docling. Así ningún texto del corpus ni de los borradores sale para obtener vectores.
- **Externo obligatorio:** el proveedor LLM (por decisión de la tesis) y las bases bibliográficas.
- **Externo opcional:** plataforma de observabilidad en la nube, solo con datos ficticios en desarrollo.

## 13.3. Opciones de alojamiento para O2

**Tabla 25. Opciones de alojamiento verificadas**
| Opción | Condiciones verificadas | Evaluación para O2 |
|---|---|---|
| Oracle Cloud Always Free | Ampere A1: 1 500 horas OCPU y 9 000 GB-hora al mes, equivalentes a 2 OCPU y 12 GB; 200 GB de bloque; las instancias inactivas 7 días (CPU p95 menor a 20 %) pueden ser reclamadas [V, T31] | Recursos suficientes, pero con arquitectura ARM, riesgo de "sin capacidad" al crear y riesgo de reclamación por baja actividad en semanas de poco uso. Válido como servidor de demostración o de respaldo, no como único servidor de O2 |
| Render (plan gratuito) | Servicios web de 512 MB que se suspenden tras 15 minutos sin tráfico; sistema de archivos efímero; PostgreSQL gratuito que expira a los 30 días [V, T32] | No viable para O2 |
| Hugging Face Spaces | CPU Basic de 2 vCPU y 16 GB, disco no persistente; los Spaces Docker requieren plan de pago para crearse; se suspenden tras inactividad [V, T33] | No viable para una base de datos persistente |
| VPS de pago (por ejemplo, 4 vCPU y 8 GB) | Precios variables y en aumento durante 2026 según proveedor y región; verificar al contratar [S] | Recomendado para la prueba piloto y O2 (unos 4 meses) |
| Servidor de la universidad | No verificado | Opción preferente si la UTP lo facilita; consultar a la coordinación |

Recomendación [R]: desarrollo local con Docker Compose; un VPS de pago desde la semana 6 de 2027-1 hasta el cierre de O2, con los mismos contenedores; Oracle Always Free como entorno de demostración para la sustentación.

# 14. Comunicación entre componentes y diagramas técnicos

## 14.1. Diseño de la comunicación

**Tabla 26. Mecanismos de comunicación**
| Enlace | Mecanismo | Justificación |
|---|---|---|
| Frontend y backend | REST JSON sobre HTTPS con esquema OpenAPI; SSE para el estado de la solicitud | REST es suficiente para operaciones discretas. No se transmite el texto generado mientras se produce, porque nada se entrega antes de verificarse (RNF-05); se transmiten estados |
| Backend y orquestador | Cola de trabajos persistente en PostgreSQL (patrón `SELECT ... FOR UPDATE SKIP LOCKED`) y proceso worker separado | Las solicitudes duran decenas de segundos; no deben bloquear la API ni perderse si se reinicia el proceso. Evita añadir Redis. La biblioteca concreta se elige en el sprint 1 [S] |
| Orquestador y agentes | Llamadas en proceso dentro del grafo de LangGraph; estado tipado compartido por nodo | Sin red entre agentes; menos latencia y menos fallos |
| Agentes y RAG | Interfaz Python `Recuperador.buscar(caso_id, tipo, consulta)` que aplica el filtro de colección | El agente no elige colección; el repositorio impone el aislamiento |
| Recuperador y modelos locales | HTTP interno al contenedor de modelos (embeddings y reranking por lote) | Aísla la memoria de los modelos y permite escalar aparte |
| Verificación y servicios externos | Clientes HTTP asíncronos con limitador de tasa por servicio, reintento exponencial, tiempo máximo y caché por DOI | Respeta 10 consultas por segundo de registro individual y 3 de búsqueda en el pool cortés de Crossref [V, T18] y el presupuesto diario de OpenAlex [V, T19] |
| Sistema y base de datos | SQLAlchemy 2 con migraciones Alembic; checkpointer PostgreSQL de LangGraph | Un solo motor; migraciones versionadas |
| Sistema y proveedor LLM | SDK oficial detrás de un adaptador propio con salidas estructuradas y caché de instrucciones | Cambio de proveedor sin tocar agentes (RNF-20) |

## 14.2. Diagramas técnicos

Además de las figuras 1 a 5, se incluyen el proceso RAG y la verificación. El código Mermaid de todas las figuras se entrega junto a este documento para editarlo.

*[Figura 6. Proceso RAG: indexación y recuperación: ver diagramas Mermaid de la Fase 1]*

*[Figura 7. Integración y verificación de una propuesta: ver diagramas Mermaid de la Fase 1]*


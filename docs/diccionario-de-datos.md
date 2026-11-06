# Diccionario de datos

> Generado con `python -m app.bd.diccionario` desde los modelos ORM. **No editar a mano**:
> cambie los modelos y regenere. Una prueba automática falla si este archivo no coincide.

Convenciones: identificadores UUID; fechas `timestamptz` en UTC; enumeraciones guardadas
como texto con restricción CHECK. No hay columnas de nombre, correo ni documento de
identidad (RNF-02, RN-12): los casos se identifican solo por código.

La columna **Alimenta** indica qué métrica de la ficha de registro (M1 a M6, tesis,
Tabla 22) o qué otro dato exportado usa la columna. Las métricas no se guardan como
columnas: se calculan a partir del registro exportado (RF-17). Cuando la alimentan todas
las columnas de una tabla, la tabla lo declara y se repite en cada columna. El índice
inverso, de métrica a columnas, está al final.


## `cache_metadatos`

Caché de respuestas de servicios bibliográficos (T14).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `servicio` | varchar(40) | no |  |  | crossref, doi, unpaywall u openalex. |  |
| `clave` | text | no |  |  | DOI o consulta normalizada. |  |
| `respuesta` | jsonb | no |  |  | Respuesta normalizada. |  |
| `obtenida_en` | timestamp with time zone | no |  |  | Fecha de obtención. |  |
| `vigente_hasta` | timestamp with time zone | no |  |  | Fin de vigencia. |  |

Restricciones e índices parciales:

- única (servicio, clave)

## `cambio_norma`

Registro de cada cambio de norma de citación de un caso (T07).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id | Caso afectado. |  |
| `norma_anterior` | varchar(20) | no |  |  | Norma antes del cambio. |  |
| `norma_nueva` | varchar(20) | no |  |  | Norma después del cambio. |  |
| `cuenta_id` | uuid | no |  | FK cuenta.id | Cuenta del investigador que hizo el cambio. |  |
| `cambiado_en` | timestamp with time zone | no |  |  | Fecha y hora del cambio. |  |

## `caso`

Caso de estudio (estudiante o pareja), identificado solo por código (RN-12).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `codigo` | varchar(32) | no |  | única | Código único del caso (sin datos personales). | Clave de todas las exportaciones (RF-17) |
| `tipo_autoria` | texto (enumeración) | no | `individual`, `pareja` |  | individual o pareja. | Exportación de casos (RF-17) |
| `coleccion_cientifica_id` | uuid | no |  | FK coleccion.id | Colección científica del tema del caso. La personal es coleccion.caso_id. |  |
| `norma_citacion` | varchar(20) | no |  |  | Norma de citación del caso, de la lista cerrada configurada (D-12). |  |
| `estado` | texto (enumeración) | no | `habilitado`, `desactivado` |  | habilitado o desactivado. |  |
| `creado_en` | timestamp with time zone | no |  |  | Fecha y hora del alta. |  |
| `actualizado_en` | timestamp with time zone | no |  |  | Último cambio de estado o norma. |  |

Restricciones e índices parciales:

- codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,31}$'

## `coleccion`

Colección del corpus: guías (una), científica (una por tema) o personal (una por caso).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `tipo` | texto (enumeración) | no | `guias`, `cientifica`, `personal` |  | guias, cientifica o personal. |  |
| `tema` | varchar(80) | sí |  |  | Código del tema (solo en la colección científica). |  |
| `caso_id` | uuid | sí |  | FK caso.id | Caso dueño (solo en la colección personal). |  |
| `n_incluidas` | integer | no |  |  | Documentos incluidos. | Informe del corpus por tema (RF-15) |
| `n_excluidas` | integer | no |  |  | Referencias excluidas con motivo. | Informe del corpus por tema (RF-15) |
| `n_pendientes` | integer | no |  |  | Referencias pendientes de PDF. | Informe del corpus por tema (RF-15) |
| `creada_en` | timestamp with time zone | no |  |  | Fecha y hora de creación. |  |

Restricciones e índices parciales:

- (tipo = 'cientifica') = (tema IS NOT NULL)
- (tipo = 'personal') = (caso_id IS NOT NULL)
- n_incluidas >= 0 AND n_excluidas >= 0 AND n_pendientes >= 0
- uq_coleccion_caso_personal: único en (caso_id) donde tipo = 'personal'
- uq_coleccion_tema_cientifica: único en (tema) donde tipo = 'cientifica'
- uq_coleccion_unica_guias: único en (tipo) donde tipo = 'guias'

## `configuracion`

Parámetros funcionales versionados (RF-23). Se validan con Pydantic.

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `numero_version` | integer | no |  | única | Número de versión. |  |
| `parametros` | jsonb | no |  |  | Parámetros validados por app.administracion.parametros. |  |
| `comentario` | text | no |  |  | Motivo del cambio. |  |
| `vigente` | boolean | no |  |  | Vigente. |  |
| `congelada` | boolean | no |  |  | Congelada (RN-21). |  |
| `creada_en` | timestamp with time zone | no |  |  | Fecha y hora de creación. |  |

Restricciones e índices parciales:

- uq_configuracion_una_vigente: único en (vigente) donde vigente

## `cuenta`

Cuenta de acceso: A1 (caso) o A2 (investigador).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `codigo` | varchar(40) | no |  | única | Código de inicio de sesión. |  |
| `hash_contrasena` | varchar(255) | no |  |  | Hash Argon2id; nunca la contraseña. |  |
| `rol` | texto (enumeración) | no | `A1`, `A2` |  | A1 (caso) o A2 (investigador). |  |
| `caso_id` | uuid | sí |  | FK caso.id | Caso de la cuenta A1. |  |
| `intentos_fallidos` | integer | no |  |  | Fallos en la ventana actual. |  |
| `primer_fallo_en` | timestamp with time zone | sí |  |  | Inicio de la ventana de 15 minutos de fallos. |  |
| `bloqueada_hasta` | timestamp with time zone | sí |  |  | Fin del bloqueo temporal. |  |
| `contrasena_inicial_cambiada` | boolean | no |  |  | La contraseña inicial ya fue reemplazada. |  |
| `creada_en` | timestamp with time zone | no |  |  | Fecha y hora del alta. |  |

Restricciones e índices parciales:

- (rol = 'A1') = (caso_id IS NOT NULL)
- codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,39}$'
- intentos_fallidos >= 0

## `decision`

Decisión del caso sobre un resultado; un cambio crea otra fila (RN-08).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (resultado_id, caso_id) a resultado | Caso dueño (filtro obligatorio de aislamiento). | Contadores de decisiones por tipo y caso (RF-12) |
| `resultado_id` | uuid | no |  | FK compuesta (resultado_id, caso_id) a resultado | Resultado. |  |
| `opcion` | texto (enumeración) | no | `aceptar`, `modificar`, `rechazar`, `continuar`, `aportar` |  | aceptar, modificar, rechazar, continuar o aportar. | Contadores de decisiones por tipo y caso (RF-12) |
| `decidida_en` | timestamp with time zone | no |  |  | Fecha y hora de la decisión. |  |
| `decision_reemplazada_id` | uuid | sí |  | FK decision.id | Decisión anterior a la que reemplaza (se conserva). |  |

## `documento`

Documento indexado en una colección, con metadatos bibliográficos (Fase 1, 18.2).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `coleccion_id` | uuid | no |  | FK coleccion.id | Colección a la que pertenece. |  |
| `titulo` | text | sí |  |  | Título de la obra. |  |
| `autores` | jsonb | no |  |  | Autores de la obra publicada (metadato bibliográfico, no participantes). |  |
| `anio` | integer | sí |  |  | Año de publicación. |  |
| `doi` | varchar(255) | sí |  |  | DOI normalizado. |  |
| `revista_editorial` | text | sí |  |  | Revista (artículos) o editorial (libros). |  |
| `isbn` | varchar(13) | sí |  |  | ISBN-10 o ISBN-13 sin guiones (libros, 18.9). |  |
| `idioma` | varchar(8) | sí |  |  | Idioma (ISO 639-1). |  |
| `licencia` | varchar(80) | sí |  |  | Licencia de uso. |  |
| `url_acceso_abierto` | text | sí |  |  | Mejor ubicación de acceso abierto. |  |
| `estado_oa` | texto (enumeración) | no | `gold`, `green`, `hybrid`, `bronze`, `closed`, `desconocido` |  | Estado de acceso abierto según Unpaywall. | Comprobación 5 de la verificación (acceso abierto, RNF-08) |
| `ruta_archivo` | text | sí |  |  | Ruta interna con nombre aleatorio, fuera de la carpeta pública; nula si se indexó solo el resumen de Crossref u OpenAlex (RF-13). |  |
| `huella_sha256` | varchar(64) | no |  |  | Huella SHA-256 del texto normalizado, para deduplicar (18.9). |  |
| `estado` | texto (enumeración) | no | `activo`, `retirado`, `incompleto` |  | activo, retirado o incompleto (un retirado deja de recuperarse, 18.9). |  |
| `motivo_estado` | text | sí |  |  | Motivo si está incompleto o retirado. |  |
| `origen` | texto (enumeración) | no | `ingesta`, `importacion_o1`, `aporte` |  | ingesta, importacion_o1 o aporte. |  |
| `num_paginas` | integer | sí |  |  | Páginas del PDF. |  |
| `creado_en` | timestamp with time zone | no |  |  | Fecha y hora de indexación. |  |
| `retirado_en` | timestamp with time zone | sí |  |  | Fecha y hora de retiro. |  |

Restricciones e índices parciales:

- anio IS NULL OR anio BETWEEN 1500 AND 2100
- huella_sha256 ~ '^[0-9a-f]{64}$'
- isbn IS NULL OR isbn ~ '^(97[89][0-9]{10}/[0-9]{9}[0-9X])$'
- única (coleccion_id, huella_sha256)

## `evento_tecnico`

Evento técnico por etapa: latencia, tokens, costo y error (separado del registro metodológico).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `solicitud_id` | uuid | sí |  | FK solicitud.id | Solicitud asociada, si la hay. |  |
| `etapa` | varchar(60) | no |  |  | Etapa (recuperacion, generacion, ...). |  |
| `inicio` | timestamp with time zone | no |  |  | Inicio de la etapa. | Monitoreo (RF-24) |
| `duracion_ms` | integer | no |  |  | Duración en milisegundos. | Latencia p95 (RNF-12) |
| `proveedor` | varchar(60) | sí |  |  | Proveedor usado. |  |
| `modelo` | varchar(120) | sí |  |  | Identificador fijo del modelo (RN-24). |  |
| `tokens_entrada` | integer | sí |  |  | Tokens de entrada. | Costos (RNF-24) |
| `tokens_salida` | integer | sí |  |  | Tokens de salida. | Costos (RNF-24) |
| `costo_estimado` | numeric(12, 6) | sí |  |  | Costo estimado en USD. | Tope de gasto y modo protegido (RN-22) |
| `error` | varchar(120) | sí |  |  | Tipo de error, sin contenido. | Tasa de errores (RF-24) |

## `fragmento`

Fragmento IMRaD de un documento, con vector denso y texto léxico.

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `documento_id` | uuid | no |  | FK documento.id | Documento de origen. |  |
| `coleccion_id` | uuid | no |  | FK coleccion.id | Colección (copiada del documento para filtrar la recuperación). |  |
| `orden` | integer | no |  |  | Posición del fragmento en el documento. |  |
| `texto` | text | no |  |  | Texto limpio del fragmento. |  |
| `seccion_normalizada` | texto (enumeración) | no | `resumen`, `introduccion`, `metodos`, `resultados`, `discusion`, `conclusiones`, `otra` |  | Sección IMRaD. |  |
| `seccion_original` | text | sí |  |  | Título de la sección tal como aparece en el PDF. |  |
| `pagina_inicio` | integer | sí |  |  | Página inicial. |  |
| `pagina_fin` | integer | sí |  |  | Página final. |  |
| `tokens` | integer | no |  |  | Número de tokens del fragmento. |  |
| `embedding` | vector(1024) | sí |  |  | Vector bge-m3 normalizado (1 024). |  |
| `texto_lexico` | tsvector | no |  |  | Vector léxico tsvector con configuración simple, generado desde el texto. |  |
| `creado_en` | timestamp with time zone | no |  |  | Fecha y hora de creación. |  |

Restricciones e índices parciales:

- pagina_inicio IS NULL OR pagina_fin IS NULL OR pagina_inicio <= pagina_fin
- única (documento_id, orden)

## `fragmento_recuperado`

Fragmento recuperado para una solicitud, con sus puntajes (RF-10).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). | M2, M3 |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (solicitud_id, caso_id) a solicitud | Caso dueño (filtro obligatorio de aislamiento). | M2, M3 |
| `solicitud_id` | uuid | no |  | FK compuesta (solicitud_id, caso_id) a solicitud | Solicitud. | M2, M3 |
| `fragmento_id` | uuid | no |  | FK fragmento.id | Fragmento del corpus. | M2, M3 |
| `identificador_visible` | varchar(8) | no |  |  | F1 a Fn, citable por el agente. | M2, M3 |
| `puntaje_denso` | float | sí |  |  | Similitud coseno. | M2, M3 |
| `puntaje_lexico` | float | sí |  |  | Puntaje léxico. | M2, M3 |
| `puntaje_fusionado` | float | sí |  |  | Fusión por rangos recíprocos. | M2, M3 |
| `puntaje_reranking` | float | sí |  |  | Puntaje del reordenador normalizado entre 0 y 1 (sigmoide). | M2, M3; Suficiencia, paso 1 (tau, RF-10) |
| `posicion` | integer | no |  |  | Posición final tras el reranking. | M2, M3 |
| `pertinencia_evaluador` | boolean | sí |  |  | Juicio del modelo evaluador: el fragmento es pertinente a la consulta. | M2, M3 |
| `pertinencia_humana` | boolean | sí |  |  | Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25). | M2, M3 |

Restricciones e índices parciales:

- identificador_visible ~ '^F[1-9][0-9]*$'
- única (solicitud_id, identificador_visible)

## `fuente_aportada`

Fuente aportada por el caso tras una abstención (RF-13).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (solicitud_id, caso_id) a solicitud | Caso dueño (filtro obligatorio de aislamiento). |  |
| `solicitud_id` | uuid | no |  | FK compuesta (solicitud_id, caso_id) a solicitud | Solicitud con abstención que motivó el aporte. | M1 (lo resuelto solo tras un aporte cuenta como no cubierto; se reporta aparte) |
| `datos_bibliograficos` | jsonb | no |  |  | Título, autores de la obra y año declarados por el caso. |  |
| `doi` | varchar(255) | sí |  |  | DOI declarado. |  |
| `existencia` | texto (enumeración) | no | `confirmada`, `no_localizada`, `no_comprobable` |  | confirmada, no_localizada o no_comprobable (RN-18). |  |
| `metodo_existencia` | texto (enumeración) | sí | `doi`, `metadatos` |  | doi o metadatos. |  |
| `coherencia` | texto (enumeración) | no | `coherente`, `parcial`, `no_coherente`, `no_evaluada` |  | Coherencia con la afirmación (informativa). |  |
| `documento_id` | uuid | sí |  | FK documento.id | Documento indexado en la colección personal, si existe. |  |
| `aportada_en` | timestamp with time zone | no |  |  | Fecha y hora del aporte. |  |

## `resultado`

Salida estructurada de un agente por intento (RN-05).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). | M5 |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (solicitud_id, caso_id) a solicitud | Caso dueño (filtro obligatorio de aislamiento). | M5 |
| `solicitud_id` | uuid | no |  | FK compuesta (solicitud_id, caso_id) a solicitud | Solicitud. | M5 |
| `intento` | integer | no |  |  | 1 o 2 (un solo reintento). | M5 |
| `salida` | jsonb | sí |  |  | Salida estructurada validada por tipo. | M5 |
| `etiqueta` | texto (enumeración) | sí | `verificada`, `con_advertencias`, `sin_evidencia_suficiente` |  | verificada, con_advertencias o sin_evidencia_suficiente. | M5; Distribución de etiquetas (RF-25) |
| `advertencias` | jsonb | no |  |  | Comprobaciones fallidas que se entregan con la etiqueta con_advertencias (6.7). | M5 |
| `abstencion` | boolean | no |  |  | El agente se abstuvo. | M5; M1 (las abstenciones solo cuentan en la cobertura) |
| `creado_en` | timestamp with time zone | no |  |  | Fecha y hora de generación. | M5 |
| `relevancia_evaluador` | float | sí |  |  | Juicio del modelo evaluador, 0 a 1: el resultado atiende lo solicitado. | M5 |
| `relevancia_humana` | float | sí |  |  | Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la concordancia. | M5 |

Restricciones e índices parciales:

- (relevancia_evaluador IS NULL OR relevancia_evaluador BETWEEN 0 AND 1) AND (relevancia_humana IS NULL OR relevancia_humana BETWEEN 0 AND 1)
- intento IN (1, 2)
- única (id, caso_id)
- única (solicitud_id, intento)

## `sesion`

Sesión de navegador (8 h absolutas, 60 min de inactividad, dos por cuenta).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `cuenta_id` | uuid | no |  | FK cuenta.id | Cuenta dueña. |  |
| `huella_token` | varchar(64) | no |  | única | SHA-256 del token de la cookie; el token no se guarda. |  |
| `creada_en` | timestamp with time zone | no |  |  | Inicio de la sesión. |  |
| `ultima_actividad_en` | timestamp with time zone | no |  |  | Última petición autenticada. |  |
| `expira_en` | timestamp with time zone | no |  |  | Expiración absoluta. |  |
| `cerrada_en` | timestamp with time zone | sí |  |  | Cierre o invalidación. |  |
| `motivo_cierre` | varchar(40) | sí |  |  | cierre, inactividad, expiracion, limite o contrasena. |  |

Restricciones e índices parciales:

- ix_sesion_activas_por_cuenta: índice en (cuenta_id, creada_en) donde cerrada_en IS NULL

## `solicitud`

Solicitud tipificada de un caso sobre una versión (RF-02).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (solicitud_origen_id, caso_id) a solicitud; FK compuesta (version_id, caso_id) a version_borrador | Caso dueño (filtro obligatorio de aislamiento). |  |
| `version_id` | uuid | no |  | FK compuesta (version_id, caso_id) a version_borrador | Versión del borrador sobre la que se pide (da el hito). | Uso mínimo por hito (tesis 6.2.2.2), unida a version_borrador.hito |
| `tipo` | texto (enumeración) | no | `revision_estructura`, `plan_tarea`, `revision_metodologica`, `propuesta_redaccion`, `busqueda_evidencia`, `verificacion_referencias` |  | Uno de los seis tipos (agente fijo por tipo, RN-02). | M1; Contadores de decisiones por tipo y caso (RF-12); arnés por tipo (RF-25) |
| `alcance_tipo` | texto (enumeración) | no | `seccion`, `hito`, `fragmento`, `consulta`, `version` |  | Alcance admitido por el tipo: seccion, hito, fragmento, consulta o version. | M5 |
| `alcance_ref` | text | sí |  |  | Identificador de sección o de párrafo, o texto de la consulta; nulo en los alcances hito y version, que toman la versión vigente completa. | M5; exportación (RF-17, excluible por RN-20) |
| `estado` | texto (enumeración) | no | `recibida`, `asignada`, `recuperando`, `generando`, `verificando`, `reintentando`, `entregada`, `no_atendida`, `rechazada` |  | Estado en la cola y entrega. | M1; estado visible (RF-22) |
| `motivo` | text | sí |  |  | Motivo de rechazo o de no atención. |  |
| `configuracion_id` | uuid | no |  | FK configuracion.id | Versión de configuración vigente al crearla (RNF-21). |  |
| `solicitud_origen_id` | uuid | sí |  | FK compuesta (solicitud_origen_id, caso_id) a solicitud | Solicitud original si es un reenvío. |  |
| `intentos_tecnicos` | integer | no |  |  | Reintentos técnicos ante el proveedor. |  |
| `creada_en` | timestamp with time zone | no |  |  | Fecha y hora de creación. | Latencia por solicitud (RNF-12); historial |
| `actualizada_en` | timestamp with time zone | no |  |  | Último cambio de estado. |  |
| `entregada_en` | timestamp with time zone | sí |  |  | Fecha y hora de entrega. | Latencia por solicitud (RNF-12) |
| `completitud_evaluador` | float | sí |  |  | Juicio del modelo evaluador, 0 a 1: lo recuperado reúne la evidencia necesaria. | M3 |
| `completitud_humana` | float | sí |  |  | Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la concordancia. | M3 |

Restricciones e índices parciales:

- (alcance_tipo IN ('consulta', 'fragmento', 'seccion')) = (alcance_ref IS NOT NULL)
- (completitud_evaluador IS NULL OR completitud_evaluador BETWEEN 0 AND 1) AND (completitud_humana IS NULL OR completitud_humana BETWEEN 0 AND 1)
- (tipo = 'revision_estructura' AND alcance_tipo IN ('seccion')) OR (tipo = 'plan_tarea' AND alcance_tipo IN ('hito')) OR (tipo = 'revision_metodologica' AND alcance_tipo IN ('seccion')) OR (tipo = 'propuesta_redaccion' AND alcance_tipo IN ('fragmento')) OR (tipo = 'busqueda_evidencia' AND alcance_tipo IN ('consulta', 'fragmento')) OR (tipo = 'verificacion_referencias' AND alcance_tipo IN ('version'))
- intentos_tecnicos BETWEEN 0 AND 3
- única (id, caso_id)
- ix_solicitud_cola: índice en (estado, creada_en) donde estado IN ('recibida', 'asignada', 'recuperando', 'generando', 'verificando', 'reintentando')

## `verificacion`

Verificación de un resultado por intento: seis comprobaciones en orden (Fase 1, 6.7). En las comprobaciones, nulo significa que no aplica al tipo.

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id; FK compuesta (resultado_id, caso_id) a resultado | Caso dueño (filtro obligatorio de aislamiento). |  |
| `resultado_id` | uuid | no |  | FK compuesta (resultado_id, caso_id) a resultado | Resultado. |  |
| `intento` | integer | no |  |  | Intento verificado (1 o 2). | M4 (se toma la verificación final de cada resultado) |
| `formato_ok` | boolean | no |  |  | Comprobación 1: la salida cumple el esquema del tipo. |  |
| `limites_ok` | boolean | sí |  |  | Comprobación 2: límites de extensión y ausencia de reescritura. |  |
| `citas_ok` | boolean | sí |  |  | Comprobación 3: toda cita es un fragmento recuperado (F1 a Fn). |  |
| `n_fuentes_citadas` | integer | no |  |  | Comprobación 4: fuentes entregadas cuya existencia se comprobó. | M6 |
| `n_fuentes_confirmadas` | integer | no |  |  | Comprobación 4: fuentes localizadas por DOI o por metadatos. | M6 |
| `n_fuentes_no_comprobables` | integer | no |  |  | Comprobación 4: fuentes no comprobables porque un servicio no respondió (RN-18); no cuentan como no localizadas. | M6 (se informan aparte) |
| `metodo` | texto (enumeración) | sí | `doi`, `metadatos`, `mixto` |  | Comprobación 4: doi, metadatos o mixto; nulo si no se confirmó ninguna. | M6 |
| `acceso_abierto_ok` | boolean | sí |  |  | Comprobación 5: las fuentes recomendadas son de acceso abierto. |  |
| `fidelidad` | float | sí |  |  | Comprobación 6: afirmaciones respaldadas sobre total. | M4 |
| `umbral_fidelidad` | float | sí |  |  | Umbral aplicado (de la configuración). |  |
| `afirmaciones_total` | integer | sí |  |  | Afirmaciones. |  |
| `afirmaciones_respaldadas` | integer | sí |  |  | Respaldadas. |  |
| `afirmaciones_no_respaldadas` | integer | sí |  |  | No respaldadas. |  |
| `afirmaciones_contradichas` | integer | sí |  |  | Contradichas. |  |
| `motivos_falla` | jsonb | no |  |  | Motivos usados en el reintento. |  |
| `superada` | boolean | no |  |  | Todas las comprobaciones aplicables superadas. |  |
| `modelo_evaluador` | varchar(120) | sí |  |  | Identificador fijo del modelo evaluador (RN-24). |  |
| `verificada_en` | timestamp with time zone | no |  |  | Fecha y hora de la verificación. |  |

Restricciones e índices parciales:

- (n_fuentes_confirmadas = 0) = (metodo IS NULL)
- NOT superada OR (formato_ok AND limites_ok IS NOT FALSE AND citas_ok IS NOT FALSE AND acceso_abierto_ok IS NOT FALSE AND n_fuentes_confirmadas = n_fuentes_citadas AND (fidelidad IS NULL OR umbral_fidelidad IS NULL OR fidelidad >= umbral_fidelidad))
- fidelidad IS NULL OR fidelidad BETWEEN 0 AND 1
- intento IN (1, 2)
- n_fuentes_citadas >= 0 AND n_fuentes_confirmadas >= 0 AND n_fuentes_no_comprobables >= 0 AND n_fuentes_confirmadas + n_fuentes_no_comprobables <= n_fuentes_citadas
- única (resultado_id, intento)

## `version_borrador`

Versión del borrador .docx cargada por un caso en un hito (RF-01, RN-09).

Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).

| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | no |  | PK | Identificador interno (UUID). |  |
| `caso_id` | uuid | no |  | FK caso.id | Caso dueño. |  |
| `hito` | varchar(40) | no |  |  | Código del hito, del catálogo de la configuración versionada. | Uso mínimo por hito (tesis 6.2.2.2); historial (RF-14) |
| `cargada_en` | timestamp with time zone | no |  |  | Fecha y hora de la carga. | Historial (RF-14); exportación (RF-17) |
| `ruta_archivo` | text | no |  |  | Ruta interna con nombre aleatorio, fuera de la carpeta pública. |  |
| `huella_sha256` | varchar(64) | no |  |  | Huella SHA-256 del archivo. |  |
| `tamano_bytes` | bigint | no |  |  | Tamaño del archivo. |  |
| `vigente` | boolean | no |  |  | Versión vigente de su hito. |  |
| `secciones` | jsonb | sí |  |  | Secciones detectadas con identificadores estables (T12). |  |
| `metodo_deteccion` | texto (enumeración) | sí | `estilos`, `manual` |  | estilos o manual. |  |

Restricciones e índices parciales:

- huella_sha256 ~ '^[0-9a-f]{64}$'
- única (id, caso_id)
- uq_version_borrador_vigente_por_hito: único en (caso_id, hito) donde vigente

## Ficha de métricas: columnas que alimentan cada una

| Código | Métrica | Dimensión | Umbral | Columnas |
| --- | --- | --- | --- | --- |
| M1 | Cobertura del corpus documental | Calidad de la recuperación | Se describe | `fuente_aportada.solicitud_id`, `resultado.abstencion`, `solicitud.tipo`, `solicitud.estado` |
| M2 | Precisión contextual de los fragmentos | Calidad de la recuperación | 0.80 o más | `fragmento_recuperado.id`, `fragmento_recuperado.caso_id`, `fragmento_recuperado.solicitud_id`, `fragmento_recuperado.fragmento_id`, `fragmento_recuperado.identificador_visible`, `fragmento_recuperado.puntaje_denso`, `fragmento_recuperado.puntaje_lexico`, `fragmento_recuperado.puntaje_fusionado`, `fragmento_recuperado.puntaje_reranking`, `fragmento_recuperado.posicion`, `fragmento_recuperado.pertinencia_evaluador`, `fragmento_recuperado.pertinencia_humana` |
| M3 | Completitud de la recuperación | Calidad de la recuperación | Se describe | `fragmento_recuperado.id`, `fragmento_recuperado.caso_id`, `fragmento_recuperado.solicitud_id`, `fragmento_recuperado.fragmento_id`, `fragmento_recuperado.identificador_visible`, `fragmento_recuperado.puntaje_denso`, `fragmento_recuperado.puntaje_lexico`, `fragmento_recuperado.puntaje_fusionado`, `fragmento_recuperado.puntaje_reranking`, `fragmento_recuperado.posicion`, `fragmento_recuperado.pertinencia_evaluador`, `fragmento_recuperado.pertinencia_humana`, `solicitud.completitud_evaluador`, `solicitud.completitud_humana` |
| M4 | Fidelidad respuesta-fuente | Fidelidad de la respuesta | 0.90 o más | `verificacion.intento`, `verificacion.fidelidad` |
| M5 | Relevancia de la respuesta | Fidelidad de la respuesta | Se describe | `resultado.id`, `resultado.caso_id`, `resultado.solicitud_id`, `resultado.intento`, `resultado.salida`, `resultado.etiqueta`, `resultado.advertencias`, `resultado.abstencion`, `resultado.creado_en`, `resultado.relevancia_evaluador`, `resultado.relevancia_humana`, `solicitud.alcance_tipo`, `solicitud.alcance_ref` |
| M6 | Tasa de referencias no verificables | Fidelidad de la respuesta | 0.05 o menos | `verificacion.n_fuentes_citadas`, `verificacion.n_fuentes_confirmadas`, `verificacion.n_fuentes_no_comprobables`, `verificacion.metodo` |

Otros datos exportados que no son métricas de la ficha:

- Contadores de decisiones por tipo y caso (RF-12): `decision.opcion` agrupada por `solicitud.tipo` y `decision.caso_id`.
- Uso mínimo por hito (tesis 6.2.2.2): `solicitud` unida a `version_borrador.hito`; se reporta, no bloquea.

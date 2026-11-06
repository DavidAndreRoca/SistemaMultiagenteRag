# Insumos para cerrar T04 y preparar T11

**Fecha:** 6 de noviembre de 2026. **Para:** Claude Code. **Fuentes:** tesis *Taller de Investigacion 03-11-2026* (6.2.2, 6.2.5, 6.2.7.2, Tabla 22 del procedimiento de métricas) y `docs/especificacion-fase1/`.

La especificación completa de la Fase 1 está ahora en `docs/especificacion-fase1/` (archivos 01 a 07). Los apartados que pediste:

- Columnas de `verificacion`: `02_funcionalidades.md`, apartado 6.7 (campo "Salida").
- Metadatos de `documento` y `fragmento`: `06_rag_seguridad.md`, apartado 18.2.
- Tipos de alcance: `03_requisitos.md`, RF-02, y la tabla 3 de este documento.
- Parámetros de recuperación: `06_rag_seguridad.md`, apartado 18.6.

Contrasta las tablas provisionales con esos apartados. Si algo difiere, corrígelo con una migración nueva y registra la diferencia en `docs/decisiones/`.

---

## 1. Ficha de registro de métricas (para la columna "Alimenta" del diccionario)

La ficha registra seis métricas normalizadas de 0 a 1, en dos dimensiones. Se calculan **a partir del registro exportado** (RF-17), no se guardan como columnas propias. El diccionario debe indicar qué columnas alimentan cada una.

| Código | Métrica | Dimensión | Procedimiento de cálculo (tesis, Tabla 22) | Umbral | Columnas que la alimentan |
| --- | --- | --- | --- | --- | --- |
| M1 | Cobertura del corpus documental | Calidad de la recuperación | Solicitudes con evidencia pertinente en el corpus sobre el total de solicitudes que consultan el corpus. Las resueltas solo tras un aporte de fuente cuentan como no cubiertas; el aporte se reporta aparte | Se describe | `solicitud.tipo`, `solicitud.estado`, `resultado.abstencion`, `fuente_aportada.solicitud_id` |
| M2 | Precisión contextual de los fragmentos | Calidad de la recuperación | Promedio, por solicitud, de la proporción de fragmentos recuperados pertinentes al contexto de la consulta | 0.80 o más | `fragmento_recuperado.*` y una columna de **pertinencia evaluada** por fragmento (véase la nota) |
| M3 | Completitud de la recuperación | Calidad de la recuperación | En el conjunto de prueba: evidencia de referencia presente en lo recuperado. En O2: juicio del evaluador sobre si lo recuperado reúne la evidencia necesaria | Se describe | `fragmento_recuperado.*`; en O2, una columna de **juicio de completitud** por solicitud (véase la nota) |
| M4 | Fidelidad respuesta-fuente | Fidelidad de la respuesta | Afirmaciones respaldadas sobre el total, tomada de la verificación **final** de cada resultado | 0.90 o más | `verificacion.fidelidad`, `verificacion.intento` |
| M5 | Relevancia de la respuesta | Fidelidad de la respuesta | Grado en que cada resultado atiende lo solicitado, promediado sobre los resultados con propuesta | Se describe | `resultado.*`, `solicitud.alcance`, y una columna de **relevancia evaluada** por resultado (véase la nota) |
| M6 | Tasa de referencias no verificables | Fidelidad de la respuesta | Referencias entregadas por el sistema que no se localizaron por DOI ni por metadatos, sobre el total entregadas | 0.05 o menos | `verificacion.n_fuentes_citadas`, `verificacion.n_fuentes_confirmadas`, `verificacion.metodo` |

**Nota sobre M2, M3 y M5.** La tesis exige que la pertinencia, la completitud y la relevancia las juzgue un modelo evaluador sobre todas las solicitudes, con una muestra humana del 20 al 30 % (6.2.7.2). Ese juicio necesita dónde guardarse. Propuesta:
- `fragmento_recuperado.pertinente` (booleano, nulo hasta que se evalúe), con `pertinencia_fuente` (`evaluador` o `humano`);
- `resultado.relevancia` (decimal 0 a 1, nulo hasta que se evalúe);
- `solicitud.completitud` (decimal 0 a 1, nulo hasta que se evalúe).

Las columnas se llenan en T38 (arnés) y en el cálculo de O2, no durante la solicitud. Si prefieres guardar estos juicios en una tabla aparte, de evaluación, también vale; lo que no puede faltar es el dato.

**Otros datos del registro, que no son métricas de la ficha pero se exportan:**
- Contadores de propuestas aceptadas, modificadas y rechazadas: `decision.opcion` agrupada por tipo y caso.
- Uso mínimo orientativo, una solicitud por hito: `solicitud` unida a `version_borrador.hito`.

---

## 2. Catálogo de hitos

Son los ocho hitos con los que se elabora un artículo en el programa de titulación (tesis, 6.2.2, nivel principal del BPMN). Cada caso los recorre dos veces en 2027-1: en O1 (semanas 1 a 10) y en O2 (semanas 12 a 22). Los hitos no tienen semana fija.

| Orden | Código | Nombre | Contenido |
| --- | --- | --- | --- |
| 1 | `avance_1` | Avance 1 | Planteamiento |
| 2 | `avance_2` | Avance 2 | Metodología y estado del arte |
| 3 | `entrega_plan` | Entrega final del plan | Plan de tesis completo |
| 4 | `avance_3` | Avance 3 | Introducción |
| 5 | `avance_4` | Avance 4 | Metodología |
| 6 | `avance_5` | Avance 5 | Resultados |
| 7 | `avance_6` | Avance 6 | Discusión y conclusiones |
| 8 | `entrega_final` | Entrega final del artículo | Artículo completo |

- **Uso mínimo orientativo:** 1 solicitud por hito. Se reporta, no bloquea nada.
- **Dónde vive:** en la configuración versionada (`configuracion.parametros.hitos`), no como tabla rígida, para poder ajustarlo si el programa cambia.
- **Pendiente:** las instrucciones oficiales de cada hito (para el plan de tarea, RF-05) llegan con el corpus de guías en T22. El catálogo no depende de ellas.

---

## 3. Tipos de solicitud y alcance

| Tipo (código) | Agente | Caso de uso | Alcance admitido |
| --- | --- | --- | --- |
| `revision_estructura` | D1 | CU-03 | `seccion` |
| `plan_tarea` | D1 | CU-04 | `hito` (sobre la versión vigente completa) |
| `revision_metodologica` | D2 | CU-05 | `seccion` |
| `propuesta_redaccion` | D3 | CU-06 | `fragmento` (un párrafo de hasta unas 250 palabras) |
| `busqueda_evidencia` | D4 | CU-07 | `consulta` (texto libre) o `fragmento` (afirmación a sustentar) |
| `verificacion_referencias` | D4 | CU-08 | `version` (lista de referencias y citas de la versión) |

RF-02 define tres alcances explícitos (sección, fragmento, consulta), y la consulta libre es solo para CU-07. Los alcances `hito` y `version` se deducen de RF-05 y RF-09, que trabajan sobre la versión vigente y no sobre una parte elegida. Columnas sugeridas en `solicitud`: `alcance_tipo` (los cinco valores anteriores) y `alcance_ref` (identificador de sección o párrafo, o texto de la consulta).

---

## 4. Valores iniciales de configuración

Van en la migración semilla de `configuracion` como **versión 1, provisional**. T34 los recalibra.

| Parámetro | Valor inicial | Origen |
| --- | --- | --- |
| `k_denso` | 30 | Fase 1, 18.6 |
| `k_lexico` | 30 | Fase 1, 18.6 |
| `rrf_constante` | 60 | Fase 1, 18.6 |
| `n_reranking` | 8 | Fase 1, 18.6 |
| `suficiencia_n` | 2 | Fase 1, 18.6 |
| `suficiencia_tau` | 0.5 | **Propuesta provisional**: la Fase 1 dejó tau "a calibrar". El valor se aplica sobre el puntaje del reranker normalizado entre 0 y 1 (función sigmoide sobre la salida del modelo). T34 lo fija con la curva de precisión del conjunto de prueba |
| `ventana_tokens` | 300 a 450 (objetivo 400) | Fase 1, 18.4 |
| `umbral_fidelidad` | 0.90 | Fase 1, 6.7; tesis 6.2.7.2 |
| `limite_palabras_d3` | 250 | RF-07 |
| `factor_extension_d3` | 1.2 | RF-07 |
| `limite_reescritura_palabras` | 40 | Fase 1, 6.3 (a calibrar) |
| `normas_citacion` | `["ieee", "apa7"]` | D-12 (lista pendiente de confirmación) |
| `norma_por_defecto` | `ieee` | D-12 |
| `tamano_max_docx_mb` | 15 | RN-16 |
| `tamano_max_pdf_mb` | 25 | RN-16 |
| `paginas_max_pdf` | 60 | RN-16 |
| `uso_minimo_por_hito` | 1 | Tesis 6.2.2.2 |
| `hitos` | Tabla 2 de este documento | Tesis 6.2.2 |

Los identificadores de modelo y sus precios se agregan en T17. No los inventes antes.

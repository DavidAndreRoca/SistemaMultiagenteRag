# T19-01. Agente D4 de búsqueda de evidencia

**Fase:** T19 (Fase 3). **Fecha:** 24 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T19. Especificación de la Fase 1:
- RF-08 y CU-07 (evidencia con referencia asociada);
- RF-21 en parte (citas navegables);
- 7.2 (consultas ambiguas o fuera de alcance);
- RN-04 (abstención), RN-14 y RNF-08 (acceso abierto), RN-17 (ningún modelo escribe referencias);
- CP-05 y CP-11.

Decisión del equipo del 24 de noviembre de 2026 ("paquete recomendado"): apartado 8.

## 1. Instrucción del agente (versión 1)

`backend/instrucciones/evidencia/v1.md`, registrada en `registro.json` con su huella. Pide la salida de la tabla 15, `{respuesta:[{afirmacion, citas}], evidencia_divergente, notas_para_el_estudiante}`:
- cada afirmación lleva al menos una cita `F1` a `Fn` de los fragmentos entregados, y nada más;
- si las fuentes no coinciden, las posturas van en `evidencia_divergente`, tal como aparecen, sin elegir por el estudiante;
- el modelo no escribe referencias ni enlaces: el esquema no tiene esos campos (RN-17).

Las fuentes recomendadas y sus referencias las arma el sistema después (apartado 5).

## 2. Validación previa de la consulta (7.2)

Antes de crear trabajo, `app/agentes/validacion_consulta.py` decide si la consulta se atiende. Hay dos filtros, en este orden:

1. **Reglas, sin modelo:**
   - `muy_corta`: menos de `consulta_min_palabras` palabras (5);
   - `muy_larga`: más de `consulta_max_caracteres` caracteres (1.000);
   - `fuera_de_alcance`: pedidos de redactar, escribir, corregir, traducir o resumir una pieza del artículo ("redacta la introducción", "escribe mi artículo");
   - `ambigua`: consultas que empiezan sin objeto ("¿qué opinas?", "ayúdame", "algo sobre") o con menos de 3 palabras con contenido.
2. **Clasificador barato de pertinencia:** la similitud de la consulta (bge-m3 local) con el fragmento más cercano de las fuentes del caso. Si no llega a `pertinencia_umbral` (0,55), es `fuera_de_alcance`. No se llama al modelo de lenguaje.

Medición con el corpus provisional (bge-m3 real, similitud con el fragmento más cercano):

| Consultas | Similitud |
|---|---|
| Del tema del caso | 0,61 a 0,74 |
| Ajenas al proyecto | 0,36 a 0,49 |
| Del otro tema | 0,41 a 0,63 |

El umbral 0,55 deja pasar todas las del tema y corta todas las ajenas. Algunas del otro tema lo superan: comparten vocabulario (tecnología, educación), y para ellas decide la suficiencia (T16).

Una consulta rechazada:
- se guarda como solicitud `rechazada`, con su `motivo`, y no se encola;
- devuelve 422 `consulta_rechazada`, con un mensaje que explica qué se puede pedir y un ejemplo.

Los tres parámetros están en la configuración (migración 0014), no en el entorno.

## 3. Ruta directa y trabajo en segundo plano

No hay orquestador en el bloque 1, así que la solicitud es directa:
- `POST /caso/evidencias` (rol A1) valida, crea la solicitud y responde 202;
- el trabajo sigue en segundo plano, como en T15;
- la interfaz consulta `GET /caso/evidencias/{id}` cada 2 segundos.

Estados de la solicitud:
- recorre `recibida`, `recuperando` y `generando` hasta `entregada`, o `no_atendida` si falla el modelo (CP-07);
- si el servidor se reinicia a mitad de camino, la solicitud queda `no_atendida` con el motivo `interrumpida`.

Condiciones de la ruta:
- se necesita una versión vigente del borrador (409 si no hay);
- sin servicio de modelos configurado, la ruta da 503.

La matriz de autorización admite esos códigos para el propio caso (`admite_propio`). Otro caso recibe 404.

## 4. Comprobaciones y reintento

Al generar se ejecutan:
- la comprobación 1, de esquema (T18);
- la comprobación 3, de citas a `fragmento_recuperado` (T18);
- la comprobación 5 nueva, de acceso abierto.

La comprobación 5 falla si alguna afirmación cita un fragmento de un documento sin estado OA comprobado (`gold`, `green`, `hybrid` o `bronze`).

El reintento con los motivos de la falla llega en T30, con el verificador. Hasta entonces, si una comprobación falla, la respuesta se entrega con la etiqueta "Con advertencias" y la lista de motivos. Si todas se superan, va sin etiqueta. CP-11 se cumple así: la fuente cerrada no aparece como recomendada, y si se cita, la verificación no se supera y se avisa.

## 5. Fuentes recomendadas y regla de acceso abierto (RN-14)

Las fuentes recomendadas son los documentos citados con estado OA comprobado y enlace de acceso abierto. El sistema construye su referencia en la norma del caso con el constructor de T18 (doi.org o CSL local), nunca el modelo. Un documento cerrado o sin comprobar puede citarse en la respuesta, marcado "Sin acceso abierto comprobado", pero nunca se recomienda.

**Completar el estado OA del corpus.** `python -m app.corpus.acceso_abierto --tema T --investigador I [--aplicar]` consulta Unpaywall (cliente y caché de T14) por cada documento con DOI cuyo estado no está comprobado, y guarda solo tres campos: el estado, el enlace y la licencia. No toca fragmentos ni vectores. Los resultados posibles son:
- si Unpaywall no responde, el documento se omite;
- si no conoce el DOI, el documento queda `desconocido`;
- un documento sin DOI no se consulta y queda sin recomendar.

**Corpus de desarrollo:** se respaldó antes de aplicar (`datos/respaldos/antes-de-acceso-abierto-2026-11-24.*`). Resultado:

| Tema | Con DOI | gold | hybrid | green | bronze | Sin registro |
|---|---|---|---|---|---|---|
| TEMA-1-IA-EDUCACION | 61 | 55 | 2 | 1 | 2 | 1 |
| TEMA-2-TRANSFORMACION-DIGITAL-MYPES | 25 | 17 | 4 | 2 | 0 | 2 |

Quedan 83 documentos con acceso abierto comprobado y 19 sin comprobar: 16 sin DOI y 3 que Unpaywall no conoce. Los 2.785 fragmentos no cambiaron. Las respuestas de Unpaywall quedaron en la caché de metadatos de T14 (`cache_metadatos`).

## 6. Pantalla

`frontend/src/paginas/Evidencia.tsx`, en `/panel/evidencia` y enlazada desde el panel del caso:
- un campo de consulta, el aviso de progreso y el motivo del rechazo tal como lo da la API;
- cada afirmación con sus citas desplegables (`<details>`): el fragmento, el título, la sección, las páginas, la marca de extracción incompleta y el enlace de acceso abierto (solo si está comprobado);
- la evidencia divergente, las notas y las fuentes recomendadas;
- en la abstención, "Sin evidencia suficiente" y la invitación a aportar una fuente (el aporte llega en T32).

La revisión automática de accesibilidad de Playwright no encuentra errores graves.

## 7. Comportamiento con el modelo real

`python -m app.agentes.evaluar_evidencia <conjunto> [--limite N] [--salida informe.json]` es la prueba bajo demanda. Corre en una transacción que siempre se revierte y no registra eventos. Recorre la recuperación, la suficiencia y la generación del agente, y cuenta:
- las citas fuera de lo recuperado;
- las fuentes cerradas recomendadas;
- las citas a fuentes sin OA comprobado.

Se ejecutó el 24 de noviembre de 2026 con Groq (`openai/gpt-oss-120b`) sobre 3 consultas por tema del conjunto de T16. El corpus de desarrollo ya tenía el estado OA completado. El informe está en `evaluacion/resultados/comportamiento-d4-t19.json`.

| Medida | Resultado |
|---|---|
| Consultas | 6 |
| Respuestas generadas | 4, con 2 a 4 afirmaciones cada una |
| Abstenciones | 2 (T1-02 y T1-03), por el juicio del modelo en el segundo paso de la suficiencia |
| Errores del proveedor | 0 |
| Citas fuera de los fragmentos recuperados | **0** (la comprobación 3 se superó en las 4) |
| Fuentes cerradas recomendadas | **0** |
| Citas a fuentes sin OA comprobado | 4, todas en T2-03, de documentos del tema 2 que siguen sin estado OA comprobado |

En el flujo real, T2-03 se entregaría "Con advertencias" (comprobación 5) y esas fuentes no se recomendarían. Es el comportamiento de CP-11.

Cada consulta generada tardó entre 88 y 122 s, sobre todo por la espera del límite por minuto. La pantalla avisa que puede tardar uno o dos minutos.

Las dos abstenciones son de consultas con fragmentos recuperados. Si el juicio del modelo es demasiado estricto, se revisa con el conjunto del equipo (T34), no en T19.

**Límite por minuto de Groq (riesgo R-01).** Cada consulta hace dos llamadas al modelo, la suficiencia y la generación, y la cuota es de 8.000 tokens por minuto. El limitador reserva la estimación de entrada más `max_tokens_salida` (2.048). Con la espera máxima por defecto (30 s, `ESPERA_MAXIMA_LIMITADOR_S`), la segunda llamada falla por límite de tasa. En la primera ejecución, 3 de 6 consultas no pudieron atenderse por esto. Con 65 s, ninguna. Como D4 trabaja en segundo plano, se recomienda `ESPERA_MAXIMA_LIMITADOR_S=65` (una ventana completa) mientras Groq sea el único proveedor. No cambia el valor por defecto de T17, que vale para llamadas en primer plano.

## 8. Decisiones del equipo (24 de noviembre de 2026)

1. **Pertinencia:** reglas más similitud con bge-m3 local contra el corpus del caso, sin modelo de lenguaje.
2. **Ejecución:** en segundo plano, con consulta del avance, como T15.
3. **Sin reintento hasta T30:** si una comprobación falla, la respuesta se entrega "Con advertencias", con la lista de motivos.
4. **Acceso abierto:** un comando que completa solo los metadatos OA desde Unpaywall para los documentos con DOI, tras un respaldo. Un documento sin DOI no se recomienda.

## 9. Insumos del equipo y lo que queda sin validar con datos reales

T19 no necesita borradores con errores introducidos ni la hoja de errores: esos insumos son de T20, T23, T24, T26 y T27. Necesita:

1. **La revisión de `evaluacion/conjuntos/recuperacion-t16.json`**, que es un borrador escrito por el asistente.
2. **`evaluacion/conjuntos/validacion-consultas-t19.json`**, con unas 15 consultas aceptadas y 15 rechazadas, redactadas por el equipo. Cada entrada tiene estos campos:
   - `id`;
   - `consulta`;
   - `esperado` (`aceptada` o `rechazada`);
   - `motivo` (`muy_corta`, `ambigua` o `fuera_de_alcance`) si se rechaza;
   - `nota`, opcional.

   El archivo actual es un borrador de 16 entradas. Las que llevan `"detecta": "pertinencia"` las decide el clasificador y no las reglas.

**Actualización del 25 de noviembre de 2026:** el equipo entregó el conjunto de validación, con 30 consultas y el campo `tema` agregado. Con reglas y pertinencia reales acierta en las 30 (ESTADO, apartado 22.8). La revisión del conjunto de T16 tiene 13 consultas revisadas y 17 en segunda ronda.

Sin validar con datos reales:
- el comportamiento del agente sobre el conjunto revisado completo, que solo se probó en un subconjunto (apartado 7);
- los contratos de DeepSeek y Gemini, porque faltan sus claves.

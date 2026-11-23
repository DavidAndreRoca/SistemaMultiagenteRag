# T18-01. Contrato común de agentes, comprobaciones 1 y 3 y constructor de referencias

**Fase:** T18 (Fase 3). **Fecha:** 23 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T18. Especificación de la Fase 1:
- 6.1 (contrato común) y tablas 12 a 16;
- RN-17: ningún modelo escribe referencias;
- D-07: comprobaciones 1 y 3 tempranas;
- D-12: normas `ieee`, `apa7` y `vancouver`;
- n.° 8 del plan: sin memoria entre solicitudes.

Decisión del equipo del 23 de noviembre de 2026: apartado 5.

## 1. Estado de entrada (6.1)

`EstadoAgente` es el estado del grafo que recibe todo agente:
- `solicitud_id`, `caso_id`, `tipo`, `alcance` (el texto de la sección, el párrafo o la consulta), `hito`, `tema_id`, `version_id`;
- `intento` (1 o 2) y, en el intento 2, `motivos_falla` de la verificación anterior.

Es inmutable y no lleva nada más: ni el historial del caso, ni otras solicitudes, ni otras versiones.

## 2. Clase base de agente

`Agente` (en `app/agentes/contrato.py`) hace siempre lo mismo:
1. **Recupera y decide la suficiencia** con `ServicioEvidencia.preparar` de T16, con el contexto del caso y la consulta que arma cada agente a partir de su alcance.
2. **Se abstiene si la evidencia no alcanza:** devuelve la abstención sin llamar al modelo (RN-04).
3. **Genera** con el adaptador de T17: la instrucción vigente del agente, el alcance y los fragmentos `F1` a `Fn` como datos (RN-23) y el esquema de su tipo. En el intento 2, la tarea incluye los motivos de la falla.
4. **Devuelve** la salida validada, la evidencia y los datos del modelo.

Cada agente concreto (D1 a D4, desde T19) define:
- los tipos que atiende;
- el nombre de su instrucción;
- la consulta para la recuperación;
- cómo presenta su alcance.

**Sin memoria:** la clase base no recibe ni consulta el historial del caso. Una solicitud se resuelve solo con su estado y la evidencia recuperada. Una prueba lo comprueba: con otra solicitud previa del mismo caso, lo que se envía al modelo no cambia.

## 3. Esquemas de salida (tablas 12 a 15)

`app/agentes/esquemas.py` define un modelo Pydantic estricto por tipo, sin campos extra:

| Tipo | Esquema | Campos |
| --- | --- | --- |
| `revision_estructura` (D1) | `RevisionEstructura` | `hallazgos`, `fortalezas`, `notas_para_el_estudiante` |
| `plan_tarea` (D1) | `PlanTarea` | `hito`, `tareas` (`orden`, `tarea`, `criterio_de_logro`, `citas`), `notas_para_el_estudiante` |
| `revision_metodologica` (D2) | `RevisionMetodologica` | `hallazgos`, `preguntas_al_estudiante`, `notas_para_el_estudiante` |
| `propuesta_redaccion` (D3) | `PropuestaRedaccion` | `original`, `propuesta`, `cambios` (`tipo`, `antes`, `despues`, `razon`, `citas`), `notas_para_el_estudiante` |
| `busqueda_evidencia` (D4) | `BusquedaEvidencia` | `respuesta` (`afirmacion`, `citas`), `evidencia_divergente`, `notas_para_el_estudiante` |
| `verificacion_referencias` (D4) | `VerificacionReferencias` | Salida del sistema, determinista (T20): `referencias`, `citas_sin_entrada` y `entradas_no_citadas` |

- **Hallazgo:** `indicador` (los indicadores de la tabla del agente), `ubicacion` (identificador de párrafo o sección del borrador), `descripcion`, `severidad` (`baja`, `media` o `alta`), `recomendacion` y `citas`.
- **Nombres:** la salida común usa `notas_para_el_estudiante` (6.1), aunque las tablas digan `notas`.
- **Citas:** son identificadores `F<n>`, al menos uno por afirmación, hallazgo, tarea o cambio.
- **Sin referencias en texto libre (RN-17):**
  - ningún esquema que produzca el modelo tiene un campo para referencias, fuentes o documentos;
  - las fuentes de `busqueda_evidencia` las calcula el sistema a partir de los fragmentos citados (apartado 5);
  - `texto_original` de la verificación es la entrada del propio estudiante, extraída por el sistema (T20).

  Una prueba recorre los esquemas.
- **Extensión:** los textos tienen longitudes máximas. Los límites de extensión y la ausencia de reescritura son la comprobación 2, de T30.

## 4. Comprobaciones 1 y 3 (D-07)

Viven en `app/verificacion/comprobaciones.py`, fuera de los agentes, para que T30 las reutilice:

- **Comprobación 1, esquema del tipo:** valida la salida guardada (un `dict`) contra el esquema de su tipo. Devuelve los campos y los tipos de error, nunca los valores.
- **Comprobación 3, citas:** reúne todos los identificadores `F<n>`:
  - los de los campos `citas`;
  - los mencionados dentro de cualquier texto, como «[F9]».

  Exige que cada uno esté entre los fragmentos recuperados para esa solicitud (`fragmento_recuperado`). Una cita a `F9` cuando solo hay `F1` a `F8` la rechaza, con la lista de identificadores inexistentes.

## 5. Constructor de referencias y formateador CSL (decisión del equipo)

**Constructor de referencias** (`app/bibliografia/referencias.py`): para los identificadores citados en una solicitud, obtiene sus documentos, siempre filtrando por el caso, y arma una referencia por documento en la norma del caso. Ningún texto sale del modelo.
- **Con DOI:** la cita formateada por el registro del DOI (doi.org, cliente y caché de T14), en el estilo CSL de la norma.
- **Sin DOI, o si doi.org no responde:** el formateador CSL local, con los metadatos guardados del documento (título, autores, año, revista o editorial, idioma, DOI y URL de acceso abierto).
- **Resultado:** cada referencia indica el método (`doi` o `csl_local`), la norma, el documento y los identificadores que lo citan.
- **Número de lista:** se quita el que agregan IEEE y Vancouver («[1]», «1.»). Una referencia suelta no tiene número: la numeración es la del documento del estudiante.

**Formateador CSL local** (`app/bibliografia/csl.py`):
- **Motor:** `citeproc-py` 0.12.3 (licencia BSD), versión fija, con la configuración regional `es-ES` que trae.
- **Estilos:** los oficiales del repositorio de estilos CSL, tomados de `citeproc-py-styles` 0.2.0. Se copian al repositorio solo los tres que se usan, en `app/bibliografia/estilos/`, con su huella SHA-256 y su licencia (CC BY-SA 3.0): el paquete completo trae 10 867 estilos y pesa 60 MB.

  | Norma (D-12) | Estilo | Título del estilo |
  | --- | --- | --- |
  | `ieee` | `ieee.csl` | IEEE Reference Guide version 11.29.2023 |
  | `apa7` | `apa.csl` | APA Style 7th edition |
  | `vancouver` | `nlm-citation-sequence.csl` | NLM/Vancouver: Citing Medicine 2nd edition (citation-sequence) |

- **Normas cubiertas:** las tres de la lista cerrada de D-12. La hoja de ruta nombra solo IEEE y APA 7 porque se escribió antes de que se cerrara la lista.
- **Idioma:** el del documento se pasa al motor. Así APA no aplica la capitalización de títulos en inglés a obras en español.
- **Formato:** la salida es texto plano, como la de doi.org.

## 6. Base de desarrollo (decisión del equipo)

T18 no cambia el esquema de datos. A pedido del equipo, la base de desarrollo se migró de 0010 a 0013 tras un respaldo completo (`datos/respaldos/antes-de-0013-2026-11-23.*`), sin perder nada (ESTADO, apartado 21).

## 7. Pruebas

- **Unitarias:**
  - cada esquema con salidas válidas y defectuosas;
  - esquemas sin campos de referencia;
  - comprobación 1 con salidas fabricadas mal formadas;
  - comprobación 3 con `F9` sobre `F1` a `F8`, en campos y en texto;
  - formateador CSL en las tres normas, con artículo y con libro;
  - quitado del número de lista.
- **Integración con la base real:**
  - clase base con un agente de prueba y el modelo simulado: abstención, generación, intento 2 y sin memoria;
  - constructor de referencias con documentos con y sin DOI, en las tres normas: doi.org simulado que responde y que no responde, y aislamiento por caso.

# T20-01. Agente D4 de verificación de referencias

**Fase:** T20 (Fase 3). **Fecha:** 25 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T20. Especificación de la Fase 1:
- RF-09 y CU-08 (estado de referencias y correspondencia);
- HU-07, CP-12 y CP-13;
- RN-10 y RN-18 (no comprobable, nunca inexistente);
- D-12 (normas `ieee`, `apa7` y `vancouver`);
- 6.6: salida de la verificación; el modelo solo redacta, si se configura, una explicación de cada discrepancia.

Decisión del equipo del 25 de noviembre de 2026 ("paquete recomendado"): apartado 9.

## 1. Flujo

`POST /caso/referencias` (rol A1) toma la versión vigente más reciente del caso:
- sin versión responde 409;
- si T12 no detectó la lista de referencias responde 422, con qué hacer (RF-09, alternativo).

Si no, crea la solicitud `verificacion_referencias` con alcance `version` y responde 202. El trabajo sigue en segundo plano, como en T19. La interfaz consulta `GET /caso/referencias/{id}`, que informa el avance (referencias hechas de un total) y, al terminar, el informe.

En segundo plano (`app/agentes/referencias.py`, `AtencionReferencias`):
1. **Estructura** las entradas de la lista (las que detectó T12) con GROBID (`processCitationList`, el mismo cliente de T15). Si GROBID no trae el DOI o el año pero la entrada los tiene, se toman del texto, sin mirar el DOI para el año.
2. **Verifica** cada referencia (apartado 2).
3. **Extrae y cruza** las citas del texto según la norma del caso (apartado 3).
4. Si se configura, **explica** cada discrepancia con el modelo (apartado 4).
5. **Aplica la comprobación 1** al informe y lo guarda como resultado. El registro lleva estados y cantidades, nunca el texto de las referencias ni del borrador.

Si GROBID no responde, la solicitud queda `no_atendida` con el motivo `grobid_no_disponible`.

## 2. Estado de cada referencia (determinista)

`app/agentes/verificacion_referencias.py` (`Verificador`) usa los clientes de T14:

1. **Con DOI:** Crossref por DOI y, si no lo conoce, OpenAlex.
2. **Sin DOI, o con un DOI que nadie conoce:** búsqueda por metadatos en Crossref y luego en OpenAlex. El candidato es el de título más parecido, si llega al umbral del comparador de T14 (0,88). Así se verifican también los libros, sin servicio de ISBN.
3. **Comparación** de título, autores y año con la fuente encontrada:
   - **título:** similitud menor al umbral. Si el título de la fuente aparece tal cual en el texto de la entrada, no hay discrepancia: GROBID a veces toma la revista como título, por ejemplo cuando el título termina en un año;
   - **autores:** ningún autor coincide, o el primer autor no coincide con el primero de la fuente;
   - **año:** distinto, aunque sea en uno (apartado 9, b);
   - **dato faltante:** un dato que falta en la referencia es una discrepancia, y uno que no trae la fuente no se compara.
4. **Estado:**

   | Estado | Cuándo |
   |---|---|
   | `verificada` | La obra existe y título, autores y año coinciden |
   | `con_discrepancias` | La obra existe y algún dato difiere o falta. También un DOI que lleva a otra obra (apartado 9, a) y un DOI mal escrito de una obra que se encontró por metadatos (discrepancia `doi`) |
   | `no_localizada` | Todos los servicios respondieron y ninguno la encontró |
   | `no_comprobable` | Algún servicio no respondió y nada la encontró. Nunca queda `no_localizada` en ese caso (RN-18, CP-13) |

Cada discrepancia lleva el campo, el valor de la referencia y el de la fuente. El informe da el DOI encontrado y su enlace a doi.org.

## 3. Citas en el texto y cruce con la lista

`app/agentes/citas.py`, sin base ni red, sobre los párrafos guardados de la versión. Se excluyen los títulos y la lista.

- **IEEE:** `[1]`, `[1], [3]`, `[1]-[3]` (con guion, raya corta o raya), `[2-4]` y `[1, 3]`. Un rango de más de 50 no se expande: es un error de escritura.
- **Vancouver:** lo mismo, más `(1)`, `(2,3)` y `(1-3)`, con a lo sumo tres cifras para no confundir años. Los superíndices no se detectan, porque los párrafos guardados no conservan el formato, y el informe lo avisa (apartado 9, c).
- **APA 7:**
  - entre paréntesis: `(García, 2020)`, `(García & López, 2021)`, `(García y López, 2021)`, `(Kasneci et al., 2023)`, varias obras con `;`, varios años del mismo autor, letras (`2020a`), página y `s. f.`;
  - narrativas: `García (2020)`, `Kasneci et al. (2023)` y `García y López (2021)`, sin tomar como autor las palabras de enlace ("Según", "En", "Durante").

**Cruce:**
- **Numéricas:** por número de entrada.
- **APA:** por primer apellido y año. El apellido sale del texto de la entrada cuando tiene la forma `Apellido, I.`, porque GROBID parte los compuestos ("Alarcón Llontop" quedaba como "Llontop"). Una cita sin letra alcanza a `2020a` y `2020b`.

Se informan las **citas sin entrada** (una vez cada una) y las **entradas no citadas**.

## 4. Explicación de las discrepancias con el modelo (opcional)

El parámetro `explicar_discrepancias` de la configuración (migración de datos 0015) está apagado por defecto (apartado 9, d). Encendido:
- se hace una sola llamada con la instrucción `referencias/v1`;
- al modelo solo van las discrepancias de cada referencia `con_discrepancias` (R1 a Rn): ni el borrador ni la lista completa (RNF-10);
- la salida es `{explicaciones: [{indice, explicacion}]}`, de a lo sumo 300 caracteres. Se descarta lo que no corresponde a una referencia con discrepancias;
- el modelo no decide estados ni escribe referencias (RN-17);
- si falla, el informe sale igual, con un aviso.

## 5. Pantalla

`frontend/src/paginas/Referencias.tsx`, en `/panel/referencias` y enlazada desde el panel del caso. Muestra:
- el avance;
- los avisos: referencias no comprobables, superíndices en Vancouver y texto sin citas en la forma de la norma;
- el resumen por estado;
- cada referencia con su estado en texto (no solo color) y su explicación de una línea. También sus discrepancias ("Año: en su referencia, 2022; en la fuente, 2021"), el enlace a doi.org y si se cita en el texto;
- las citas sin entrada y las entradas no citadas.

La revisión automática de accesibilidad de Playwright no encuentra errores graves.

**Lista no detectada:** el mensaje pide poner a la lista un título con estilo y volver a cargar la versión. La ruta para marcarla a mano existe desde T12 (`/caso/versiones/{id}/referencias`), pero su pantalla no es de esta fase.

## 6. Pruebas sin red y datos de prueba

`pruebas/datos/referencias_t20.py` define 11 obras ficticias (prefijo DOI 10.5555), una por escenario:

| Escenario | Estado esperado |
|---|---|
| correcta con DOI | verificada |
| correcta sin DOI | verificada |
| año corrido en uno | con_discrepancias |
| título cambiado | con_discrepancias |
| primer autor cambiado | con_discrepancias |
| fabricada sin DOI | no_localizada |
| fabricada con el DOI de otra obra | con_discrepancias |
| fabricada con un DOI inexistente | no_localizada |
| libro sin DOI | verificada |
| servicio caído | no_comprobable |
| no citada | verificada |

Con ellas se generan los borradores `referencias_ieee.docx` y `referencias_apa7.docx` (`python -m pruebas.datos.generar_docx_muestra`), con una cita sin entrada.

- **GROBID:** sus respuestas reales a esas listas están grabadas en `pruebas/contrato/grobid/referencias_t20_<norma>.tei.xml` (`python -m pruebas.contrato.grabar_grobid_referencias`).
- **Crossref y OpenAlex:** se simulan en `pruebas/dobles_referencias.py`.

## 7. Conjunto de prueba con obras reales (actividad 8)

`evaluacion/conjuntos/referencias-t20.json` es el **borrador** del asistente (apartado 9, g), a revisar por el equipo con la hoja `evaluacion/revision/revision-referencias-t20.xlsx`. Tiene 20 referencias:
- **8 reales y correctas** (4 sin DOI en el texto);
- **6 reales con errores introducidos:** dos años, dos títulos y dos primeros autores;
- **6 fabricadas:** dos sin DOI, dos con el DOI real de otra obra y dos con un DOI inexistente.

Las obras reales son 14 del corpus provisional, con los metadatos de Crossref, consultados sin caché y sin escribir en la base. Cada referencia se escribe en IEEE y en APA 7 en `evaluacion/conjuntos/referencias-t20/borrador_<norma>.docx`, que las citan y tienen una cita sin entrada y una entrada no citada. La clave de cada borrador dice el estado esperado de cada entrada y sus citas.

**Ejecución con servicios reales:** `python -m app.agentes.evaluar_referencias evaluacion/conjuntos/referencias-t20.json`. Usa GROBID, Crossref y OpenAlex reales, sin base ni modelo. Resultado del 25 de noviembre de 2026, en `evaluacion/resultados/verificacion-referencias-t20.json`:

| Medida | IEEE | APA 7 |
|---|---|---|
| Estados iguales a la clave | 20 de 20 | 20 de 20 |
| Fabricadas que quedan verificadas | **0** | **0** |
| Cita sin entrada detectada | sí (`[21]`) | sí (`(Castañeda, 2019)`) |
| Entrada no citada detectada | sí | sí |
| Citas extraídas | 20 de 20 | 20 de 20 |

La primera ejecución mostró tres fallas, que se corrigieron:
- tres años que GROBID no devolvió en IEEE;
- un título que GROBID confundió con la revista;
- dos apellidos compuestos partidos en APA, que dieron citas sin entrada falsas.

Además, un primer autor cambiado con coautores reales pasaba como verificada, y ahora es discrepancia (apartado 2).

## 8. Rendimiento

El objetivo de 120 s para 40 referencias (RNF-12) se mide en T30, con la caché de `cache_metadatos` que usa la API. La ejecución del apartado 7 va sin caché a propósito y no se cronometró.

## 9. Decisiones del equipo (25 de noviembre de 2026)

a. Un DOI que lleva a otra obra (no coinciden título ni autores) da `con_discrepancias`, nunca `verificada`.
b. Un año que difiere, aunque sea en uno, da `con_discrepancias` con ambos años: el estudiante decide si cita la fecha en línea o la impresa.
c. En Vancouver se detectan las citas numéricas entre corchetes o paréntesis. Los superíndices no se detectan, y se avisa.
d. La explicación de cada discrepancia con el modelo se implementa, pero apagada por defecto (parámetro en la configuración).
e. Corre en segundo plano con avance, como T19.
f. Los libros se verifican por metadatos, sin servicio de ISBN, como indica la hoja de ruta.
g. El asistente arma el borrador del conjunto de referencias y de los dos borradores de prueba con su clave, y el equipo lo revisa con una hoja de Excel.

## 10. Insumos del equipo y lo que queda sin validar con datos reales

- **Revisión del conjunto:** con la hoja `revision-referencias-t20.xlsx`, una fila por referencia y otra por cita, para confirmar o corregir el tipo, el estado esperado y los campos con error, y agregar referencias propias.
- **Borradores reales con errores introducidos por el equipo:** opcional. Con los mismos campos de la hoja, ampliarían la prueba a los errores que el equipo ve en los estudiantes.

Sin validar con datos reales:
- el conjunto revisado por el equipo: el resultado del apartado 7 es sobre el borrador del asistente;
- Vancouver con servicios reales y un borrador completo (sus citas están cubiertas por las pruebas unitarias);
- la explicación de discrepancias con un modelo real, que está apagada por defecto;
- el rendimiento de RNF-12, que se mide en T30.

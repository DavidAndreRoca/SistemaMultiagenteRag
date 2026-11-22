# T15-01. Importador de referencias del artículo O1

**Fase:** T15 (Fase 3). **Fecha:** 20 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T15. Especificación de la Fase 1:
- RF-20 y CU-14;
- RN-14: las fuentes recomendadas son de acceso abierto;
- RN-18: lo que no se puede comprobar no se declara inexistente;
- RN-19: del artículo O1 solo se usan sus referencias; el artículo no se almacena ni se indexa;
- 18.9: fuente sin DOI;
- n.° 14 del plan: los PDF sin enlace directo los sube el investigador.

Decisiones del equipo del 20 de noviembre de 2026: apartados 2 y 9.

## 1. Alcance

Para la colección científica de un tema:
1. Recibe el artículo O1 o una lista de DOI y extrae sus referencias.
2. Resuelve cada referencia con los servicios de T14 y comprueba su acceso abierto.
3. Descarga el PDF cuando hay un enlace directo y lo indexa con T09 y T10.
4. Deja el resto como pendiente de PDF o excluido, con su motivo.
5. Arma el informe del tema.

El corpus provisional de T10 ya está ingerido y respaldado: el importador no lo toca.

## 2. Formatos del artículo O1 (ampliación de RF-20)

RF-20 nombra el .docx o una lista de DOI y la extracción "con GROBID". GROBID solo lee PDF, y los artículos base del equipo son PDF. Por eso el equipo decidió aceptar tres formatos:

| Entrada | Validación | Extracción de referencias |
| --- | --- | --- |
| PDF | La de T09 (tipo real, tamaño, cifrado y páginas) | GROBID `processReferences`, sin consolidar (no consulta servicios externos) |
| .docx | La de T11 (macros, cifrado, contenido anómalo…) | La lista de referencias se detecta con T12 (título de la sección o, si no lo hay, la forma de las entradas). Después, GROBID `processCitationList` analiza cada entrada |
| Lista de DOI | Cada línea se normaliza; las que no tienen forma de DOI se excluyen (`doi_invalido`) | Sin GROBID |

## 3. RN-19: el artículo O1 no queda

- **Archivo:** el subido se guarda en `DIRECTORIO_ARCHIVOS/importacion/<id>/`, una carpeta privada que nunca se sirve. Se borra en cuanto se extraen las referencias, antes de resolver ninguna, y también si la extracción falla.
- **Petición:** Starlette guarda el cuerpo de una subida grande en un archivo temporal anónimo, que se borra al cerrar la petición.
- **Al arrancar:** la API borra lo que haya quedado en esa carpeta (por ejemplo, tras una caída). Una importación que figura en curso pero que el proceso actual no atiende se marca `interrumpida` en la siguiente consulta o importación. Se hace así porque, al arrancar, la base puede no estar disponible todavía.
- **Base:** solo se guardan las referencias: el texto de cada entrada, que es un dato bibliográfico público, y sus metadatos. No se guarda el nombre del archivo ni su huella.
- **Corpus:** el artículo nunca pasa por el indexador.
- **Registro público del artículo en la caché bibliográfica:** las búsquedas de OpenAlex para otras referencias pueden devolver, entre sus candidatos, el registro bibliográfico del propio artículo O1 (título, autores, año y DOI). Esas respuestas quedan en `cache_metadatos` (T14), como cualquier otra. Ocurrió en la prueba real (ESTADO, apartado 18.3). El equipo decidió el 22 de noviembre de 2026 que esto no infringe RN-19: es un metadato público de un servicio externo, no el artículo ni su texto. Por eso se deja así.
- **Comprobación:** las pruebas revisan, después de importar, que no quede ningún archivo en la carpeta, que ninguna tabla contenga una frase del cuerpo del artículo y que el artículo no esté entre los documentos. Se hace con archivos ficticios y con un artículo base real, en un proyecto aislado.

## 4. Modelo de datos (migración 0011)

| Tabla o cambio | Contenido |
| --- | --- |
| `importacion_referencias` | Una por importación: colección, origen (`pdf`, `docx` o `doi`), estado (`en_cola`, `en_proceso`, `terminada`, `interrumpida` o `fallida`), totales y avance, quién la pidió, fechas y código de error |
| `referencia_importada` | Una por referencia y colección (única por `clave`: el DOI normalizado o la huella del texto normalizado). Guarda el texto de la entrada, los metadatos, el estado (`incluida`, `pendiente_pdf`, `excluida` o `no_comprobable`), el motivo, la ubicación y la licencia de acceso abierto, el documento indexado y la última importación que la trató |
| `motivo_exclusion_corpus` | Tres valores nuevos para las referencias: `no_localizada` (los servicios respondieron y no hay coincidencia), `sin_doi` (localizada, pero sin DOI no se puede comprobar el acceso abierto) y `doi_invalido` (una línea de la lista de DOI sin forma de DOI) |

El contador `n_pendientes` de la colección cuenta ahora las referencias pendientes de PDF.

## 5. Resolución de cada referencia

1. **Con DOI:** Crossref por DOI y, si Crossref no lo conoce, OpenAlex por DOI. Los DOI de DataCite (arXiv, Zenodo) no están en Crossref; se agregó tras la prueba real (ESTADO, apartado 18.4). Si nadie lo encuentra (puede ser un DOI mal escrito), se busca por metadatos.
2. **Sin DOI, o con un DOI que no se encontró:**
   - búsqueda en Crossref y luego en OpenAlex;
   - el comparador de T14 confirma un candidato solo si coinciden título, autor y año;
   - sin confirmación, la referencia queda `no_localizada` (excluida). Si algún servicio no respondió, queda `no_comprobable` (RN-18): no se excluye y se reintenta en la próxima importación.
3. **Localizada sin DOI** (libros, informes): excluida con `sin_doi`.
4. **Acceso abierto:** se consulta Unpaywall.
   - Unpaywall solo cubre DOI de Crossref. Si no tiene el registro y OpenAlex localizó la obra por su DOI, vale el acceso abierto que informa OpenAlex.
   - Sin ninguno de los dos registros, o con `is_oa = false`, la referencia se excluye con `sin_acceso_abierto`, porque RN-14 exige acceso abierto comprobado.
   - Si Unpaywall no responde, queda `no_comprobable`.
5. **Con un enlace directo al PDF:** se descarga (hasta el tamaño máximo de PDF, con la firma `%PDF-` comprobada) y se indexa con el indexador de T10. El documento recibe los metadatos de Crossref (DOI, título, autores, año, revista) y los de acceso abierto (estado, licencia, URL).
   - Si la descarga falla (403, no es un PDF, tiempo agotado), queda `pendiente_pdf` con el motivo `descarga_fallida`.
   - Si T10 lo excluye (escaneado, cifrado…), la referencia queda excluida con ese motivo.
6. **Abierta, sin enlace directo:** `pendiente_pdf` (`sin_enlace_directo`), con la URL de la página de acceso abierto para que el investigador baje el PDF y lo suba.

**Idempotencia:** reimportar el mismo artículo no duplica nada.
- Las referencias ya `incluida` o `excluida` se cuentan, pero no se vuelven a procesar.
- Las `no_comprobable` se reintentan.
- Las `pendiente_pdf` se reintentan solo si ahora hay un enlace directo.
- Un DOI que ya tiene documento en la colección no se descarga otra vez.

## 6. Proceso en segundo plano

- La ruta de importación responde 202 en cuanto guarda el archivo y crea la importación. El trabajo sigue en una tarea `asyncio` de la API, una importación a la vez por proceso: Docling ocupa más de 1 GB.
- El estado se consulta en `GET /investigador/importaciones/{id}`, que muestra el avance.
- La cola persistente y el proceso trabajador son de T28. Hasta entonces, una importación cortada por un reinicio queda `interrumpida` (apartado 3), y basta con importar de nuevo (idempotencia).

## 7. Rutas del investigador (A2)

| Ruta | Qué hace |
| --- | --- |
| `POST /investigador/colecciones/{id}/importaciones` | Formulario con `archivo` (PDF o .docx) o con `dois` (uno por línea). Responde 202 con la importación |
| `GET /investigador/importaciones/{id}` | Estado, avance y contadores |
| `GET /investigador/colecciones/{id}/informe` | Informe del tema: referencias totales, de acceso abierto, incluidas, excluidas (por motivo), pendientes de PDF y no comprobables |
| `GET /investigador/colecciones/{id}/referencias?estado=` | Las referencias con su estado y motivo. Con `estado=pendiente_pdf`, la vista de pendientes |
| `POST /investigador/referencias/{id}/pdf` | Sube el PDF de una referencia pendiente. Se indexa con T10 y la referencia queda incluida, o excluida con el motivo de T10 |

## 8. Pantallas

En `/investigador/importacion`:
- elegir el tema y subir el artículo O1 o pegar los DOI, con el avance de la importación;
- el informe del tema;
- la lista de pendientes con un enlace a su página de acceso abierto y un botón para subir el PDF.

## 9. Pruebas

- **Integración**, con servicios simulados (GROBID, los cuatro servicios bibliográficos, la descarga y el canal de T09 y T10 con sus dobles):
  - un .docx ficticio con 24 referencias, con todos los resultados posibles;
  - la lista de DOI;
  - la idempotencia;
  - RN-19;
  - la subida desde pendientes.
- **Prueba real, decidida por el equipo:** un artículo base de `datos/articulos-base/` se importa de punta a punta (GROBID, Crossref, Unpaywall, descarga, Docling y embeddings reales) en un proyecto de Compose aislado, con RN-19 comprobado al final en disco y en la base.
- **Extremo a extremo de la pantalla:** Playwright, en la CI y con `scripts/e2e.ps1`, abre la importación de un tema, comprueba el informe y los pendientes vacíos y revisa la accesibilidad. Subir un PDF requiere el canal completo (GROBID, Docling y el servicio de modelos), que la CI no tiene. Por eso la subida desde pendientes se prueba así:
  - en la interfaz, con pruebas unitarias;
  - en la API, con pruebas de integración;
  - con el canal real, en la prueba con un artículo base.

  Así se reemplaza la variante `-Completo` de `scripts/e2e.ps1` prevista al inicio: no se pudo armar con datos estables, porque las referencias pendientes de un artículo real dependen de servicios externos.

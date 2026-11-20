# T14-01. Clientes bibliográficos con limitador y caché

**Fase:** T14 (Fase 3). **Fecha:** 20 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T14. Especificación de la Fase 1: RN-18 ("si un servicio bibliográfico no responde, la fuente queda no comprobable y nunca inexistente"), RNF-20 (servicios detrás de interfaces), 14.1 (clientes asíncronos con limitador, reintento exponencial, tiempo máximo y caché por DOI), 18.9 (fuente sin DOI) y 05_tecnologias (límites de cada servicio). Base de RF-09, RF-13, RF-20 y CP-13.

## 1. Alcance

T14 entrega el módulo `app/bibliografia/` con los cuatro clientes, el limitador, la caché y el comparador. No decide qué servicio consultar para cada referencia ni importa referencias: eso es T15 (importador) y T20 (D4).

## 2. Resultado común (`modelos.py`)

Toda consulta devuelve un `ResultadoBibliografico` con:
- `servicio`;
- `estado`: `encontrado`, `no_encontrado` o `no_comprobable`;
- metadatos normalizados (`MetadatosBibliograficos`: DOI, título, autores con apellidos y nombres, año, revista, volumen, número, páginas, editorial y tipo);
- según el servicio, el acceso abierto (`AccesoAbierto`) o la cita formateada;
- `motivo` cuando no es `encontrado`;
- `desde_cache`.

**RN-18 en el código:**
- `no_encontrado` solo sale de una respuesta válida del servicio que dice que no existe (404 por DOI, o una búsqueda que responde sin coincidencias).
- Cualquier otra cosa da `no_comprobable` con su motivo: error de red, tiempo agotado, 429 o 5xx tras los reintentos, respuesta ilegible, otro estado HTTP o servicio sin configurar.

La interfaz `ServicioBibliografico` (`interfaces.py`) tiene `por_doi`. Crossref y OpenAlex agregan `buscar` (búsqueda por metadatos), doi.org agrega `cita` y Unpaywall da el acceso abierto en `por_doi`. Cambiar de servicio no toca a quien los usa (RNF-20).

## 3. Cliente HTTP (`http.py`)

- **Tiempos:** 5 s de conexión y un máximo por consulta (`TIEMPO_MAXIMO_BIBLIOGRAFIA_S`, 15 s).
- **Reintentos** (`REINTENTOS_BIBLIOGRAFIA`, 3 intentos en total) ante errores transitorios (red, tiempo agotado, 429, 500, 502, 503 y 504). La espera es exponencial, de 0,5 s, 1 s, 2 s…, con un componente aleatorio. Se respeta `Retry-After` hasta 10 s.
- **Sin reintento** ante un 404 u otro 4xx: son respuestas definitivas.
- **Antes de cada intento** se pide una ficha al limitador del servicio.
- **Datos enviados:** a los servicios solo van DOI, títulos, autores y años, nunca texto del borrador (06_rag_seguridad). El correo del proyecto va en `mailto` (Crossref y OpenAlex), en `email` (Unpaywall, obligatorio) y en el `User-Agent`. La clave de OpenAlex va en `api_key`. Ninguno de los dos se registra: el registro solo lleva el servicio, el estado HTTP, el número de intentos y el motivo.

## 4. Limitador (`limitador.py`)

Una cubeta de fichas por servicio (`asyncio`, con reloj y espera inyectables para las pruebas). Valores iniciales, tomados de la documentación de cada servicio (05_tecnologias):

| Servicio | Tasa (consultas por segundo) | Ráfaga | Fuente |
| --- | --- | --- | --- |
| Crossref, registro por DOI | 10 | 10 | Pool cortés: 10 por segundo de registro individual |
| Crossref, búsqueda | 3 | 3 | Pool cortés: 3 por segundo de listas o búsquedas |
| doi.org | 5 | 5 | Sin límite publicado: valor prudente |
| Unpaywall | 1,15 | 10 | 100 000 consultas por día (1,16 por segundo de media) |
| OpenAlex | 10 | 10 | 10 por segundo; la búsqueda tiene costo, la consulta por DOI no |

Se configuran con `TASA_CROSSREF`, `TASA_CROSSREF_BUSQUEDA`, `TASA_DOI`, `TASA_UNPAYWALL` y `TASA_OPENALEX`. **Son ajustes de operación, no parámetros funcionales:** no cambian qué se verifica ni cómo, sino cuántas consultas por segundo se hacen. Por eso van en las variables de entorno y no en la configuración versionada. Lo mismo vale para los tiempos, los reintentos y la vigencia de la caché.

## 5. Caché (`cache.py`, tabla `cache_metadatos` de T04)

- **Clave:** `(servicio, clave)`. La clave es el DOI normalizado, `doi|estilo|idioma` para una cita o `busqueda|<consulta normalizada>` para una búsqueda.
- **Qué se guarda:** solo resultados `encontrado` y `no_encontrado`. Un `no_comprobable` nunca se guarda, para que una caída no se recuerde como un resultado.
- **Vigencia:**
  - 30 días para lo encontrado (`VIGENCIA_CACHE_BIBLIOGRAFIA_DIAS`);
  - 24 horas para lo no encontrado (`VIGENCIA_NO_ENCONTRADO_HORAS`), porque un DOI recién registrado puede aparecer al día siguiente.
- **Lo que se guarda es el resultado normalizado**, no la respuesta cruda.
- **Repositorio:** `RepositorioCacheMetadatos`, en `repositorios/sistema.py`. No lleva contexto de caso porque son metadatos públicos de publicaciones, compartidos por todo el sistema, igual que la configuración.

## 6. Clientes

| Cliente | Consulta | Notas |
| --- | --- | --- |
| Crossref (`crossref.py`) | `GET /works/{doi}`; búsqueda `GET /works?query.bibliographic=...&rows=5` | Fuente principal (decisión de la especificación). Autores con apellidos y nombres por separado |
| doi.org (`doi.py`) | Negociación de contenido: `application/vnd.citationstyles.csl+json` (metadatos) y `text/x-bibliography; style=...; locale=...` (cita) | Cita determinista, sin modelo de lenguaje (RN-17). Estilos de las normas de la configuración: `apa` (apa7), `ieee` y `vancouver` |
| Unpaywall (`unpaywall.py`) | `GET /v2/{doi}?email=...` | Estado OA, si es abierto, y la mejor ubicación: URL, PDF, licencia y versión |
| OpenAlex (`openalex.py`) | `GET /works/doi:{doi}`; búsqueda `GET /works?search=...` | Respaldo de metadatos y de estado OA. Sin `CLAVE_OPENALEX` da `no_comprobable` (`no_configurado`). Da el nombre completo de cada autor; el apellido se toma como la última palabra |

## 7. Comparador (`comparador.py`)

Confirma que un candidato de una búsqueda corresponde a la referencia (18.9; CP-15). Exige las tres condiciones:

| Condición | Tolerancia |
| --- | --- |
| Título | Similitud de 0,88 o más (`difflib`), sobre el título normalizado: minúsculas, sin tildes ni puntuación, espacios simples. También se compara sin el subtítulo (lo que sigue a ":") y vale la mayor |
| Autor | Al menos un apellido en común, normalizado igual que el título. Con apellidos compuestos, basta que coincida una palabra de 3 letras o más |
| Año | Igual, o con un año de diferencia: la versión en línea y la impresa suelen diferir |

Si a la referencia le falta el título, los autores o el año, no se confirma (`datos_insuficientes`): sin los tres datos no hay coincidencia comprobable. El umbral de 0,88 es el que se calibró con el corpus provisional (`scripts/armar_corpus_provisional.py`).

## 8. Pruebas

- **Contrato:** `pruebas/contrato/` guarda respuestas reales de los cuatro servicios (un artículo existente y un DOI inexistente), grabadas con `python -m pruebas.contrato.grabar`. Antes de guardarlas se quitan el correo, la clave y la lista de referencias del artículo, que es larga y no se usa.
- **Simulación:** caídas (error de conexión), tiempo agotado, 429 con `Retry-After`, 500 y respuestas lentas, con `httpx.MockTransport` y esperas simuladas.
- **Unitarias:** limitador con reloj simulado y comparador.
- **Integración:** caché con la base real.
- **Sin red en la CI:** ninguna prueba llama a los servicios reales.

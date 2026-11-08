# T08-01. Servicios compartidos: inferencia, revisiones, determinismo y despliegue

**Estado:** Vigente (decisión técnica nueva, fase T08, 6 de noviembre de 2026).

## 1. Biblioteca de inferencia (actividad 3)

**Decisión:** transformers 5.20.2 con PyTorch 2.14.1 para CPU, sin sentence-transformers ni FlagEmbedding. Las versiones de todo el árbol están fijadas en `servicio_modelos/restricciones.txt`.

| Opción | Motivo |
| --- | --- |
| **transformers + PyTorch CPU (elegida)** | Reproduce la salida densa de bge-m3 (vector [CLS] normalizado, como indica `1_Pooling/config.json` del modelo) y el logit de bge-reranker-v2-m3 con pocas líneas propias. Da control sobre el armado de los lotes, que hace falta para el determinismo (apartado 3). Hay ruedas oficiales para `linux/arm64` y `linux/amd64` |
| sentence-transformers | Envuelve lo mismo, pero arma los lotes con relleno por dentro y cambia de interfaz entre versiones mayores |
| FlagEmbedding | Biblioteca oficial de BAAI, con más dependencias y el mismo problema de relleno |
| ONNX Runtime | Menos memoria posible, pero los pesos oficiales de bge-reranker-v2-m3 no traen ONNX, y convertirlos sería un artefacto no verificable frente a la revisión fijada |

PyTorch sale del índice de CPU de PyTorch: la rueda de PyPI para amd64 trae CUDA, que pesa varios GB. Al auditar, `restricciones.txt` se revisa sin la etiqueta local `+cpu`, porque PyPI no la conoce (paso de la integración continua).

## 2. Revisiones exactas y descarga (actividad 4)

| Modelo | Revisión (commit) | Licencia | Pesos |
| --- | --- | --- | --- |
| `BAAI/bge-m3` | `5617a9f61b028005a4858fdac845db406aefb181` | MIT | `pytorch_model.bin`, 2 271 145 830 bytes |
| `BAAI/bge-reranker-v2-m3` | `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` | Apache-2.0 | `model.safetensors`, 2 271 071 852 bytes |

- `servicio_modelos/servicio/catalogo.py` guarda el tamaño de cada archivo y el SHA-256 de los archivos LFS, según la API de Hugging Face consultada el 6 de noviembre de 2026.
- `python -m servicio.descargar` baja solo los archivos de la salida densa al volumen `sma_modelos` y verifica tamaño y huella.
- El servicio arranca sin red (`HF_HUB_OFFLINE=1`) y se niega a arrancar si falta un archivo.
- Cada respuesta incluye el modelo y la revisión (RNF-21). Cambiar una revisión obliga a reindexar (Fase 1, 18.5).

## 3. Determinismo: lotes sin relleno

**Medición** (contenedor amd64, 8 hilos, bge-m3, un párrafo de unos 350 tokens):

| Forma del lote | ¿Igual al vector del texto solo? |
| --- | --- |
| El mismo texto, otra solicitud | Sí, bit a bit |
| Lote de 2, 4 o 16 textos con la misma cantidad de tokens (sin relleno) | Sí, bit a bit |
| Lote con textos de otras longitudes (con relleno) | No: diferencia máxima de 1,2e-7 (coseno 1,0000000000) |

**Decisión:** cada lote agrupa solo textos con la misma cantidad de tokens (`servicio/lotes.py`), en grupos de hasta `TAMANO_LOTE`. Así el mismo texto produce siempre el mismo vector, llegue solo o acompañado, que es el criterio de T08. El reordenador sigue la misma regla.

**Costo:** ninguno apreciable. En CPU, agrupar casi no acelera (64 párrafos):

| Lote | Textos por segundo |
| --- | --- |
| 1 | 1,49 |
| 4 | 1,60 |
| 16 | 1,41 |

Además, `torch.use_deterministic_algorithms(True)`.

## 4. Límites y concurrencia

- `MAX_CONCURRENCIA` (1 por defecto): inferencias simultáneas. Las demás esperan hasta `ESPERA_MAXIMA_S` (120 s) y luego reciben 503 `servicio_ocupado`. Así dos integrantes no saturan la instancia.
- `MAX_TEXTOS` (128) por solicitud y `MAX_TOKENS` (1 024) por texto o par. Un texto más largo se rechaza con 422 `texto_demasiado_largo`: **nunca se trunca en silencio**. Los fragmentos son de 300 a 450 tokens (18.4).
- El cliente de la API (`app/inferencia/servicio_modelos.py`) divide en partes de 64 textos. Comprueba la dimensión, la cantidad y que todas las partes vengan de la misma revisión.
- El registro solo guarda cantidades y duraciones, nunca textos (4.6).

## 5. Despliegue: proyecto `compartido`

- `compartido/docker-compose.yml` (nombre `sma_compartido`) contiene GROBID 0.9.1-crf (decisión T01-01), el servicio de modelos, la descarga y las pruebas con pesos reales.
- Vive en su propia carpeta porque el `COMPOSE_PROJECT_NAME` del `.env` de la raíz tiene prioridad sobre `name:` y le cambiaba el nombre al proyecto (comprobado: quedaba como `sma_rag`).
- Puertos solo en `127.0.0.1`: modelos en 8001 y GROBID en 8070.
- La red `sma_compartido` tiene nombre fijo. T10 une la API a ella con `URL_SERVICIO_MODELOS=http://servicio_modelos:8000`. En T08 la API no se conecta todavía, porque nada la usa hasta la indexación.

## 6. Interfaces en `app/` (actividad 5, RNF-20)

- `app/inferencia/interfaces.py`: `ProveedorEmbeddings.embeber(textos)` y `Reordenador.reordenar(consulta, textos)`. Devuelven los vectores o los puntajes con la identidad del modelo.
- `ClienteServicioModelos` implementa ambas interfaces.
- Los errores del servicio se convierten en `servicio_modelos_no_disponible`: 503 si el servicio cayó, o 422 si rechazó la entrada.

## 7. Memoria y tiempo medidos

Equipo de desarrollo amd64, Docker Desktop con 8 GB y 16 CPU (8 hilos de PyTorch).

| Componente | Memoria |
| --- | --- |
| Servicio de modelos: proceso tras un lote de 64 párrafos y un reranking de 30 | 3,5 GB residente, pico de 3,6 GB (`VmHWM`) |
| GROBID 0.9.1-crf tras procesar PDF | 2,2 a 2,5 GB |
| Base de desarrollo (cada una, vacía) | 40 a 55 MB |
| API (cada una) | 50 MB |

| Operación | Tiempo |
| --- | --- |
| Embeber 64 párrafos de unos 350 tokens | 38 s (1,7 por segundo) |
| Reordenar 30 candidatos (k = 30) | 19 s |
| Cargar los dos modelos | 9 a 13 s |

**Estimación para la instancia** (2 OCPU y 12 GB de Always Free, según la Fase 1, 13.3):

| Componente | GB |
| --- | --- |
| Servicio de modelos | 3,6 |
| GROBID | 2,5 |
| Dos bases con corpus (estimado) | 1,0 |
| Dos API | 0,4 |
| Sistema, Docker y dos sesiones de Claude Code (estimado) | 2,0 |
| **Total** | **unos 9,5** |

Cabe sin intercambio, con unos 2,5 GB de margen. **Debe medirse en la instancia real** (T01, pendiente) con `docker stats` y `free -m`.

## 8. Riesgos detectados (para T10, T16 y T34)

- **Latencia del reranking (riesgo para T16).** Reordenar 30 candidatos tardó 18,6 s en la prueba con pesos reales y 19 s contra el servicio en marcha, con 8 hilos x86. Con 2 OCPU ARM puede ser varias veces más lento, lo que pesa en la latencia por solicitud (RNF-12). Opciones a evaluar en T16 y T34, sin adelantarlas:
  - Reordenar menos candidatos.
  - Bajar `MAX_TOKENS` del par.
  - Cuantizar a int8.
  - Usar un servidor de pago (contingencia de R-02).
- **Tiempo de indexación.** A 1,7 fragmentos por segundo en este equipo, unos 50 000 fragmentos tardan unas 8 h; en la instancia, previsiblemente más. Encaja con la indexación fuera de línea en lote (18.5), pero conviene medirlo en T10.
- **GROBID bajo emulación:** la primera solicitud tardó más de 2 minutos en cargar sus modelos, y las siguientes tardaron 3 s. La prueba de integración da 600 s a la primera solicitud.

## 9. Verificación en ARM

Con emulación `linux/arm64` (QEMU de Docker Desktop):
- GROBID 0.9.1-crf respondió y extrajo título y autores.
- La imagen del servicio de modelos se construye para arm64, pero en emulación no arranca: oneDNN, dentro de PyTorch, falla al leer `MIDR_EL1`, que QEMU no expone.

Es una limitación del emulador y no bloquea T08 (`T08-emulacion-arm64.md`). La respuesta, el rendimiento y la memoria reales se verifican en la instancia ARM de T01, en trámite con Oracle (incidente 261107-001540).

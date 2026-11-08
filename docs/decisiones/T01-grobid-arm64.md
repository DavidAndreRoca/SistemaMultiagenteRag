# T01-01. GROBID en ARM: variante CRF

**Estado:** Vigente. Confirmada por los autores el 6 de noviembre de 2026 (decisión técnica nueva, fase T01; riesgo R-03).

## Hallazgo

Consulta del 6 de noviembre de 2026 a los manifiestos de Docker Hub (script `scripts/verificar-imagenes-arm.sh`):

* `pgvector/pgvector:pg16`, `python:3.12-slim` y `node:22-slim` publican `linux/arm64`.
* Las etiquetas de GROBID de la serie 0.8.x (`grobid/grobid:0.8.1`, `0.8.2`, `0.8.2.1`, incluidas las `-full` y `-crf`) y las etiquetas `0.9.0` y `0.9.1-full` son **solo amd64**.
* `grobid/grobid:0.9.1-crf` (y `0.9.0-crf`) publican **amd64 y arm64**.

## Decisión

Usar `grobid/grobid:0.9.1-crf` en la instancia ARM de desarrollo y de producción (T08). La variante CRF no incluye los modelos de aprendizaje profundo de la variante `full`, por lo que la calidad de extracción de metadatos y referencias debe medirse en T09 con los PDF de muestra; GROBID se usa solo para metadatos de cabecera y referencias (D-01), no para el texto de los fragmentos (Docling).

## Alternativas

* Emular amd64 en la instancia ARM: descartada por rendimiento y memoria (R-02).
* Servidor de pago amd64 solo para GROBID: queda como contingencia si la calidad CRF no basta en T09.

## Pendiente

Verificar en la instancia ARM real (T01, aún no disponible) que el contenedor arranca, y medir en T09 la calidad de la variante CRF con los PDF de muestra. En T08, GROBID se comprobó con emulación arm64 en local: responde y extrae la cabecera (`T08-emulacion-arm64.md`).

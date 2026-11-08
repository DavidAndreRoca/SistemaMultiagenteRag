# T08-02. Prueba en arm64 emulado: limitación del emulador, no bloquea T08

**Estado:** Vigente. Decidida por los autores el 8 de noviembre de 2026.

## Hallazgo

En el equipo de desarrollo (Windows, Docker Desktop amd64) se probaron las imágenes con emulación `linux/arm64` (QEMU):

| Imagen | Resultado |
| --- | --- |
| `grobid/grobid:0.9.1-crf` | Arranca (`uname -m`: `aarch64`), responde `isalive` y extrae título y autores del PDF ficticio. La primera solicitud tardó más de 2 minutos en cargar sus modelos; las siguientes, unos 3 s |
| Servicio de modelos (`servicio_modelos`, construido para arm64 con las ruedas oficiales de PyTorch 2.14.1+cpu para aarch64) | La imagen se construye (48 minutos bajo emulación), pero el proceso no llega a responder `/salud`. El registro muestra un error de oneDNN, dentro de PyTorch, al leer el registro `MIDR_EL1` de la CPU, seguido de `qemu: uncaught target signal 11 (Segmentation fault)` |

oneDNN (con `xbyak_aarch64`) detecta las capacidades de la CPU leyendo `MIDR_EL1` desde sysfs. QEMU en modo usuario no expone ese registro, así que la detección falla dentro del emulador. Una CPU ARM real, como la Ampere A1 de Oracle, sí lo expone.

## Decisión

- **Es una limitación del emulador (oneDNN con QEMU), no un defecto de la imagen.** No bloquea T08 y no se sigue diagnosticando en emulación.
- **Queda pendiente confirmarlo en la instancia ARM real**, que está en trámite con Oracle (incidente 261107-001540). Se añadió como pendiente a T01 en `docs/ESTADO_DESARROLLO.md`.

## Qué se comprueba en la instancia real

1. `docker compose -f compartido/docker-compose.yml --profile descarga run --rm --build descargar_modelos` y `up -d --wait`: los dos servicios quedan sanos.
2. `docker compose -f compartido/docker-compose.yml --profile pruebas run --rm --build pruebas_modelos`: contrato, determinismo, memoria y tiempo con los pesos reales.
3. `docker stats --no-stream` y `free -m` con los servicios compartidos y dos bases de desarrollo: sin intercambio a disco (criterio de T08).

Si en la instancia real apareciera el mismo error, la alternativa es desactivar oneDNN (`torch.backends.mkldnn.enabled = False`) y medir el costo en tiempo, o recurrir a la contingencia de R-02.

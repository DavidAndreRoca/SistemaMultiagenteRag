# T02-01. Escaneo de secretos con la imagen oficial de gitleaks

**Estado:** Vigente (decisión técnica nueva, fase T02)

## Decisión

La integración continua ejecuta `ghcr.io/gitleaks/gitleaks` (versión fijada) con `docker run`, y no la acción `gitleaks/gitleaks-action`, porque esta exige licencia en repositorios de organizaciones (D-02 prevé una organización).

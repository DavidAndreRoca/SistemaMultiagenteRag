# Imagen de la API. Python 3.12 (D-01); la imagen base es multiarquitectura (amd64 y arm64).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    DOCLING_SECURITY_REFUSE_UNPINNED_REMOTE_CODE=1
WORKDIR /app
RUN python -m pip install --upgrade "pip>=26.2"
# Árbol completo con versiones exactas, incluido el extra corpus (T09: Docling y PyTorch en
# CPU desde el índice de PyTorch). Va antes que el código para aprovechar la caché.
COPY restricciones-corpus.txt ./
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r restricciones-corpus.txt
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY migraciones ./migraciones
# Instrucciones versionadas de los agentes (T17): /app/instrucciones/<agente>/<version>.md
COPY instrucciones ./instrucciones

# --- Ejecución (desarrollo y producción) ---
FROM base AS ejecucion
# /archivos: PDF del corpus (T10); un volumen nuevo hereda este dueño. El usuario no tiene
# carpeta personal: las cachés de PyTorch y Docling van a /tmp.
RUN pip install --no-deps . && useradd --system --no-create-home --uid 10001 sma \
    && mkdir -p /archivos /recursos && chown sma:sma /archivos
ENV HOME=/tmp
USER sma
EXPOSE 8000
CMD ["python", "-m", "app"]

# --- Pruebas y análisis (nunca se despliega) ---
FROM base AS pruebas
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    -c restricciones-corpus.txt -e ".[dev,corpus]"
COPY pruebas ./pruebas
CMD ["pytest", "--cov", "--cov-report=term-missing"]

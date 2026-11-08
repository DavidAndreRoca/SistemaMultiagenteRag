# Servicio de modelos (T08). Python 3.12 (D-01); imagen base y ruedas para amd64 y arm64.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
RUN python -m pip install --upgrade "pip>=26.2"
# Árbol completo con versiones exactas; torch para CPU desde el índice de PyTorch.
COPY restricciones.txt ./
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r restricciones.txt
COPY pyproject.toml ./
COPY servicio ./servicio
RUN pip install --no-deps . \
    && useradd --system --no-create-home --uid 10002 sma \
    && mkdir /modelos && chown sma:sma /modelos
# Un volumen nuevo hereda el dueño de /modelos: la descarga corre sin ser root.
# El usuario no tiene carpeta personal: la caché de descarga va dentro del volumen.
ENV DIRECTORIO_MODELOS=/modelos \
    HF_HOME=/modelos/.cache-hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# --- Ejecución ---
FROM base AS ejecucion
USER sma
EXPOSE 8000
CMD ["python", "-m", "servicio"]

# --- Pruebas y análisis (nunca se despliega) ---
FROM base AS pruebas
RUN pip install "pytest>=9.0.3,<10" "pytest-asyncio>=0.24,<2" "pytest-cov>=5,<8" "httpx>=0.27,<1"
COPY pruebas ./pruebas
USER sma
CMD ["pytest"]

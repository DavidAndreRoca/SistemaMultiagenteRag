# Imagen de la API. Python 3.12 (D-01); la imagen base es multiarquitectura (amd64 y arm64).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN python -m pip install --upgrade "pip>=26.2"
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY migraciones ./migraciones

# --- Ejecución (desarrollo y producción) ---
FROM base AS ejecucion
RUN pip install . && useradd --system --no-create-home --uid 10001 sma
USER sma
EXPOSE 8000
CMD ["python", "-m", "app"]

# --- Pruebas y análisis (nunca se despliega) ---
FROM base AS pruebas
RUN pip install -e ".[dev]"
COPY pruebas ./pruebas
CMD ["pytest", "--cov", "--cov-report=term-missing"]

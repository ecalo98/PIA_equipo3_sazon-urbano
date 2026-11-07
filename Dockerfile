# syntax=docker/dockerfile:1
# Imagen única con dos destinos: "app" (producción) y "tests" (pruebas + cobertura).

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# ---------- Pruebas ----------
FROM base AS tests
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["pytest", "--cov", "--cov-report=term-missing", "-ra"]

# ---------- Aplicación (destino por defecto) ----------
FROM base AS app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY src ./src
COPY data ./data
COPY fixtures ./fixtures
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
# Railway/Render/Fly.io inyectan PORT; en local se usa APP_PORT o 8000.
CMD ["sh", "-c", "uvicorn --factory sazon_urbano.api.main:crear_app --host 0.0.0.0 --port ${PORT:-${APP_PORT:-8000}}"]

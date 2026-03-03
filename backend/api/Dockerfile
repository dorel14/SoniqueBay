# Étape d'extraction de version
FROM python:3.11-slim AS version_extractor
COPY _version_.py /_version_.py
RUN python -c "from _version_ import __version__; print(__version__)" > /version.txt

# Dockerfile pour le service API FastAPI
FROM python:3.11-slim

# Labels pour la traçabilité
ARG BUILD_DATE

LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="$(cat /version.txt)" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay API" \
      org.opencontainers.image.description="Service API FastAPI pour SoniqueBay"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv et vérification
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv --version

# Création du répertoire de travail
WORKDIR /app

# Copie et installation des dépendances
COPY requirements.txt .

RUN /root/.local/bin/uv pip install --system -r requirements.txt

# Vérification et installation forcée d'uvicorn si nécessaire
RUN /root/.local/bin/uv pip install --system uvicorn || true

# Copie du code de l'application
COPY backend/ ./backend/
COPY scripts/ ./scripts/
# Note: Les migrations alembic sont gérées par le worker ou Supabase
# COPY alembic/ ./alembic/
# COPY alembic.ini .

# Copie du script de healthcheck
COPY scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Création des répertoires nécessaires pour les données persistantes (img, static, api_data)
RUN mkdir -p /app/backend/data/img /app/backend/data/static /app/backend/data/api_data /app/logs

# Exposition du port
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Commande de démarrage
CMD ["python3", "-m", "uvicorn", "backend.api.api_app:create_api", "--host", "0.0.0.0", "--port", "8001"]



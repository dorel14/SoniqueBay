# Dockerfile pour le service API FastAPI
FROM python:3.11-slim

# Labels pour la traçabilité
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app"
LABEL org.opencontainers.image.description="Service API FastAPI pour SoniqueBay"
LABEL org.opencontainers.image.version="1.0"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Création du répertoire de travail
WORKDIR /app

# Copie et installation des dépendances
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Vérification et installation forcée d'uvicorn si nécessaire
RUN python3 -c "import uvicorn; print('uvicorn OK')" || uv pip install --system uvicorn

# Copie du code de l'application
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Création des répertoires nécessaires
RUN mkdir -p /app/backend/api/data /app/logs

# Exposition du port
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Commande de démarrage
CMD ["python3", "-m", "uvicorn", "backend.api.api_app:create_api", "--host", "0.0.0.0", "--port", "8001"]
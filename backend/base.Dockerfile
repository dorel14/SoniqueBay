# Image de base avec uv préinstallé
FROM python:3.13-slim AS base

# Labels pour le cache et la traçabilité
LABEL org.opencontainers.image.source="https://github.com/your-repo/SoniqueBay-app"
LABEL org.opencontainers.image.description="Image de base Python avec uv"
LABEL org.opencontainers.image.version="1.0"

# Configuration des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:/app/.venv/bin:$PATH" \
    UV_TIMEOUT=1800 \
    UV_BUILD_JOBS=4 \
    UV_PIP_COMPILE_TIMEOUT=600

# Installation des dépendances système
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv avec vérification du cache
ADD --chmod=755 --checksum=sha256:abc123... https://astral.sh/uv/install.sh /install.sh
RUN --mount=type=cache,target=/root/.cache/uv \
    /install.sh && rm /install.sh

WORKDIR /app

# Création et activation de l'environnement virtuel
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv

# Configuration du cache pour pip
ENV PIP_CACHE_DIR=/root/.cache/pip \
    PIP_NO_CACHE_DIR=false
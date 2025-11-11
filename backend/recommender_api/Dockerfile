# Stage 1: Builder
FROM python:3.11-slim-bullseye AS builder
ARG BUILD_DATE

WORKDIR /app

# Labels standards OCI
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay Recommender API" \
      org.opencontainers.image.description="Service API de recommandation musicale"

# Installation des dépendances système pour la compilation (builder only)
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libpq-dev \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Configuration du timeout uv et PATH
ENV UV_TIMEOUT=300 \
    UV_HTTP_TIMEOUT=180 \
    PATH="/usr/local/bin:$PATH"

# Installation de uv via le script officiel (plus rapide que pip install uv)
RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -sf /root/.local/bin/uv /usr/local/bin/uv && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

COPY --link backend/recommender_api/requirements.txt ./
# Utiliser uv pip install directement pour installer toutes les dépendances (+ dépendances transitives) dans /install_recommender
# uv gère les dépendances transitives mieux que pip wheel et est plus rapide
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    /root/.local/bin/uv pip install --target /install_recommender --no-cache-dir -r requirements.txt || true

# Stage 2: Runner (use shared base image)
FROM soniquebay/base:optim AS runner

WORKDIR /app

# Copy the built python packages from builder
COPY --from=builder /install_recommender /usr/local/lib/python3.11/site-packages

# Bring in healthcheck script and app files
COPY --link scripts/healthcheck.sh /healthcheck.sh
USER root
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /logs /app/backend/recommender_api/data /app/data && \
    chown -R soniquebay:soniquebay /logs /app/backend/recommender_api/data /app/data && \
    chmod +x /healthcheck.sh

# Copier le script d'entrypoint qui appliquera chown sur les volumes montés au démarrage
COPY --link backend/recommender_api/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY --link backend/recommender_api /app/backend/recommender_api
COPY --link backend/recommender_api/alembic_recommender.ini /app/alembic_recommender.ini
COPY --link backend/recommender_api/alembic_recommender /app/alembic_recommender

# Ensure sqlite_vec permissions if present
RUN python3 -c "import sqlite_vec; print('sqlite-vec import check')" 2>/dev/null || true
RUN python3 -m uvicorn --version 2>/dev/null || true

# Laisser l'entrypoint s'exécuter en tant que root ; il basculera proprement vers l'utilisateur non-root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


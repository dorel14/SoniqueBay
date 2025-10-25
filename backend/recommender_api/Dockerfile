# Stage 1: Builder
FROM do14500352/soniquebay-base:latest AS builder

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

# Installation des dépendances système pour la compilation
RUN --mount=type=cache,target=/var/cache/apt,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances spécifiques
# Configuration du timeout UV et PATH
ENV UV_TIMEOUT=300 \
    UV_HTTP_TIMEOUT=180 \
    PATH="/usr/local/bin:$PATH"

COPY --link backend/recommender_api/requirements.txt ./
# Installation des dépendances avec UV et cache
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    uv pip install --system -r requirements.txt && \
    # Installation explicite d'uvicorn
    uv pip install --system "uvicorn[standard]>=0.22.0" && \
    # Vérification des installations (sans sqlite_vec pour éviter les problèmes de compilation)
    python3 -c "import fastapi, uvicorn, sqlite_vec; print('Dependencies OK')" && \
    which uvicorn || echo "uvicorn not in PATH, but should work"

# Stage 2: Runner
FROM do14500352/soniquebay-base:latest AS runner

WORKDIR /app

# Copie de l'environnement virtuel et des fichiers
# Copie des packages Python
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Vérification finale et permissions
RUN python3 -m uvicorn --version && \
    # S'assurer que les permissions sont correctes
    chmod 755 /usr/local/lib/python3.11/site-packages/sqlite_vec/vec0.so 2>/dev/null || echo "sqlite_vec permissions already set"
COPY --link scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Copie des fichiers de l'application D'ABORD
COPY --link backend/recommender_api /app/backend/recommender_api
COPY --link backend/recommender_api/alembic_recommender.ini /app/alembic_recommender.ini
COPY --link backend/recommender_api/alembic_recommender /app/alembic_recommender

# Copie des site-packages après les fichiers d'application
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Vérification finale et permissions
RUN python3 -c "import sqlite_vec; print('sqlite-vec import successful')" && \
    python3 -m uvicorn --version && \
    # S'assurer que les permissions sont correctes
    chmod 755 /usr/local/lib/python3.11/site-packages/sqlite_vec/vec0.so 2>/dev/null || echo "permissions already set"

# Configuration du healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /healthcheck.sh


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
    # Création du lien symbolique pour uvicorn
    ln -sf /usr/local/bin/uvicorn /usr/bin/uvicorn && \
    # Vérification des installations
    python3 -c "import sqlite_vec; print(f'sqlite-vec installé dans: {sqlite_vec.__file__}')" && \
    ls -l /usr/local/lib/python3.11/site-packages/sqlite_vec/ && \
    which uvicorn

# Stage 2: Runner
FROM do14500352/soniquebay-base:latest AS runner

WORKDIR /app

# Copie de l'environnement virtuel et des fichiers
# Copie des packages Python
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Vérification finale et permissions
RUN uvicorn --version && \
    # S'assurer que les permissions sont correctes
    chmod 755 /usr/local/lib/python3.11/site-packages/sqlite_vec/vec0.so
COPY --link scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Copie des fichiers de l'application
COPY --link backend/recommender_api /app/backend/recommender_api
COPY --link backend/recommender_api/alembic_recommender.ini /app/alembic_recommender.ini
COPY --link backend/recommender_api/alembic_recommender /app/alembic_recommender

# Configuration du healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /healthcheck.sh


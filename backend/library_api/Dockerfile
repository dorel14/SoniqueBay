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
      org.opencontainers.image.title="SoniqueBay Library API" \
      org.opencontainers.image.description="Service API de gestion de la bibliothèque musicale"

# Configuration du timeout UV
ENV UV_TIMEOUT=300 \
    UV_HTTP_TIMEOUT=180

# Copie et installation des dépendances spécifiques
COPY --link backend/library_api/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    uv pip install --system -r requirements.txt && \
    # Vérification de l'installation
    python3 -m uvicorn --version && \
    ln -sf $(which python3) /usr/local/bin/python

# Stage 2: Runner
FROM do14500352/soniquebay-base:latest AS runner

WORKDIR /app

# Copie des fichiers de l'application D'ABORD
COPY --link backend/library_api /app/backend/library_api
COPY --link alembic /app/alembic
COPY --link alembic.ini /app/alembic.ini

# Copie de l'environnement virtuel et des fichiers
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --link scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh && \
    # Vérification finale
    python3 -c "import strawberry; print('strawberry import successful')" && \
    python3 -m uvicorn --version && \
    ln -sf $(which python3) /usr/local/bin/python

# Ajout de l'entrée par défaut
CMD ["python3", "-m", "uvicorn", "backend.library_api.api_app:create_api", "--host", "0.0.0.0", "--port", "8001"]

# Configuration du healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /healthcheck.sh


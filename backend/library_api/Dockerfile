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
      org.opencontainers.image.title="SoniqueBay Library API" \
      org.opencontainers.image.description="Service API de gestion de la bibliothèque musicale"

# Configuration du timeout uv
ENV UV_TIMEOUT=300 \
    UV_HTTP_TIMEOUT=180

# Installation de uv via le script officiel (plus rapide que pip install uv)
RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -sf /root/.local/bin/uv /usr/local/bin/uv && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Copie et installation des dépendances spécifiques
COPY --link backend/library_api/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    /root/.local/bin/uv pip install --target /install_library --no-cache-dir -r requirements.txt || true

# Stage 2: Runner
FROM soniquebay/base:optim AS runner

WORKDIR /app

# Copie des fichiers de l'application D'ABORD
COPY --link backend/library_api /app/backend/library_api
COPY --link alembic /app/alembic
COPY --link alembic.ini /app/alembic.ini

# Copie de l'environnement virtuel depuis builder (uv pip install --target génère site-packages directement)
COPY --from=builder /install_library /usr/local/lib/python3.11/site-packages
COPY --link scripts/healthcheck.sh /healthcheck.sh
USER root
# installer gosu (pour basculer d'utilisateur proprement au démarrage) puis créer les répertoires de logs et données
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /logs /app/backend/library_api/data /app/data && chown -R soniquebay:soniquebay /logs /app/backend/library_api/data /app/data && \
    chmod +x /healthcheck.sh && \
    # Vérification finale
    python3 -c "import strawberry; print('strawberry import successful')" && \
    python3 -m uvicorn --version && \
    ln -sf $(which python3) /usr/local/bin/python

# Copier le script d'entrypoint qui appliquera chown sur les volumes montés au démarrage
COPY --link backend/library_api/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Laisser l'entrypoint s'exécuter en tant que root ; il basculera proprement vers l'utilisateur non-root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Ajout de l'entrée par défaut
CMD ["python3", "-m", "uvicorn", "backend.library_api.api_app:create_api", "--host", "0.0.0.0", "--port", "8001"]

# Configuration du healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /healthcheck.sh


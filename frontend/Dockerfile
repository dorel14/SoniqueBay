# Étape d'extraction de version
FROM python:3.11-slim AS version_extractor
COPY _version_.py /_version_.py
RUN python -c "from _version_ import __version__; print(__version__)" > /version.txt

# Stage 1: Builder
FROM python:3.11-slim-bullseye AS builder

ARG BUILD_DATE
# Labels standards OCI
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay Frontend" \
      org.opencontainers.image.description="Interface utilisateur de l'application SoniqueBay"

# Installation des dépendances système supplémentaires
RUN --mount=type=cache,target=/var/cache/apt/builder \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv via le script officiel (plus rapide que pip install uv)
RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -sf /root/.local/bin/uv /usr/local/bin/uv && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/frontend

# Copie et installation des dépendances spécifiques
COPY --link ./frontend/requirements.txt ./
ENV UV_TIMEOUT=300 \
    UV_HTTP_TIMEOUT=180
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    /root/.local/bin/uv pip install --target /install_frontend --no-cache-dir -r requirements.txt || true

# Stage 2: Runner

FROM soniquebay/base:optim AS runner

# Copier la version extraite
COPY --from=version_extractor /version.txt /version.txt

# Configuration des variables d'environnement
ARG LOCALE_LANGUAGE=en_US
ARG ENV_LOCALE_LANGUAGE
ENV LOCALE_LANGUAGE=${ENV_LOCALE_LANGUAGE:-${LOCALE_LANGUAGE}}

ARG TZ=UTC
ARG ENV_TZ
ENV TZ=${ENV_TZ:-${TZ}}

# Créer les répertoires de données et logs avec permissions correctes
USER root
RUN mkdir -p /logs /app/frontend/data /app/data && \
    chown -R soniquebay:soniquebay /logs /app/frontend/data /app/data

# Copier l'entrypoint qui appliquera chown sur les volumes montés au démarrage
COPY --link ./frontend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copier les packages Python depuis le builder (uv pip install --target génère directement site-packages)
COPY --from=builder /install_frontend /usr/local/lib/python3.11/site-packages

# Copier les fichiers applicatifs
COPY --link ./frontend /app/frontend

WORKDIR /app/frontend

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "start_ui.py"]
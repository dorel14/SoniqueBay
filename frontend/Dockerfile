# Stage 1: Builder
FROM do14500352/soniquebay-base:latest AS builder

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

WORKDIR /app/frontend

# Copie et installation des dépendances spécifiques
COPY --link ./frontend/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Stage 2: Runner
FROM do14500352/soniquebay-base:latest AS runner

# Configuration des variables d'environnement
ARG LOCALE_LANGUAGE=en_US
ARG ENV_LOCALE_LANGUAGE
ENV LOCALE_LANGUAGE=${ENV_LOCALE_LANGUAGE:-${LOCALE_LANGUAGE}}

ARG TZ=UTC
ARG ENV_TZ
ENV TZ=${ENV_TZ:-${TZ}}

# Installation des dépendances système supplémentaires
RUN --mount=type=cache,target=/var/cache/apt/runner \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copie de l'environnement virtuel et des fichiers
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --link ./frontend /app/frontend

WORKDIR /app/frontend


CMD ["python", "/app/frontend/start_ui.py"]
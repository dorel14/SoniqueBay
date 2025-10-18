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
      org.opencontainers.image.title="SoniqueBay Backend Worker" \
      org.opencontainers.image.description="Service worker pour le traitement des tâches en arrière-plan"

# Installation des dépendances système supplémentaires
RUN --mount=type=cache,target=/var/cache/apt/builder \
    apt-get update && apt-get install -y --no-install-recommends \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /backend_worker

# Copie et installation des dépendances spécifiques
COPY --link ./backend_worker/requirements.txt /backend_worker/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Stage 2: Runner
FROM do14500352/soniquebay-base:latest AS runner

# Configuration des variables d'environnement
ARG LOCALE_LANGUAGE=en_US
ARG ENV_LOCALE_LANGUAGE
ENV LOCALE_LANGUAGE=${ENV_LOCALE_LANGUAGE:-${LOCALE_LANGUAGE}} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/usr/local/bin:$PATH"

ARG TZ=UTC
ARG ENV_TZ
ENV TZ=${ENV_TZ:-${TZ}}

# Installation des dépendances système supplémentaires
RUN --mount=type=cache,target=/var/cache/apt/runner \
    apt-get update && apt-get install -y --no-install-recommends \
    nfs-common \
    cifs-utils \
    locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=${LANG} && \
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copie de l'environnement virtuel et des binaires
COPY --from=builder --link /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --link /usr/local/bin /usr/local/bin

WORKDIR /app


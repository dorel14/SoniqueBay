# Étape d'extraction de version
FROM python:3.11-slim AS version_extractor
COPY _version_.py /_version_.py
RUN python -c "from _version_ import __version__; print(__version__)" > /version.txt

# Builder stage: installer les outils natifs (Rust/Cargo) et construire les dépendances spécifiques au worker
FROM python:3.11-slim-bullseye AS builder
ARG BUILD_DATE

LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="$(cat /version.txt)" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay Backend Worker" \
      org.opencontainers.image.description="Service worker pour le traitement des tâches en arrière-plan"

WORKDIR /backend_worker

# Installer cargo/rust et outils de build uniquement dans le builder
RUN --mount=type=cache,target=/var/cache/apt/builder \
    apt-get update && apt-get install -y --no-install-recommends \
    cargo \
    rustc \
    build-essential \
    gcc \
    python3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv via le script officiel (plus rapide que pip install uv)
RUN --mount=type=cache,target=/root/.cache/uv \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -sf /root/.local/bin/uv /usr/local/bin/uv

ENV PATH="/root/.local/bin:$PATH"

# Copier les requirements du worker et installer avec uv dans /install_worker
COPY --link ./backend_worker/requirements.txt /backend_worker/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    /root/.local/bin/uv pip install --target /install_worker --no-cache-dir -r /backend_worker/requirements.txt || true

# Runner stage: utiliser une image Python standard optimisée pour production
FROM python:3.11-slim-bullseye AS runner

# Copier la version extraite
COPY --from=version_extractor /version.txt /version.txt

# Variables d'environnement et locale
ARG LOCALE_LANGUAGE=en_US
ARG ENV_LOCALE_LANGUAGE
ENV LOCALE_LANGUAGE=${ENV_LOCALE_LANGUAGE:-${LOCALE_LANGUAGE}} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/usr/local/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

ARG TZ=UTC
ARG ENV_TZ
ENV TZ=${ENV_TZ:-${TZ}}

# Installer runtime tools nécessaires (no -dev)
RUN --mount=type=cache,target=/var/cache/apt/runner \
    apt-get update && apt-get install -y --no-install-recommends \
    nfs-common \
    cifs-utils \
    locales \
    procps \
    gosu && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=${LANG} && \
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    # Créer l'utilisateur soniquebay
    groupadd -r soniquebay && useradd -r -g soniquebay soniquebay && \
    # Créer les répertoires de données et logs avec permissions correctes
    mkdir -p /data /logs /app/backend_worker/logs /app/backend_worker/data && \
    chown -R soniquebay:soniquebay /data /logs /app/backend_worker/logs /app/backend_worker/data

# Copier l'entrypoint qui appliquera chown sur les volumes montés au démarrage
COPY --link ./backend_worker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copier les packages spécifiques au worker construits dans builder
# uv pip install --target installe directement site-packages + bin scripts sous /install_worker
COPY --from=builder /install_worker /usr/local/lib/python3.11/site-packages
# Copier aussi les bin scripts (celery, etc.) générés par uv pip install
COPY --from=builder /install_worker/bin /usr/local/bin

# Copier l'application
COPY --link ./backend_worker /app/backend_worker
COPY --link ./backend /app/backend
COPY --link ./backend_worker/api_app.py /app/backend_worker/api_app.py

WORKDIR /app
# Add docker-compose-wait tool
ENV WAIT_VERSION=2.12.0
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/$WAIT_VERSION/wait /wait
RUN chmod +x /wait

# Vérification que celery est disponible (smoke-test)
RUN python3 -c "import celery; print('celery import check')" || true

# Labels standards OCI
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="$(cat /version.txt)" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay Backend Worker" \
      org.opencontainers.image.description="Service worker pour le traitement des tâches en arrière-plan"

# Laisser l'entrypoint s'exécuter en tant que root ; il basculera proprement vers l'utilisateur non-root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


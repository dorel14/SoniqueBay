# Étape d'extraction de version
FROM python:3.11-slim AS version_extractor
COPY _version_.py /_version_.py
RUN python -c "from _version_ import __version__; print(__version__)" > /version.txt

FROM pgautoupgrade/pgautoupgrade:17-debian

ARG LOCALE_LANGUAGE=en_US

# Copier la version extraite
COPY --from=version_extractor /version.txt /version.txt

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    postgresql-contrib-17 \
    locales-all \
    tzdata \
    git \
    build-essential \
    postgresql-server-dev-17 \
    && locale-gen ${LOCALE_LANGUAGE}.UTF-8 \
    && update-locale LANG=${LOCALE_LANGUAGE}.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Installer pgvector depuis les sources
RUN git clone https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make CC=gcc OPTFLAGS="-O2" && \
    make install && \
    cd / && \
    rm -rf /tmp/pgvector

# Nettoyer les dépendances de build
RUN apt-get remove --purge -y git build-essential postgresql-server-dev-17 && \
    apt-get autoremove -y && \
    apt-get clean

# Copier les scripts d'initialisation
COPY db_folder/db_init/ /docker-entrypoint-initdb.d/

# Exposer le port PostgreSQL
EXPOSE 5432

# Labels standards OCI
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="$(cat /version.txt)" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay PostgreSQL Image" \
      org.opencontainers.image.description="Image de base de donnée pour SoniqueBay"
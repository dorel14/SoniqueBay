# Dockerfile pour Supabase PostgreSQL avec extensions
# Basé sur l'image officielle Supabase Postgres

FROM supabase/postgres:15.1.0.117

# Arguments pour la configuration
ARG LOCALE_LANGUAGE=en_US
ARG JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long

# Installer les locales
RUN apt-get update && apt-get install -y \
    locales-all \
    tzdata \
    && locale-gen ${LOCALE_LANGUAGE}.UTF-8 \
    && update-locale LANG=${LOCALE_LANGUAGE}.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Les extensions sont déjà installées dans l'image Supabase:
# - uuid-ossp
# - pg_trgm  
# - pgcrypto
# - vector (pgvector)

# Copier les scripts d'initialisation
COPY supabase/db_init/ /docker-entrypoint-initdb.d/

# Copier le script d'entrypoint personnalisé
COPY supabase/scripts/entrypoint.sh /usr/local/bin/custom-entrypoint.sh
RUN chmod +x /usr/local/bin/custom-entrypoint.sh

# Exposer le port PostgreSQL
EXPOSE 5432

# Utiliser l'entrypoint personnalisé
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
CMD ["postgres"]

# Labels standards OCI
LABEL org.opencontainers.image.source="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.url="https://github.com/dorel14/SoniqueBay-app" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.authors="SoniqueBay Team" \
      org.opencontainers.image.vendor="SoniqueBay" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="SoniqueBay Supabase PostgreSQL" \
      org.opencontainers.image.description="Image Supabase PostgreSQL pour SoniqueBay avec extensions vectorielles - v0.2.0"

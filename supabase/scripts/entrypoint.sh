#!/bin/bash
# Entrypoint personnalisé pour Supabase PostgreSQL
# Crée automatiquement le schéma auth nécessaire pour GoTrue

set -e

# Fonction pour attendre que PostgreSQL soit prêt
wait_for_postgres() {
    echo "⏳ Attente du démarrage de PostgreSQL..."
    until pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
        echo "   En attente de PostgreSQL..."
        sleep 1
    done
    echo "✅ PostgreSQL est prêt"
}

# Fonction pour créer le schéma auth
create_auth_schema() {
    echo "🔧 Création du schéma auth pour GoTrue..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        CREATE SCHEMA IF NOT EXISTS auth;
        GRANT ALL ON SCHEMA auth TO $POSTGRES_USER;
        ALTER SCHEMA auth OWNER TO $POSTGRES_USER;
        
        -- Créer également les extensions si elles n'existent pas
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE EXTENSION IF NOT EXISTS "vector";
EOSQL
    echo "✅ Schéma auth et extensions créés avec succès"
}

# Si c'est la commande postgres, initialiser d'abord
if [ "$1" = "postgres" ] || [ "$1" = "/usr/local/bin/docker-entrypoint.sh" ] || [ "$1" = "docker-entrypoint.sh" ]; then
    # Exécuter l'entrypoint original en arrière-plan pour démarrer PostgreSQL
    echo "🚀 Démarrage de PostgreSQL avec initialisation automatique du schéma auth..."
    
    # Appeler l'entrypoint original avec la commande postgres
    # et créer le schéma auth une fois prêt
    (
        # Attendre que PostgreSQL démarre via l'entrypoint original
        sleep 10
        wait_for_postgres
        create_auth_schema
    ) &
    
    # Exécuter l'entrypoint original
    exec /usr/local/bin/docker-entrypoint.sh postgres
else
    # Pour toute autre commande, exécuter directement
    exec "$@"
fi

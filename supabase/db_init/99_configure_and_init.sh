#!/bin/bash
set -e

echo "🔧 Configuration initiale de PostgreSQL..."

# Configurer PostgreSQL pour écouter sur toutes les interfaces
if [ -f "/var/lib/postgresql/data/postgresql.conf" ]; then
    sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/postgresql/data/postgresql.conf
    sed -i "s/^listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/postgresql/data/postgresql.conf
    echo "   ✅ listen_addresses configuré sur '*'"
fi

# Configurer pg_hba.conf pour accepter les connexions depuis n'importe où
if [ -f "/var/lib/postgresql/data/pg_hba.conf" ]; then
    # Supprimer les lignes existantes qui pourraient bloquer
    sed -i '/^host all all all /d' /var/lib/postgresql/data/pg_hba.conf
    sed -i '/^host all all 0.0.0.0\/0 /d' /var/lib/postgresql/data/pg_hba.conf
    # Ajouter la règle d'acceptation
    echo "host all all 0.0.0.0/0 trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "   ✅ pg_hba.conf configuré pour accepter toutes les connexions"
fi

# Créer le schéma auth pour GoTrue
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
echo "   ✅ Schéma auth et extensions créés avec succès"

# Recharger la configuration pour appliquer les changements
pg_ctl reload -D /var/lib/postgresql/data || echo "   ⚠️ Reload échoué, redémarrage nécessaire"

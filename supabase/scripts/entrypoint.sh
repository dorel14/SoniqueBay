#!/bin/bash
# Entrypoint personnalisé pour Supabase PostgreSQL
# Crée automatiquement le schéma auth nécessaire pour GoTrue

set -e

# Fonction pour configurer PostgreSQL pour accepter les connexions externes
configure_postgres() {
    echo "🔧 Configuration de PostgreSQL pour les connexions externes..."
    
    # Modifier postgresql.conf pour écouter sur toutes les interfaces
    if [ -f "/var/lib/postgresql/data/postgresql.conf" ]; then
        sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/postgresql/data/postgresql.conf
        sed -i "s/^listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/postgresql/data/postgresql.conf
        echo "   ✅ listen_addresses configuré"
    fi
    
    # Modifier pg_hba.conf pour accepter les connexions depuis n'importe où
    if [ -f "/var/lib/postgresql/data/pg_hba.conf" ]; then
        # Remplacer la ligne scram-sha-256 par trust pour les connexions host
        sed -i 's/^host all all all scram-sha-256/host all all 0.0.0.0\/0 trust/' /var/lib/postgresql/data/pg_hba.conf
        # S'assurer que les connexions locales sont aussi en trust
        sed -i 's/^host all all 127.0.0.1\/32 scram-sha-256/host all all 127.0.0.1\/32 trust/' /var/lib/postgresql/data/pg_hba.conf
        sed -i 's/^host all all ::1\/128 scram-sha-256/host all all ::1\/128 trust/' /var/lib/postgresql/data/pg_hba.conf
        echo "   ✅ pg_hba.conf configuré"
    fi
}

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
    echo "🚀 Démarrage de PostgreSQL avec initialisation automatique du schéma auth..."
    
    # Créer un script d'initialisation qui sera exécuté après le démarrage de PostgreSQL
    # mais avant qu'il ne commence à accepter des connexions externes
    INIT_SCRIPT="/docker-entrypoint-initdb.d/99_configure_and_init.sh"
    
    cat > "$INIT_SCRIPT" << 'EOFINIT'
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
EOFINIT

    chmod +x "$INIT_SCRIPT"
    
    # Exécuter l'entrypoint original
    exec /usr/local/bin/docker-entrypoint.sh postgres
else
    # Pour toute autre commande, exécuter directement
    exec "$@"
fi

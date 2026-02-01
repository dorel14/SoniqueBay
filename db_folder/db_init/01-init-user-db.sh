#!/bin/bash

set -e

# Set default values for environment variables if not set
: ${TZ:="UTC"}
: ${LOCALE_LANGUAGE:="en_US"}

# Set environment variables for timezone and locale
export TZ=${TZ}
export LANG=${LOCALE_LANGUAGE}.UTF-8
export LANGUAGE=${LOCALE_LANGUAGE}.UTF-8
export LC_ALL=${LOCALE_LANGUAGE}.UTF-8

# Create postgres superuser only if it doesn't exist and POSTGRES_USER is different
if [ "$POSTGRES_USER" != "postgres" ]; then
    echo "Creating postgres superuser..."
    createuser -U "$POSTGRES_USER" --superuser postgres || echo "User postgres may already exist or creation skipped"
fi

# Check if a backup exists and restore it
BACKUP_FILE="/db_folder/backup.sql"
if [ -f "$BACKUP_FILE" ]; then
    echo "📦 Backup file found. Checking file integrity..."

    # Basic check for file integrity (not empty and contains SQL)
    if [ -s "$BACKUP_FILE" ] && grep -q "CREATE TABLE\|INSERT INTO\|CREATE DATABASE" "$BACKUP_FILE"; then
        echo "📦 Backup file appears valid. Attempting to restore..."

        # Attempt to restore with error handling
        if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < "$BACKUP_FILE"; then
            echo "✅ Database restored successfully from backup!"
        else
            echo "❌ Error restoring from backup. Creating a new database instead..."
            # Fall through to the database creation code
            CREATE_NEW_DB=true
        fi
    else
        echo "⚠️ Backup file appears invalid or empty. Creating a new database instead..."
        CREATE_NEW_DB=true
    fi
else
    echo "📦 No backup found. Creating a new database..."
    CREATE_NEW_DB=true
fi

# Create a new database if needed
if [ "$CREATE_NEW_DB" = true ]; then
    echo "🔧 Creating new database and user..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" template1 <<EOSQL
        SELECT 'CREATE DATABASE ${POSTGRES_DB}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\gexec
        GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};

EOSQL

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname ${POSTGRES_DB} <<EOSQL
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
        CREATE EXTENSION IF NOT EXISTS unaccent;
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

    echo "✅ New database and user created successfully!"
fi

echo "🚀 Database initialization complete!"

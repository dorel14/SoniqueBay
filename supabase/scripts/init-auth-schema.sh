#!/bin/bash
# Script d'initialisation du schéma auth pour Supabase
# Ce script crée le schéma auth nécessaire pour le service GoTrue

set -e

echo "⏳ Attente du démarrage de supabase-db..."
until docker exec soniquebay-supabase-db pg_isready -U supabase -d postgres > /dev/null 2>&1; do
    echo "   En attente de supabase-db..."
    sleep 2
done

echo "✅ supabase-db est prêt"

echo "🔧 Création du schéma auth..."
docker exec -i soniquebay-supabase-db env PGPASSWORD="${SUPABASE_DB_PASSWORD:-supabase}" psql -h localhost -p 5432 -U supabase -d postgres -c "
CREATE SCHEMA IF NOT EXISTS auth;
GRANT ALL ON SCHEMA auth TO supabase;
"

echo "✅ Schéma auth créé avec succès"

echo "🚀 Redémarrage de supabase-auth..."
docker stop soniquebay-supabase-auth 2>/dev/null || true
docker rm soniquebay-supabase-auth 2>/dev/null || true
docker-compose up -d supabase-auth

echo "⏳ Attente du démarrage de supabase-auth..."
sleep 5

# Vérifier si le service est healthy
if docker ps | grep -q "soniquebay-supabase-auth"; then
    echo "✅ supabase-auth démarré avec succès"
else
    echo "❌ supabase-auth n'a pas démarré correctement"
    echo "Logs du service :"
    docker-compose logs --tail=20 supabase-auth
    exit 1
fi

echo "🎉 Initialisation du schéma auth terminée"

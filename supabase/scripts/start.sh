#!/bin/bash
# Script pour démarrer les services Supabase
# Usage: ./supabase/scripts/start.sh

set -e

echo "🚀 Démarrage des services Supabase..."

# Vérifier si docker-compose est disponible
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose n'est pas installé"
    exit 1
fi

# Étape 1: Démarrer supabase-db en premier (avec entrypoint automatique pour auth)
echo "📦 Démarrage de supabase-db..."
docker-compose up -d supabase-db

echo "⏳ Attente de l'initialisation de la base de données (schéma auth créé automatiquement)..."
sleep 20

# Étape 2: Démarrer les autres services Supabase
echo "📦 Démarrage des autres services Supabase..."
docker-compose up -d supabase-realtime supabase-auth supabase-meta supabase-dashboard

echo "⏳ Attente du démarrage complet..."
sleep 10

# Vérifier l'état des services
services=("supabase-db" "supabase-realtime" "supabase-auth" "supabase-meta" "supabase-dashboard")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✅ $service est démarré"
    else
        echo "❌ $service n'est pas démarré"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 Services Supabase démarrés avec succès!"
    echo ""
    echo "📊 URLs d'accès:"
    echo "   - Dashboard (Studio): http://localhost:54325"
    echo "   - Database: localhost:54322"
    echo "   - Realtime: localhost:54323"
    echo "   - Auth: localhost:54324"
    echo ""
    echo "🔑 Tokens JWT (développement):"
    echo "   - Anon Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    echo "   - Service Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
else
    echo ""
    echo "⚠️  Certains services n'ont pas démarré correctement"
    echo "   Consultez les logs: docker-compose logs [service-name]"
fi

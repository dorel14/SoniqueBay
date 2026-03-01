#!/bin/bash
# Script pour afficher les logs des services Supabase
# Usage: ./supabase/scripts/logs.sh [service-name]

SERVICE=$1

declare -A services=(
    ["db"]="supabase-db"
    ["realtime"]="supabase-realtime"
    ["auth"]="supabase-auth"
    ["meta"]="supabase-meta"
    ["dashboard"]="supabase-dashboard"
)

if [ -n "$SERVICE" ]; then
    if [ -n "${services[$SERVICE]}" ]; then
        container_name=${services[$SERVICE]}
        echo "📋 Logs pour $container_name..."
        docker-compose logs -f $container_name
    else
        echo "❌ Service inconnu: $SERVICE"
        echo "Services disponibles: db, realtime, auth, meta, dashboard"
    fi
else
    echo "📋 Logs de tous les services Supabase..."
    docker-compose logs -f supabase-db supabase-realtime supabase-auth supabase-meta supabase-dashboard
fi

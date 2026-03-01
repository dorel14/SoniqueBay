#!/bin/bash
# Script pour arrêter les services Supabase
# Usage: ./supabase/scripts/stop.sh

set -e

echo "🛑 Arrêt des services Supabase..."

docker-compose stop supabase-db supabase-realtime supabase-auth supabase-meta supabase-dashboard

echo "✅ Services Supabase arrêtés"

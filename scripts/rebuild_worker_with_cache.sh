#!/bin/bash
# Script pour rebuild l'image worker en préservant le cache HuggingFace
# Usage: ./rebuild_worker_with_cache.sh

set -e

echo "🔄 Rebuild de l'image celery-worker avec cache HuggingFace persistant..."

# Vérifier que le dossier cache existe sur l'hôte
if [ ! -d "./data/huggingface_cache" ]; then
    echo "📁 Création du dossier data/huggingface_cache..."
    mkdir -p ./data/huggingface_cache
fi

# Afficher la taille actuelle du cache
if [ -d "./data/huggingface_cache" ]; then
    CACHE_SIZE=$(du -sh ./data/huggingface_cache 2>/dev/null | cut -f1 || echo "0B")
    echo "📊 Taille actuelle du cache HuggingFace: $CACHE_SIZE"
fi

# Stopper le worker
echo "🛑 Arrêt du conteneur celery-worker..."
docker-compose stop celery-worker

# Rebuild l'image
echo "🔨 Rebuild de l'image..."
docker-compose build --no-cache celery-worker

# Redémarrer avec le volume monté
echo "🚀 Démarrage du worker avec cache persistant..."
docker-compose up -d celery-worker

# Vérifier que le cache est bien monté
echo "🔍 Vérification du montage du cache..."
docker-compose exec celery-worker ls -la /root/.cache/huggingface/ 2>/dev/null || echo "⚠️  Le cache n'est pas encore peuplé"

echo "✅ Rebuild terminé!"
echo ""
echo "💡 Le cache HuggingFace est maintenant persistant dans ./data/huggingface_cache"
echo "💡 Lors des prochains rebuilds, les modèles ne seront pas re-téléchargés"

#!/bin/sh
set -e

# Créer les répertoires nécessaires s'ils n'existent pas
mkdir -p /logs /app/frontend/data /app/data

# Corriger les permissions sur les volumes montés (liaison depuis l'hôte)
# On ajoute || true pour ignorer les erreurs si les répertoires ne peuvent pas être modifiés
chown -R soniquebay:soniquebay /logs /app/frontend/data /app/data 2>/dev/null || true

# Basculer vers l'utilisateur non-root avant d'exécuter le service
# exec su -s /bin/sh soniquebay -c "exec \"$@\""
exec "$@"

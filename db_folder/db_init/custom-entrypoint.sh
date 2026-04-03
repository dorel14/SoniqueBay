#!/bin/bash
set -e

# 1. Lancer Postgres en arrière-plan
# On utilise l'entrypoint officiel pour ne pas casser la configuration standard
docker-entrypoint.sh postgres &

# 2. Fonction pour attendre que Postgres soit prêt
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  echo "Attente de la base de données..."
  sleep 2
done

echo "PostgreSQL est prêt. Exécution des scripts de maintenance..."

# 3. Boucler sur le dossier /sql
# On vérifie si le dossier contient des fichiers pour éviter les erreurs de boucle vide
if [ -d "/sql" ] && [ "$(ls -A /sql/*.sql 2>/dev/null)" ]; then
  for f in /sql/*.sql; do
    echo "Exécution de : $f"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
  done
else
  echo "Aucun script SQL trouvé dans /sql."
fi

echo "Maintenance terminée."

# 4. Ramener le processus Postgres au premier plan pour que le conteneur reste actif
wait
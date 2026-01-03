#!/bin/sh
set -e

# Ensure directories exist and correct ownership (useful when host bind mounts overwrite permissions)
# Create all required directories with proper permissions
REQUIRED_DIRS="/home/soniquebay /app/data /app/data/models /app/data/celery_beat_data /app/data/search_indexes /app/data/whoosh_index /app/backend_worker/data /app/backend_worker/logs"

# Create directories and set permissions
for dir in $REQUIRED_DIRS; do
  mkdir -p "$dir"
  # Only try chown if directory exists and is writable
  if [ -d "$dir" ] && [ -w "$dir" ]; then
    chown -R soniquebay:soniquebay "$dir" || true
    # Ensure parent directories are writable
    parent_dir=$(dirname "$dir")
    [ -d "$parent_dir" ] && chmod 775 "$parent_dir" || true
    chmod 775 "$dir" || true
  else
    echo "[ENTRYPOINT] Avertissement: Impossible de définir les permissions pour $dir - peut-être monté en lecture seule ou inexistant"
  fi
done

# Fix permissions on existing Celery Beat schedule file if it exists
if [ -f /data/celery_beat_data/celerybeat-schedule.db ]; then
    chown soniquebay:soniquebay /data/celery_beat_data/celerybeat-schedule.db || true
fi

# Wait for PostgreSQL to be ready
/wait

# Initialize data directories before starting any service
echo "[ENTRYPOINT] Initialisation des répertoires de données..."
if [ -f /app/backend_worker/services/data_directory_initializer.py ]; then
    # Run directory initialization as soniquebay user
    su - soniquebay -c "cd /app && python -c 'from backend_worker.services.data_directory_initializer import initialize_data_directories; initialize_data_directories()'"
    echo "[ENTRYPOINT] Répertoires de données initialisés"
    
    # Validate data access after initialization
    if ! su - soniquebay -c "cd /app && python -c 'from backend_worker.services.data_directory_initializer import validate_data_access; exit(0 if validate_data_access() else 1)'"; then
        echo "[ENTRYPOINT] ERREUR: Accès aux répertoires de données impossible! Vérifiez les permissions."
        exit 1
    fi
else
    echo "[ENTRYPOINT] Service d'initialisation non trouvé, utilisation des répertoires par défaut"
fi

# If first arg looks like an option, prepend the default command
if [ "${1#-}" != "$1" ]; then
  set -- celery "$@"
fi

# If gosu is available use it to drop privileges cleanly, otherwise fallback to su
if command -v gosu >/dev/null 2>&1; then
  exec gosu soniquebay "$@"
else
  exec su -s /bin/sh soniquebay -c "exec "$@""
fi

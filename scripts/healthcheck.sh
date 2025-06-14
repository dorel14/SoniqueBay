#!/bin/bash

# Désactiver la redirection automatique de curl
# Afficher les entêtes pour le débogage
status_code=$(curl -s -o /dev/null -w "%{http_code}" \
              --max-redirs 0 \
              --no-location \
              http://localhost:8001/api/healthcheck)

echo "Status code: $status_code"

if [ "$status_code" -eq 200 ]; then
    exit 0
else
    exit 1
fi
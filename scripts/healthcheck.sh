#!/bin/bash

# Vérification de l'endpoint healthcheck
# L'option -f fait échouer silencieusement curl en cas d'erreur HTTP
# L'option -s supprime la barre de progression
response=$(curl -f -s http://localhost:${HEALTHCHECK_PORT:-8000}/api/healthcheck)
status=$?

if [ $status -eq 0 ]; then
    # Le service répond correctement
    exit 0
else
    # Le service ne répond pas
    exit 1
fi
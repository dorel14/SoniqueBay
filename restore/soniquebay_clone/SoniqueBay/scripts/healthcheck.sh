#!/bin/bash

# Vérification de l'endpoint healthcheck
# L'option -f fait échouer silencieusement curl en cas d'erreur HTTP
# L'option -s supprime la barre de progression

# Récupérer le port depuis les variables d'environnement
PORT=${HEALTHCHECK_PORT:-8000}

# Dans Docker, utiliser les aliases réseau définis dans docker-compose
# api:8001 et recommender:8002 selon le docker-compose-scan-optimized.yml

echo "Healthcheck: Container $(hostname) on port $PORT"

# Déterminer l'URL basée sur le nom du conteneur et le port
if [[ "$(hostname)" == *"api"* ]] || [ "$PORT" = "8001" ]; then
    SERVICE_URL="http://api:8001/api/healthcheck"
elif [[ "$(hostname)" == *"recommender"* ]] || [ "$PORT" = "8002" ]; then
    SERVICE_URL="http://recommender:8002/api/healthcheck"
else
    SERVICE_URL="http://localhost:$PORT/api/healthcheck"
fi

echo "Healthcheck: Testing $SERVICE_URL"
response=$(curl -f -s --max-time 10 --connect-timeout 5 $SERVICE_URL 2>&1)
curl_status=$?

if [ $curl_status -eq 0 ]; then
    echo "Healthcheck: Service is healthy"
    exit 0
else
    echo "Healthcheck: Service is unhealthy (curl exit code: $curl_status)"
    echo "Healthcheck: Response: $response"
    exit 1
fi
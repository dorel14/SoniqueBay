#!/bin/bash

# Vérification de l'endpoint healthcheck
# L'option -f fait échouer silencieusement curl en cas d'erreur HTTP
# L'option -s supprime la barre de progression

# Récupérer le port depuis les variables d'environnement
PORT=${HEALTHCHECK_PORT:-8000}

# Dans Docker, utiliser les aliases réseau définis dans docker-compose
# api:8001 et recommender:8002 selon le docker-compose-scan-optimized.yml

echo "Healthcheck: Container $(hostname) on port $PORT"

# Vérifier la résolution DNS du host
if [[ "$(hostname)" == *"api"* ]] || [ "$PORT" = "8001" ]; then
    SERVICE_HOST="api"
    SERVICE_URL="http://api:8001/api/healthcheck"
else
    SERVICE_HOST="localhost"
    SERVICE_URL="http://localhost:$PORT/api/healthcheck"
fi

echo "Healthcheck: Resolving $SERVICE_HOST..."
nslookup $SERVICE_HOST 2>/dev/null || echo "Healthcheck: DNS resolution failed for $SERVICE_HOST"

# Vérifier la connectivité réseau
echo "Healthcheck: Pinging $SERVICE_HOST..."
ping -c 1 -W 2 $SERVICE_HOST >/dev/null 2>&1 && echo "Healthcheck: Ping successful" || echo "Healthcheck: Ping failed"

# Vérifier si le port est ouvert
echo "Healthcheck: Checking if port $PORT is open on $SERVICE_HOST..."
nc -z -w5 $SERVICE_HOST $PORT >/dev/null 2>&1 && echo "Healthcheck: Port $PORT is open" || echo "Healthcheck: Port $PORT is closed"

echo "Healthcheck: Testing $SERVICE_URL"
response=$(curl -v -f -s --max-time 10 --connect-timeout 5 $SERVICE_URL 2>&1)
curl_status=$?

echo "Healthcheck: Curl status: $curl_status"
echo "Healthcheck: Full response: $response"

if [ $curl_status -eq 0 ]; then
    echo "Healthcheck: Service is healthy"
    exit 0
else
    echo "Healthcheck: Service is unhealthy (curl exit code: $curl_status)"
    echo "Healthcheck: Response: $response"
    exit 1
fi
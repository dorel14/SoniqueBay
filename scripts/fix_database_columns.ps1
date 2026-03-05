# Script PowerShell pour corriger les colonnes manquantes dans PostgreSQL
# Usage: .\scripts\fix_database_columns.ps1

Write-Host "=== Correction des colonnes manquantes dans track_mir_synthetic_tags ===" -ForegroundColor Green

# Copier le script SQL dans le conteneur
Write-Host "1. Copie du script SQL dans le conteneur PostgreSQL..." -ForegroundColor Yellow
docker cp scripts/fix_track_mir_synthetic_tags_columns.sql soniquebay-postgres:/tmp/fix_columns.sql

# Exécuter le script SQL
Write-Host "2. Exécution du script SQL..." -ForegroundColor Yellow
docker exec -i soniquebay-postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -f /tmp/fix_columns.sql

# Vérifier le résultat
Write-Host "3. Vérification des colonnes..." -ForegroundColor Yellow
docker exec -i soniquebay-postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'track_mir_synthetic_tags' 
AND column_name IN ('date_added', 'date_modified');
"

Write-Host "=== Correction terminée ===" -ForegroundColor Green
Write-Host "Redémarrez les conteneurs avec: docker-compose restart api-service celery-worker" -ForegroundColor Cyan

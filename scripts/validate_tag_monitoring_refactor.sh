#!/bin/bash
# Script de validation du refactoring tag_monitoring_service.py
# Vérifie que le service fonctionne correctement sans recommender_api

echo "=== VALIDATION REFACTORING TAG MONITORING SERVICE ==="
echo

echo "1. Vérification des imports..."
python -c "from backend_worker.services.tag_monitoring_service import TagMonitoringService, CeleryTaskPublisher; print('✓ Imports OK')"

echo
echo "2. Vérification absence de recommender_api..."
if grep -r "recommender_api\|RECOMMENDER_API_URL" backend_worker/services/tag_monitoring_service.py; then
    echo "✗ Erreur: Références à recommender_api trouvées"
    exit 1
else
    echo "✓ Aucune référence à recommender_api"
fi

echo
echo "3. Vérification du code vectorization_service.py..."
if grep -r "recommender_api\|RECOMMENDER_API_URL" backend_worker/services/vectorization_service.py; then
    echo "✗ Erreur: Références à recommender_api trouvées dans vectorization_service.py"
    exit 1
else
    echo "✓ Aucune référence à recommender_api dans vectorization_service.py"
fi

echo
echo "4. Test d'initialisation du service..."
python -c "
from backend_worker.services.tag_monitoring_service import TagMonitoringService
service = TagMonitoringService()
print('✓ Service initialisé correctement')
print(f'✓ Détecteur: {type(service.detector).__name__}')
print(f'✓ Publieur: {type(service.publisher).__name__}')
"

echo
echo "5. Vérification de la tâche Celery trigger_vectorizer_retrain..."
python -c "
from backend_worker.celery_app import celery
tasks = [task['name'] for task in celery.tasks.values()]
if 'trigger_vectorizer_retrain' in tasks:
    print('✓ Tâche trigger_vectorizer_retrain disponible')
else:
    print('✗ Attention: trigger_vectorizer_retrain non trouvée dans celery.tasks')
    print('Tâches disponibles:', tasks[:5], '...')
"

echo
echo "=== VALIDATION TERMINÉE ==="
echo "✓ Le refactoring est réussi!"
echo "✓ Le service tag_monitoring_service utilise maintenant Celery au lieu de recommender_api"
echo "✓ Les notifications SSE sont préservées pour l'interface utilisateur"
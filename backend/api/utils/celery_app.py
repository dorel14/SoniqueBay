from celery import Celery
import os
from backend.api.utils.celery_config_loader import load_celery_config_from_redis, _normalize_redis_url
from backend.api.utils.logging import logger

# Configuration Celery pour l'API (envoi de tâches uniquement)
# NOTE: L'API ne définit PAS de tâches, elle envoie seulement des tâches vers le worker
celery_app = Celery(
    'soniquebay_api',
    broker=_normalize_redis_url(os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')),
    backend=_normalize_redis_url(os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')),
    # PAS de 'include' - l'API n'importe pas les tâches du worker
)

# === CHARGER LA CONFIGURATION DEPUIS REDIS ===
# L'API lit la configuration depuis Redis au lieu d'importer directement du worker
try:
    logger.info("[CELERY_API] Chargement de la configuration Celery depuis Redis...")
    config = load_celery_config_from_redis()
    celery_app.conf.update(config)
    logger.info("[CELERY_API] Configuration Celery chargée avec succès depuis Redis")
except Exception as e:
    logger.error(f"[CELERY_API] Erreur lors du chargement de la configuration: {str(e)}")
    # En cas d'erreur, utiliser la configuration minimale pour éviter les crashes
    celery_app.conf.update({
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'result_accept_content': ['json'],
        'timezone': 'UTC',
        'enable_utc': True,
    })
from celery import Celery
import os
from backend.api.utils.logging import logger

# Configuration Celery pour l'API (envoi de tâches uniquement)
# NOTE: L'API ne définit PAS de tâches, elle envoie seulement des tâches vers le worker
# L'API utilise sa config locale, elle n'a pas besoin de lire depuis Redis

def _normalize_redis_url(url: str) -> str:
    """Normalise l'URL Redis pour éviter les erreurs de format."""
    if not url:
        return 'redis://redis:6379/0'
    
    # Corriger les URL malformées
    if not url.startswith('redis://'):
        url = 'redis://' + url
    
    # Corriger les doubles "redis://"
    if 'redis://redis://' in url:
        url = url.replace('redis://redis://', 'redis://', 1)
    
    # Ajouter le port et database si manquants
    if 'redis://' in url and '://' in url:
        scheme, rest = url.split('://', 1)
        if ':' not in rest and '/' not in rest:
            url = f'{scheme}://{rest}:6379/0'
        elif ':' in rest and '/' not in rest:
            url = f'{scheme}://{rest}/0'
    
    return url


celery_app = Celery(
    'soniquebay_api',
    broker=_normalize_redis_url(os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')),
    backend=_normalize_redis_url(os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')),
    # PAS de 'include' - l'API n'importe pas les tâches du worker
)

# L'API utilise sa config locale directement
# Elle n'a pas besoin de task_routes/task_queues du worker
celery_app.conf.update({
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'result_accept_content': ['json'],
    'timezone': 'UTC',
    'enable_utc': True,
})

logger.info("[CELERY_API] Configuration Celery configurée localement (pas de lecture Redis)")
logger.info(f"[CELERY_API] Broker: {os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')}")
logger.info("[CELERY_API] Note: Les task_routes et task_queues sont gérés par le worker, pas par l'API")

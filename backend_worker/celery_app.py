from celery import Celery
import os
from celery.signals import worker_ready
from helpers.logging import logger
from backend_worker.services.settings_service import SettingsService

# Communique via Redis
celery = Celery(
    'soniquebay',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=['tasks']  # nom du fichier où sont définies les tâches
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Paris',
    enable_utc=True,
)

@worker_ready.connect
def setup_settings_service(**kwargs):
    """Initialise le service de paramètres lorsque le worker est prêt."""
    try:
        settings_service = SettingsService()
        settings_service.initialize_default_settings()
        logger.info("Service de paramètres initialisé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du service de paramètres: {str(e)}")
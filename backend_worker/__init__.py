# Exposition de l'application Celery pour Docker
from .celery_app import celery as celery_app

# Pour compatibilité avec Celery CLI
app = celery_app
celery = celery_app

__all__ = ['celery_app', 'app', 'celery']

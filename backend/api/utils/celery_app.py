from celery import Celery
import os

celery_app = Celery(
    'soniquebay',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=['tasks']  # nom du fichier où sont définies les tâches
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=os.getenv('TZ', 'UTC'),
    enable_utc=True,
)
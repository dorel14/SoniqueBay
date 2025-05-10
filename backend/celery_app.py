# -*- coding: utf-8 -*-
from celery import Celery
from celery.signals import task_postrun
import platform
import os



# Création des dossiers nécessaires
for folder in ['./data/celery_in', './data/celery_out', './data/celery_processed']:
    os.makedirs(folder, exist_ok=True)

# Création de l'application Celery
celery = Celery(
    "soniquebay",
    broker='sqla+sqlite:///data/celery-broker.db',
    backend='db+sqlite:///data/celery-results.db',
    include=['backend.celery_tasks.tasks']  # Chemin complet du module
)

# Configuration de base
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
    task_track_started=True,  # Activer le suivi des tâches
    task_time_limit=3600,     # Limite de temps d'une heure
)

# Configuration Windows simplifiée
if platform.system() == 'Windows':
    celery.conf.update(
        worker_pool='solo',
        broker_connection_retry=True,
        broker_connection_max_retries=None,
    )

@task_postrun.connect
def task_postrun_handler(task_id=None, **kwargs):
    """Nettoie les ressources après chaque tâche"""
    if platform.system() == 'Windows':
        import gc
        gc.collect()

# S'assurer que le module est bien exposé
app = celery
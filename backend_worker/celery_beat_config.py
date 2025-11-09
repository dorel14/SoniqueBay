"""
Configuration Celery Beat - Tâches planifiées pour les queues différées
Gère le traitement périodique des tâches lourdes en arrière-plan.
"""
import os
from celery.schedules import crontab
from backend_worker.celery_app import celery

# Configuration des tâches planifiées
celery.conf.beat_schedule = {
    # ✅ Traitement des enrichissements (I/O modéré - toutes les 2 minutes)
    'process-deferred-enrichment': {
        'task': 'worker_deferred_enrichment.process_enrichment_batch',
        'schedule': crontab(minute='*/2'),  # Toutes les 2 minutes
        'args': (10,),  # Traiter 10 tâches par batch
        'options': {'queue': 'deferred'}  # ✅ CORRIGÉ: Queue 'deferred' comme dans celery_app.py
    },

    # ✅ Retry des tâches échouées (toutes les 10 minutes)
    'retry-failed-enrichments': {
        'task': 'worker_deferred_enrichment.retry_failed_enrichments',
        'schedule': crontab(minute='*/10'),  # Toutes les 10 minutes
        'args': (5,),  # Max 5 retries par cycle
        'options': {'queue': 'deferred'}  # ✅ CORRIGÉ: Queue 'deferred' comme dans celery_app.py
    },

    # === VECTORISATION MONITORING (NOUVEAU) ===
    
    # Monitoring des changements de tags (toutes les heures)
    'monitor-tag-changes': {
        'task': 'monitor_tag_changes',
        'schedule': crontab(minute=0),  # top de l'heure
        'options': {'queue': 'vectorization_monitoring'}  # ✅ CORRECT: Queue définie
    },

    # Vérification santé des modèles (toutes les 6 heures)
    'check-model-health': {
        'task': 'check_model_health',
        'schedule': crontab(minute=0, hour='*/6'),  # Toutes les 6h
        'options': {'queue': 'vectorization_monitoring'}  # ✅ CORRECT: Queue définie
    }
}

# Configuration Celery Beat
celery.conf.beat_schedule_filename = 'celerybeat-schedule.db'
celery.conf.beat_sync_every = 1  # Synchronise toutes les tâches

# Timezone pour les tâches planifiées
celery.conf.beat_timezone = os.getenv('TZ', 'UTC')
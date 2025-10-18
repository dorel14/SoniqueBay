"""
Configuration Celery Beat - Tâches planifiées pour les queues différées
Gère le traitement périodique des tâches lourdes en arrière-plan.
"""

from celery.schedules import crontab
from backend_worker.celery_app import celery

# Configuration des tâches planifiées
celery.conf.beat_schedule = {
    # Traitement des enrichissements (toutes les 2 minutes)
    'process-deferred-enrichment': {
        'task': 'worker_deferred_enrichment.process_enrichment_batch',
        'schedule': crontab(minute='*/2'),  # Toutes les 2 minutes
        'args': (10,),  # Traiter 10 tâches par batch
        'options': {'queue': 'worker_deferred_enrichment'}
    },

    # Traitement des covers (toutes les 5 minutes - APIs externes)
    'process-deferred-covers': {
        'task': 'worker_deferred_covers.process_covers_batch',
        'schedule': crontab(minute='*/5'),  # Toutes les 5 minutes
        'args': (5,),  # Traiter 5 tâches par batch (rate limited)
        'options': {'queue': 'worker_deferred_covers'}
    },

    # Traitement des vecteurs (toutes les 3 minutes - CPU intensif)
    'process-deferred-vectors': {
        'task': 'worker_deferred_vectors.process_vectors_batch',
        'schedule': crontab(minute='*/3'),  # Toutes les 3 minutes
        'args': (3,),  # Traiter 3 tâches par batch (CPU limité)
        'options': {'queue': 'worker_deferred_vectors'}
    },

    # Retry des tâches échouées (toutes les 10 minutes)
    'retry-failed-enrichments': {
        'task': 'worker_deferred_enrichment.retry_failed_enrichments',
        'schedule': crontab(minute='*/10'),  # Toutes les 10 minutes
        'args': (5,),  # Max 5 retries par cycle
        'options': {'queue': 'worker_deferred_enrichment'}
    },

    'retry-failed-covers': {
        'task': 'worker_deferred_covers.retry_failed_covers',
        'schedule': crontab(minute='*/15'),  # Toutes les 15 minutes (APIs lentes)
        'args': (3,),  # Max 3 retries par cycle
        'options': {'queue': 'worker_deferred_covers'}
    },

    'retry-failed-vectors': {
        'task': 'worker_deferred_vectors.retry_failed_vectors',
        'schedule': crontab(minute='*/10'),  # Toutes les 10 minutes
        'args': (2,),  # Max 2 retries par cycle (CPU)
        'options': {'queue': 'worker_deferred_vectors'}
    },

    # Nettoyage des tâches expirées (une fois par jour)
    'cleanup-expired-tasks': {
        'task': 'backend_worker.services.deferred_queue_service.cleanup_expired_tasks',
        'schedule': crontab(hour=2, minute=0),  # 2h du matin
        'args': (86400,),  # 24 heures
        'options': {'queue': 'worker_deferred_enrichment'}  # Queue arbitraire
    },

    # Rapports de santé quotidiens (une fois par jour)
    'daily-queue-health-report': {
        'task': 'backend_worker.tasks.health_monitoring.generate_daily_report',
        'schedule': crontab(hour=6, minute=0),  # 6h du matin
        'options': {'queue': 'worker_deferred_enrichment'}
    },

    # Maintenance des indexes vectoriels (hebdomadaire)
    'weekly-vector-index-maintenance': {
        'task': 'worker_vector.validate_vectors',
        'schedule': crontab(day_of_week=6, hour=3, minute=0),  # Samedi 3h
        'options': {'queue': 'worker_vector'}
    }
}

# Configuration Celery Beat
celery.conf.beat_schedule_filename = 'celerybeat-schedule.db'
celery.conf.beat_sync_every = 1  # Synchronise toutes les tâches

# Timezone pour les tâches planifiées
celery.conf.beat_timezone = 'Europe/Paris'
"""
Configuration Celery Beat - Tâches planifiées pour les queues différées
Gère le traitement périodique des tâches lourdes en arrière-plan.
"""
import os
from celery.schedules import crontab
from backend_worker.celery_app import celery

# Logs de diagnostic pour Celery Beat
from backend_worker.utils.logging import logger

logger.info(f"Celery Beat config loaded. Current working directory: {os.getcwd()}")
logger.info(f"CELERY_BEAT_DB env var: {os.getenv('CELERY_BEAT_DB')}")
beat_data_dir = './celery_beat_data'
logger.info(f"Beat data directory path: {beat_data_dir}")
logger.info(f"Beat data directory exists: {os.path.exists(beat_data_dir)}")
if os.path.exists(beat_data_dir):
    logger.info(f"Beat data directory contents: {os.listdir(beat_data_dir)}")
else:
    logger.warning("Beat data directory does not exist, attempting to create it")
    try:
        os.makedirs(beat_data_dir, exist_ok=True)
        logger.info("Beat data directory created successfully")
    except Exception as e:
        logger.error(f"Failed to create beat data directory: {e}")

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
    },

    # === MAINTENANCE TASKS (RESTAURÉES) ===

    # Nettoyage des tâches expirées (toutes les 4 heures)
    'cleanup-expired-tasks': {
        'task': 'backend_worker.tasks.maintenance_tasks.cleanup_expired_tasks_task',
        'schedule': crontab(minute=0, hour='*/4'),  # Toutes les 4 heures
        'args': (86400,),  # 24 heures en secondes
        'options': {'queue': 'maintenance'}
    },

    # Rapport de santé quotidien (tous les jours à minuit)
    'generate-daily-health-report': {
        'task': 'backend_worker.tasks.maintenance_tasks.generate_daily_health_report_task',
        'schedule': crontab(minute=0, hour=0),  # Tous les jours à minuit
        'options': {'queue': 'maintenance'}
    },

    # Rééquilibrage des queues (toutes les heures)
    'rebalance-queues': {
        'task': 'backend_worker.tasks.maintenance_tasks.rebalance_queues_task',
        'schedule': crontab(minute=30),  # Toutes les heures à H:30
        'options': {'queue': 'maintenance'}
    },

    # Archivage des anciens logs (tous les dimanches à 2h)
    'archive-old-logs': {
        'task': 'backend_worker.tasks.maintenance_tasks.archive_old_logs_task',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Dimanche 2h
        'args': (30,),  # 30 jours
        'options': {'queue': 'maintenance'}
    },

    # Validation intégrité système (toutes les 12 heures)
    'validate-system-integrity': {
        'task': 'backend_worker.tasks.maintenance_tasks.validate_system_integrity_task',
        'schedule': crontab(minute=0, hour='*/12'),  # Toutes les 12 heures
        'options': {'queue': 'maintenance'}
    }
}

# Configuration Celery Beat
celery.conf.beat_schedule_filename = './celery_beat_data/celerybeat-schedule.db'
celery.conf.beat_sync_every = 1  # Synchronise toutes les tâches

# Timezone pour les tâches planifiées
celery.conf.beat_timezone = os.getenv('TZ', 'UTC')
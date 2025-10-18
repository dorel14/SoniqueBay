from celery import Celery
from celery.signals import worker_init, task_prerun
import multiprocessing
from backend_worker.utils.logging import logger
import os

# Communique via Redis
celery = Celery(
    'soniquebay',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=[
        'backend_worker.background_tasks.tasks',  # Tâches principales (scan_music_task)
        'backend_worker.background_tasks.worker_scan',  # Worker scan
        'backend_worker.background_tasks.worker_extract',  # Worker extract
        'backend_worker.background_tasks.worker_insert_bulk',  # Worker insert bulk
        'backend_worker.background_tasks.worker_cover',  # Worker cover
        'backend_worker.background_tasks.worker_metadata',  # Worker metadata
        'backend_worker.background_tasks.worker_vector',  # Worker vector
        # Workers pour les queues différées
        'backend_worker.background_tasks.worker_deferred_enrichment',  # Deferred enrichment
        'backend_worker.background_tasks.worker_deferred_covers',  # Deferred covers
        'backend_worker.background_tasks.worker_deferred_vectors',  # Deferred vectors
    ]
)

# Configuration des queues dédiées pour chaque worker
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Paris',
    enable_utc=True,

    # Définition des queues dédiées
    task_queues={
        'worker_scan': {'exchange': 'worker_scan', 'routing_key': 'worker_scan'},
        'worker_extract': {'exchange': 'worker_extract', 'routing_key': 'worker_extract'},
        'worker_insert_bulk': {'exchange': 'worker_insert_bulk', 'routing_key': 'worker_insert_bulk'},
        'worker_cover': {'exchange': 'worker_cover', 'routing_key': 'worker_cover'},
        'worker_metadata': {'exchange': 'worker_metadata', 'routing_key': 'worker_metadata'},
        'worker_vector': {'exchange': 'worker_vector', 'routing_key': 'worker_vector'},
        # Queue différée consolidée (pour déploiement simplifié)
        'worker_deferred': {'exchange': 'worker_deferred', 'routing_key': 'worker_deferred'},
        'celery': {'exchange': 'celery', 'routing_key': 'celery'},  # Queue par défaut
    },

    # Routes des tâches vers les bonnes queues
    task_routes={
        # Worker Scan
        'worker_scan.discover_files': {'queue': 'worker_scan'},
        'scan_music_task': {'queue': 'worker_scan'},

        # Worker Extract
        'worker_extract.extract_file_metadata': {'queue': 'worker_extract'},
        'worker_extract.extract_batch_metadata': {'queue': 'worker_extract'},
        'worker_extract.validate_extraction_quality': {'queue': 'worker_extract'},

        # Worker Insert Bulk
        'worker_insert_bulk.insert_tracks_batch': {'queue': 'worker_insert_bulk'},
        'worker_insert_bulk.upsert_entities_batch': {'queue': 'worker_insert_bulk'},
        'worker_insert_bulk.process_scan_results': {'queue': 'worker_insert_bulk'},

        # Worker Cover
        'worker_cover.process_album_covers': {'queue': 'worker_cover'},
        'worker_cover.process_artist_images': {'queue': 'worker_cover'},
        'worker_cover.refresh_missing_covers': {'queue': 'worker_cover'},
        'worker_cover.process_track_covers_batch': {'queue': 'worker_cover'},

        # Worker Metadata
        'worker_metadata.enrich_tracks_batch': {'queue': 'worker_metadata'},
        'worker_metadata.analyze_audio_features': {'queue': 'worker_metadata'},
        'worker_metadata.enrich_artists_albums': {'queue': 'worker_metadata'},
        'worker_metadata.update_track_metadata': {'queue': 'worker_metadata'},
        'worker_metadata.bulk_update_genres_tags': {'queue': 'worker_metadata'},

        # Worker Vector
        'worker_vector.vectorize_tracks_batch': {'queue': 'worker_vector'},
        'worker_vector.vectorize_single_track_task': {'queue': 'worker_vector'},
        'worker_vector.update_tracks_vectors': {'queue': 'worker_vector'},
        'worker_vector.rebuild_index': {'queue': 'worker_vector'},
        'worker_vector.search_similar': {'queue': 'worker_vector'},
        'worker_vector.validate_vectors': {'queue': 'worker_vector'},

        # Worker Différé Unique (consolidé pour déploiement simplifié)
        'worker_deferred_enrichment.*': {'queue': 'worker_deferred'},
        'worker_deferred_covers.*': {'queue': 'worker_deferred'},
        'worker_deferred_vectors.*': {'queue': 'worker_deferred'},
    },

    # Paramètres de performance par queue (sera ajusté dynamiquement)
    worker_prefetch_multiplier=1,  # Valeur par défaut, ajustée dynamiquement

    # Timeouts spécifiques
    task_time_limit={
        'worker_scan.scan_directory': 3600,  # 1 heure pour scan complet
        'worker_vector.rebuild_index': 7200,  # 2 heures pour reconstruction
    },

    task_soft_time_limit={
        'worker_scan.scan_directory': 3300,  # 55 minutes
        'worker_vector.rebuild_index': 6600,  # 110 minutes
    },
)

# --- Prefetch multiplier dynamique par queue ---
PREFETCH_BY_QUEUE = {
    'worker_scan': 4,       # I/O bound
    'worker_extract': 2,    # CPU bound
    'worker_insert_bulk': 2, # DB bound
    'worker_cover': 1,      # API rate-limited
    'worker_metadata': 2,   # Mix I/O & CPU
    'worker_vector': 1,     # CPU heavy
    'worker_deferred': 2,   # Mixed background tasks
}

@worker_init.connect
def configure_worker(sender=None, **kwargs):
    """
    Appliqué une fois au démarrage du worker.
    Ajuste dynamiquement le prefetch_multiplier et la concurrency.
    """
    worker_name = sender.hostname
    app = sender.app

    # Cherche la queue liée au worker (par nom ou argument)
    queue_for_worker = None
    for queue_name in PREFETCH_BY_QUEUE:
        if queue_name in worker_name:
            queue_for_worker = queue_name
            break

    if queue_for_worker:
        # Applique le prefetch
        app.conf.worker_prefetch_multiplier = PREFETCH_BY_QUEUE[queue_for_worker]
        # Applique la concurrency
        cpu_count = multiprocessing.cpu_count()
        if queue_for_worker in ['worker_extract', 'worker_vector']:
            app.conf.worker_concurrency = max(1, cpu_count // 2)
        elif queue_for_worker in ['worker_insert_bulk', 'worker_metadata', 'worker_deferred']:
            app.conf.worker_concurrency = min(8, cpu_count)
        else:
            app.conf.worker_concurrency = 1  # worker_scan, worker_cover

        logger.info(f"[Celery] {worker_name} → Queue={queue_for_worker} | Prefetch={PREFETCH_BY_QUEUE[queue_for_worker]} | Concurrency={app.conf.worker_concurrency}")

@task_prerun.connect
def adjust_prefetch_per_task(task=None, **kwargs):
    """
    Ajuste dynamiquement selon la queue courante de la tâche.
    (utile si un worker écoute plusieurs queues)
    """
    request = getattr(task, 'request', None)
    if not request:
        return
    queue_name = request.delivery_info.get('routing_key')
    if queue_name and queue_name in PREFETCH_BY_QUEUE:
        task.app.conf.worker_prefetch_multiplier = PREFETCH_BY_QUEUE[queue_name]


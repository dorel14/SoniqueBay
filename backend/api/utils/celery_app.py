from celery import Celery
import os
from kombu import Queue

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

# Configuration unifiée Celery pour éviter les problèmes PIDBox
celery_app = Celery(
    'soniquebay',
    broker=_normalize_redis_url(os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')),
    backend=_normalize_redis_url(os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')),
    include=['backend_worker.celery_tasks']  # Référence correcte au module Worker
)

# Configuration compatible avec le worker backend_worker
celery_app.conf.update(
    # === CONFIGURATION DE BASE ===
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_accept_content=['json'],
    timezone=os.getenv('TZ', 'UTC'),
    enable_utc=True,
    
    # === CONFIGURATION ÉVÉNEMENTS CELERY (REQUIS POUR PIDBOX) ===
    worker_send_task_events=True,           # Activer envoi événements workers
    task_send_sent_event=True,              # Activer envoi événements tâches
    task_track_started=True,                # Tracking des tâches démarrées
    
    # === CONFIGURATION REDIS OPTIMISÉE ===
    redis_max_connections=20,               # Réduit pour éviter surcharge
    broker_pool_limit=5,                    # Pool plus petit pour stabilité
    result_backend_transport_options={
        'socket_timeout': 30,               # Timeout plus long pour stabilité
        'socket_connect_timeout': 20,       # Connexion plus tolérante
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'health_check_interval': 30,        # Health check plus espacé
    },
    
    # === CONFIGURATION ROUTING SIMPLE (COMPATIBLE) ===
    task_routes={
        'scan.discovery': {'queue': 'scan'},
        'metadata.extract_batch': {'queue': 'extract'},
        'batch.process_entities': {'queue': 'batch'},
        'insert.direct_batch': {'queue': 'insert'},
        'vectorization.calculate': {'queue': 'vectorization'},
        'covers.extract_embedded': {'queue': 'deferred'},
        'metadata.enrich_batch': {'queue': 'deferred'},
        'worker_deferred_enrichment.*': {'queue': 'deferred_enrichment'},
    },
    
    # === QUEUES SIMPLES (SANS EXCHANGE COMPLEXE) ===
    task_queues=[
        Queue('scan'),
        Queue('extract'), 
        Queue('batch'),
        Queue('insert'),
        Queue('covers'),
        Queue('maintenance'),
        Queue('vectorization_monitoring'),
        Queue('celery'),
        Queue('audio_analysis'),
        Queue('deferred_vectors'),
        Queue('deferred_covers'),
        Queue('deferred_enrichment'),
        Queue('deferred'),
    ],
    
    # === LIMITES DE PERFORMANCE ===
    task_acks_late=True,                    # Fiabilité maximale
    task_reject_on_worker_lost=True,        # Gestion des workers perdus
    worker_heartbeat=300,                   # Heartbeat étendu pour stabilité
    worker_clock_sync_interval=300,         # Sync étendu pour éviter timeouts
)
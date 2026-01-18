"""
Configuration Celery source unique de vérité - Worker uniquement.
Ce module est utilisé UNIQUEMENT par le worker pour définir la configuration.
Le backend API lit cette configuration depuis Redis, pas directement.
"""

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


def get_unified_queues():
    """
    Retourne la configuration unifiée des queues Celery avec routing_keys corrects.
    Utilisé uniquement par le worker - le backend lit depuis Redis.
    """
    return [
        # === QUEUES PRIORITAIRES ===
        Queue('scan', routing_key='scan'),
        Queue('extract', routing_key='extract'),
        Queue('batch', routing_key='batch'),
        Queue('insert', routing_key='insert'),
        
        # === QUEUES NORMALES ===
        Queue('covers', routing_key='covers'),
        Queue('maintenance', routing_key='maintenance'),
        Queue('vectorization_monitoring', routing_key='vectorization_monitoring'),
        Queue('celery', routing_key='celery'),
        Queue('audio_analysis', routing_key='audio_analysis'),
        
        # === QUEUES DIFFÉRÉES (PRIORITÉ BASSE) ===
        Queue('deferred_vectors', routing_key='deferred_vectors'),
        Queue('deferred_covers', routing_key='deferred_covers'),
        Queue('deferred_enrichment', routing_key='deferred_enrichment'),
        Queue('deferred', routing_key='deferred'),
    ]


def get_unified_task_routes():
    """
    Retourne la configuration unifiée du routing des tâches.
    Utilisé uniquement par le worker - le backend lit depuis Redis.
    """
    return {
        # === TÂCHES CELERY_CENTRALES ===
        'scan.discovery': {'queue': 'scan'},
        'metadata.extract_batch': {'queue': 'extract'},
        'batch.process_entities': {'queue': 'batch'},
        'insert.direct_batch': {'queue': 'insert'},
        'vectorization.calculate': {'queue': 'vectorization'},
        'covers.extract_embedded': {'queue': 'deferred'},
        'metadata.enrich_batch': {'queue': 'deferred'},
        'worker_deferred_enrichment.*': {'queue': 'deferred_enrichment'},
        
        # === MONITORING VECTORISATION ===
        'monitor_tag_changes': {'queue': 'vectorization_monitoring'},
        'trigger_vectorizer_retrain': {'queue': 'vectorization_monitoring'},
        'check_model_health': {'queue': 'vectorization_monitoring'},
        
        # === ANALYSE AUDIO AVEC LIBROSA ===
        'audio_analysis.extract_features': {'queue': 'audio_analysis'},
        'audio_analysis.batch_extract': {'queue': 'audio_analysis'},
    }


def get_unified_celery_config():
    """
    Retourne la configuration Celery complète unifiée.
    Utilisé uniquement par le worker - le backend lit depuis Redis.
    """
    return {
        # === CONFIGURATION DE BASE ===
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'result_accept_content': ['json'],
        'timezone': os.getenv('TZ', 'UTC'),
        'enable_utc': True,
        
        # === CONFIGURATION ÉVÉNEMENTS CELERY (REQUIS POUR PIDBOX) ===
        'worker_send_task_events': True,           # Activer envoi événements workers
        'task_send_sent_event': True,              # Activer envoi événements tâches
        'task_track_started': True,                # Tracking des tâches démarrées
        
        # === CONFIGURATION REDIS OPTIMISÉE ===
        'redis_max_connections': 20,               # Réduit pour éviter surcharge
        'broker_pool_limit': 5,                    # Pool plus petit pour stabilité
        'result_backend_transport_options': {
            'socket_timeout': 30,                  # Timeout plus long pour stabilité
            'socket_connect_timeout': 20,          # Connexion plus tolérante
            'retry_on_timeout': True,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'health_check_interval': 30,           # Health check plus espacé
        },
        
        # === CONFIGURATION ROUTING SYNCHRONISÉE ===
        'task_routes': get_unified_task_routes(),
        
        # === QUEUES SYNCHRONISÉES ===
        'task_queues': get_unified_queues(),
        
        # === LIMITES DE PERFORMANCE ===
        'task_acks_late': True,                    # Fiabilité maximale
        'task_reject_on_worker_lost': True,        # Gestion des workers perdus
        'worker_heartbeat': 300,                   # Heartbeat étendu pour stabilité
        'worker_clock_sync_interval': 300,         # Sync étendu pour éviter timeouts
    }
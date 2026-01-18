"""
Module de lecture de la configuration Celery depuis Redis.
Le backend API utilise ce module pour récupérer la configuration du worker.
"""

import json
import os
import time
import redis
from typing import Dict, Any, List, Optional
from kombu import Queue

from backend.api.utils.logging import logger


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


def get_redis_connection():
    """Crée une connexion Redis pour lire la configuration."""
    redis_url = _normalize_redis_url(os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'))
    
    try:
        # Extraire les paramètres de l'URL
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        
        return redis.Redis(
            host=parsed.hostname or 'redis',
            port=parsed.port or 6379,
            db=int(parsed.path[1:]) if parsed.path else 0,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
    except Exception as e:
        logger.error(f"[CELERY_CONFIG_LOADER] Erreur création connexion Redis: {e}")
        raise


def deserialize_queues_from_redis(queues_data: Dict[str, str]) -> List[Queue]:
    """
    Désérialise les queues depuis Redis en objets Kombu Queue.
    """
    queues = []
    for queue_name, queue_json in queues_data.items():
        try:
            queue_info = json.loads(queue_json)
            queue = Queue(
                name=queue_info['name'],
                routing_key=queue_info.get('routing_key', queue_info['name'])
            )
            queues.append(queue)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[CELERY_CONFIG_LOADER] Erreur désérialisation queue {queue_name}: {e}")
            continue
    
    return queues


def deserialize_routes_from_redis(routes_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Désérialise les routes des tâches depuis Redis.
    """
    routes = {}
    for task_pattern, route_json in routes_data.items():
        try:
            route_config = json.loads(route_json)
            routes[task_pattern] = route_config
        except json.JSONDecodeError as e:
            logger.warning(f"[CELERY_CONFIG_LOADER] Erreur désérialisation route {task_pattern}: {e}")
            continue
    
    return routes


def deserialize_base_config_from_redis(base_config_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Désérialise la configuration de base depuis Redis.
    """
    config = {}
    for key, value_json in base_config_data.items():
        try:
            value = json.loads(value_json)
            config[key] = value
        except json.JSONDecodeError as e:
            logger.warning(f"[CELERY_CONFIG_LOADER] Erreur désérialisation config {key}: {e}")
            continue
    
    return config


def get_fallback_config() -> Dict[str, Any]:
    """
    Configuration de fallback en cas d'indisponibilité de Redis.
    Utilisée seulement pour éviter que l'API ne plante au démarrage.
    """
    logger.warning("[CELERY_CONFIG_LOADER] Utilisation de la configuration de fallback")
    
    return {
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'result_accept_content': ['json'],
        'timezone': 'UTC',
        'enable_utc': True,
        'worker_send_task_events': True,
        'task_send_sent_event': True,
        'task_track_started': True,
        'task_acks_late': True,
        'task_reject_on_worker_lost': True,
        'worker_heartbeat': 300,
        'worker_clock_sync_interval': 300,
        'redis_max_connections': 20,
        'broker_pool_limit': 5,
        'task_routes': {
            'scan.discovery': {'queue': 'scan'},
            'metadata.extract_batch': {'queue': 'extract'},
            'batch.process_entities': {'queue': 'batch'},
            'insert.direct_batch': {'queue': 'insert'},
            'vectorization.calculate': {'queue': 'vectorization'},
            'covers.extract_embedded': {'queue': 'deferred'},
            'metadata.enrich_batch': {'queue': 'deferred'},
            'worker_deferred_enrichment.*': {'queue': 'deferred_enrichment'},
            'monitor_tag_changes': {'queue': 'vectorization_monitoring'},
            'trigger_vectorizer_retrain': {'queue': 'vectorization_monitoring'},
            'check_model_health': {'queue': 'vectorization_monitoring'},
            'audio_analysis.extract_features': {'queue': 'audio_analysis'},
            'audio_analysis.batch_extract': {'queue': 'audio_analysis'},
        },
        'task_queues': [
            Queue('scan', routing_key='scan'),
            Queue('extract', routing_key='extract'),
            Queue('batch', routing_key='batch'),
            Queue('insert', routing_key='insert'),
            Queue('covers', routing_key='covers'),
            Queue('maintenance', routing_key='maintenance'),
            Queue('vectorization_monitoring', routing_key='vectorization_monitoring'),
            Queue('celery', routing_key='celery'),
            Queue('audio_analysis', routing_key='audio_analysis'),
            Queue('deferred_vectors', routing_key='deferred_vectors'),
            Queue('deferred_covers', routing_key='deferred_covers'),
            Queue('deferred_enrichment', routing_key='deferred_enrichment'),
            Queue('deferred', routing_key='deferred'),
        ],
        'result_backend_transport_options': {
            'socket_timeout': 30,
            'socket_connect_timeout': 20,
            'retry_on_timeout': True,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'health_check_interval': 30,
        }
    }


def load_celery_config_from_redis(max_retries: int = 5, retry_delay: float = 2.0) -> Dict[str, Any]:
    """
    Charge la configuration Celery depuis Redis avec retry.
    
    Args:
        max_retries: Nombre maximum de tentatives
        retry_delay: Délai entre les tentatives en secondes
    
    Returns:
        Configuration Celery complète
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"[CELERY_CONFIG_LOADER] Tentative de chargement (attempt {attempt + 1}/{max_retries})")
            
            # Créer la connexion Redis
            redis_client = get_redis_connection()
            
            # Vérifier la connexion
            redis_client.ping()
            logger.info("[CELERY_CONFIG_LOADER] Connexion Redis établie")
            
            # Vérifier si la configuration existe
            version = redis_client.get('celery_config:version')
            if not version:
                logger.warning("[CELERY_CONFIG_LOADER] Aucune configuration trouvée dans Redis")
                if attempt == max_retries - 1:
                    # Dernière tentative - utiliser le fallback
                    return get_fallback_config()
                else:
                    logger.info(f"[CELERY_CONFIG_LOADER] Attente {retry_delay}s avant nouvelle tentative...")
                    time.sleep(retry_delay)
                    continue
            
            logger.info(f"[CELERY_CONFIG_LOADER] Version trouvée: {version}")
            
            # Charger les queues
            queues_data = redis_client.hgetall('celery_config:queues')
            if not queues_data:
                logger.warning("[CELERY_CONFIG_LOADER] Aucune queue trouvée dans Redis")
                if attempt == max_retries - 1:
                    return get_fallback_config()
                else:
                    time.sleep(retry_delay)
                    continue
            
            logger.info(f"[CELERY_CONFIG_LOADER] {len(queues_data)} queues chargées")
            
            # Charger les routes
            routes_data = redis_client.hgetall('celery_config:routes')
            if not routes_data:
                logger.warning("[CELERY_CONFIG_LOADER] Aucune route trouvée dans Redis")
                if attempt == max_retries - 1:
                    return get_fallback_config()
                else:
                    time.sleep(retry_delay)
                    continue
            
            logger.info(f"[CELERY_CONFIG_LOADER] {len(routes_data)} routes chargées")
            
            # Charger la config de base
            base_config_data = redis_client.hgetall('celery_config:base')
            if not base_config_data:
                logger.warning("[CELERY_CONFIG_LOADER] Aucune config de base trouvée dans Redis")
                if attempt == max_retries - 1:
                    return get_fallback_config()
                else:
                    time.sleep(retry_delay)
                    continue
            
            # Désérialiser tous les éléments
            queues = deserialize_queues_from_redis(queues_data)
            routes = deserialize_routes_from_redis(routes_data)
            base_config = deserialize_base_config_from_redis(base_config_data)
            
            # Assembler la configuration finale
            final_config = base_config.copy()
            final_config['task_routes'] = routes
            final_config['task_queues'] = queues
            
            logger.info("[CELERY_CONFIG_LOADER] Configuration chargée avec succès depuis Redis")
            logger.info(f"[CELERY_CONFIG_LOADER] {len(queues)} queues, {len(routes)} routes, {len(base_config)} paramètres de base")
            
            return final_config
            
        except Exception as e:
            last_error = e
            logger.error(f"[CELERY_CONFIG_LOADER] Erreur lors du chargement (attempt {attempt + 1}): {str(e)}")
            
            if attempt == max_retries - 1:
                logger.error(f"[CELERY_CONFIG_LOADER] Toutes les tentatives ont échoué: {str(last_error)}")
                logger.info("[CELERY_CONFIG_LOADER] Utilisation de la configuration de fallback")
                return get_fallback_config()
            else:
                logger.info(f"[CELERY_CONFIG_LOADER] Attente {retry_delay}s avant nouvelle tentative...")
                time.sleep(retry_delay)
    
    # Ne devrait jamais arriver ici, mais par sécurité
    logger.error("[CELERY_CONFIG_LOADER] Échec complet du chargement - utilisation du fallback")
    return get_fallback_config()


def wait_for_celery_config(timeout: int = 30) -> bool:
    """
    Attend que la configuration Celery soit disponible dans Redis.
    
    Args:
        timeout: Timeout en secondes
    
    Returns:
        True si la config est disponible, False sinon
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            redis_client = get_redis_connection()
            redis_client.ping()
            
            version = redis_client.get('celery_config:version')
            if version:
                logger.info(f"[CELERY_CONFIG_LOADER] Configuration Celery disponible (version: {version})")
                return True
                
        except Exception as e:
            logger.warning(f"[CELERY_CONFIG_LOADER] Erreur lors de la vérification: {str(e)}")
        
        time.sleep(1)
    
    logger.warning(f"[CELERY_CONFIG_LOADER] Timeout: configuration Celery non disponible après {timeout}s")
    return False
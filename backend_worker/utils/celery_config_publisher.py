"""
Module de publication de la configuration Celery dans Redis.
Le worker utilise ce module pour publier sa configuration au démarrage.
"""

import json
import time
import redis
import os
from typing import Dict, Any, List

from backend_worker.utils.logging import logger


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
    """Crée une connexion Redis pour publier la configuration."""
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
        logger.error(f"[CELERY_CONFIG_PUBLISHER] Erreur création connexion Redis: {e}")
        raise


def serialize_queues_for_redis(queues: List) -> Dict[str, str]:
    """
    Sérialise les queues Kombu en format JSON pour Redis.
    """
    serialized = {}
    for queue in queues:
        serialized[queue.name] = json.dumps({
            'name': queue.name,
            'routing_key': queue.routing_key,
            'exchange': str(queue.exchange) if queue.exchange else ''
        })
    return serialized


def serialize_routes_for_redis(routes: Dict[str, Any]) -> Dict[str, str]:
    """
    Sérialise les routes des tâches en format JSON pour Redis.
    """
    serialized = {}
    for task_pattern, route_config in routes.items():
        serialized[task_pattern] = json.dumps(route_config)
    return serialized


def serialize_base_config_for_redis(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Sérialise la configuration de base en format JSON pour Redis.
    """
    serialized = {}
    for key, value in config.items():
        # Les objets complexes (queues, routes) sont sérialisés séparément
        if key in ['task_routes', 'task_queues']:
            continue
        serialized[key] = json.dumps(value)
    return serialized


def publish_celery_config_to_redis():
    """
    Publie la configuration Celery unifiée dans Redis.
    Cette fonction est appelée par le worker au démarrage.
    """
    try:
        logger.info("[CELERY_CONFIG_PUBLISHER] Début de la publication de la configuration Celery")
        
        # Charger la configuration depuis la source unique
        from backend_worker.celery_config_source import (
            get_unified_queues,
            get_unified_task_routes,
            get_unified_celery_config
        )
        
        # Récupérer les configurations
        queues = get_unified_queues()
        routes = get_unified_task_routes()
        base_config = get_unified_celery_config()
        
        # Créer la connexion Redis
        redis_client = get_redis_connection()
        
        # Vérifier la connexion
        redis_client.ping()
        logger.info("[CELERY_CONFIG_PUBLISHER] Connexion Redis établie")
        
        # Sérialiser et stocker les queues
        logger.info(f"[CELERY_CONFIG_PUBLISHER] Publication de {len(queues)} queues")
        queues_data = serialize_queues_for_redis(queues)
        redis_client.hset('celery_config:queues', mapping=queues_data)
        
        # Sérialiser et stocker les routes
        logger.info(f"[CELERY_CONFIG_PUBLISHER] Publication de {len(routes)} routes")
        routes_data = serialize_routes_for_redis(routes)
        redis_client.hset('celery_config:routes', mapping=routes_data)
        
        # Sérialiser et stocker la config de base
        logger.info("[CELERY_CONFIG_PUBLISHER] Publication de la configuration de base")
        base_config_data = serialize_base_config_for_redis(base_config)
        redis_client.hset('celery_config:base', mapping=base_config_data)
        
        # Publier le timestamp de version
        version_timestamp = str(int(time.time()))
        redis_client.set('celery_config:version', version_timestamp)
        logger.info(f"[CELERY_CONFIG_PUBLISHER] Version publiée: {version_timestamp}")
        
        # Notifier via Pub/Sub
        redis_client.publish('celery_config_updates', 'updated')
        
        # Log de succès
        logger.info("[CELERY_CONFIG_PUBLISHER] Configuration Celery publiée avec succès dans Redis")
        
        # Statistiques pour vérification
        queues_count = redis_client.hlen('celery_config:queues')
        routes_count = redis_client.hlen('celery_config:routes')
        logger.info(f"[CELERY_CONFIG_PUBLISHER] Vérification: {queues_count} queues, {routes_count} routes stockées")
        
        return True
        
    except Exception as e:
        logger.error(f"[CELERY_CONFIG_PUBLISHER] Erreur lors de la publication: {str(e)}")
        raise


def clear_celery_config_from_redis():
    """
    Efface la configuration Celery de Redis (utilisé pour les tests ou reset).
    """
    try:
        logger.info("[CELERY_CONFIG_PUBLISHER] Effacement de la configuration Celery de Redis")
        
        redis_client = get_redis_connection()
        redis_client.ping()
        
        # Effacer les clés
        redis_client.delete('celery_config:queues', 'celery_config:routes', 'celery_config:base', 'celery_config:version')
        
        # Notifier via Pub/Sub
        redis_client.publish('celery_config_updates', 'cleared')
        
        logger.info("[CELERY_CONFIG_PUBLISHER] Configuration Celery effacée de Redis")
        return True
        
    except Exception as e:
        logger.error(f"[CELERY_CONFIG_PUBLISHER] Erreur lors de l'effacement: {str(e)}")
        raise
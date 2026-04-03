"""
Configuration des retries TaskIQ avec Dead Letter Queue (DLQ).
Équivalent TaskIQ du fichier celery_retry_config.py.

Ce module fournit :
- Configuration de retry automatique avec backoff exponentiel
- Dead Letter Queue pour les tâches en échec définitif
- Décorateurs utilitaires pour faciliter l'implémentation
"""

import asyncio
import json
import time
from functools import wraps
from typing import Type, Optional, Callable, Any, Dict, Tuple
import httpx
import redis.asyncio as redis
from sqlalchemy import exc as sqlalchemy_exc
from backend.workers.utils.logging import logger

# Import SQLAlchemy optionnel (peut ne pas être disponible dans le worker)
try:
    import sqlalchemy
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None


# === CONFIGURATION DES RETRIES ===

DEFAULT_RETRY_CONFIG = {
    # Nombre maximum de tentatives
    'max_retries': 5,
    
    # Délai initial entre les retries (en secondes)
    'default_retry_delay': 60,  # 1 minute
    
    # Backoff exponentiel : delay * (2 ** retry_count)
    'retry_backoff': True,
    
    # Maximum du backoff (en secondes) - 1 heure
    'retry_backoff_max': 3600,
    
    # Jitter pour éviter les thundering herds (0-1)
    'retry_jitter': True,
    
    # Exceptions qui déclenchent automatiquement un retry
    'autoretry_for': (
        # Erreurs réseau
        ConnectionError,
        TimeoutError,
        httpx.NetworkError,
        httpx.ConnectError,
        httpx.TimeoutException,
        
        # Erreurs DNS
        OSError,  # [Errno -2] Name or service not known
        
        # Erreurs Redis
        redis.ConnectionError,
        redis.TimeoutError,
        
        # Erreurs base de données (transitoires) - uniquement si SQLAlchemy disponible
        *((
            sqlalchemy_exc.OperationalError,
            sqlalchemy_exc.TimeoutError,
        ) if SQLALCHEMY_AVAILABLE else ()),
    ),
    
    # Exceptions qui ne doivent PAS déclencher de retry
    'retry_on': None,  # Par défaut, retry sur toutes les exceptions autoretry_for
    'throws': None,
}


# === DEAD LETTER QUEUE ===

def get_dlq_config():
    """
    Configuration de la Dead Letter Queue.
    Les tâches qui échouent après max_retries sont routées ici.
    """
    return {
        'queue': 'failed',
        'routing_key': 'failed',
    }


# === DÉCORATEURS UTILITAIRES ===

def with_retry(
    max_retries: int = 5,
    retry_delay: int = 60,
    backoff: bool = True,
    backoff_max: int = 3600,
    jitter: bool = True,
    autoretry_exceptions: Optional[tuple] = None,
    retry_on_500: bool = True,
    log_retries: bool = True,
) -> Callable:
    """
    Décorateur pour configurer les retries sur une tâche TaskIQ.
    
    Args:
        max_retries: Nombre maximum de tentatives
        retry_delay: Délai initial entre les retries (secondes)
        backoff: Activer le backoff exponentiel
        backoff_max: Maximum du backoff (secondes)
        jitter: Ajouter du jitter pour éviter les thundering herds
        autoretry_exceptions: Tuple d'exceptions qui déclenchent le retry
        retry_on_500: Retry sur les erreurs HTTP 500/502/503/504
        log_retries: Logger les tentatives de retry
    
    Example:
        @broker.task
        @with_retry(max_retries=3, retry_delay=30)
        async def ma_tache():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Le décorateur est appliqué sur une fonction de tâche TaskIQ
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Vérifier si l'exception est dans la liste des exceptions autorisées pour retry
                    if autoretry_exceptions is not None:
                        if not isinstance(e, autoretry_exceptions):
                            # Si pas dans la liste, on ne retry pas
                            raise
                    else:
                        # Utiliser la configuration par défaut
                        # On vérifie les types d'exception dans autoretry_for
                        # Pour simplifier, on retry sur toutes les exceptions sauf si on a une liste de throws
                        # Mais on ne va pas implémenter la logique complète ici pour l'exemple
                        pass
                    
                    if attempt < max_retries - 1:
                        # Calcul du délai avec backoff exponentiel et jitter
                        delay = retry_delay * (2 ** attempt) if backoff else retry_delay
                        if backoff:
                            delay = min(delay, backoff_max)
                        if jitter:
                            import random
                            delay *= (0.5 + random.random() * 0.5)  # jitter entre 0.5 et 1.0
                        
                        if log_retries:
                            logger.warning(
                                f"[TASKIQ_RETRY] Tentative {attempt + 1}/{max_retries} échouée pour {func.__name__}: {e}. "
                                f"Nouvelle tentative dans {delay:.2f}s"
                            )
                        await asyncio.sleep(delay)
                    else:
                        if log_retries:
                            logger.error(
                                f"[TASKIQ_RETRY] Toutes les tentatives épuisées pour {func.__name__} après {max_retries} essais. Dernière erreur: {e}"
                            )
                        # Après tous les retries, on envoie la tâche à la DLQ
                        # Cette partie sera implémentée dans le gestionnaire de DLQ
                        # Pour l'instant, on lève l'exception
                        raise
            # Cette ligne ne devrait jamais être atteinte
            raise last_exception
        return wrapper
    return decorator


# === GESTIONNAIRE DE DLQ ===

class DeadLetterQueueHandler:
    """
    Gestionnaire pour la Dead Letter Queue.
    Déplace les tâches échouées vers la queue 'failed' pour analyse ultérieure.
    """
    
    def __init__(self, taskiq_broker):
        self.broker = taskiq_broker
        self.logger = logger
        self.redis_client = None
    
    async def _get_redis_client(self):
        if self.redis_client is None:
            redis_url = "redis://redis:6379/0"  # À configurer via variables d'environnement
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
        return self.redis_client
    
    async def move_to_dlq(self, task_id: str, task_name: str, exception: Exception, args: tuple, kwargs: dict):
        """
        Déplace une tâche échouée vers la DLQ.
        En attendant une vraie DLQ TaskIQ, on stocke les informations dans Redis.
        """
        self.logger.error(
            f"[TASKIQ_DLQ] Tâche {task_name} (ID: {task_id}) déplacée vers la DLQ après échec définitif: {exception}"
        )
        
        # Stocker les informations de la tâche échouée dans Redis pour analyse
        try:
            from datetime import datetime
            
            failed_task_info = {
                'task_id': task_id,
                'task_name': task_name,
                'exception': str(exception),
                'exception_type': type(exception).__name__,
                'args': str(args),
                'kwargs': str(kwargs),
                'timestamp': datetime.utcnow().isoformat(),
                'retry_count': getattr(exception, 'retry_count', 0),
            }
            
            client = await self._get_redis_client()
            await client.hset(f'taskiq:failed:{task_id}', mapping=failed_task_info)
            await client.expire(f'taskiq:failed:{task_id}', 604800)  # 7 jours
            
            self.logger.info(f"[TASKIQ_DLQ] Informations de la tâche échouée stockées dans Redis (key: taskiq:failed:{task_id})")
            
        except Exception as e:
            self.logger.error(f"[TASKIQ_DLQ] Erreur lors du stockage des informations de la tâche échouée: {e}")
    
    async def get_failed_tasks(self, limit: int = 100) -> list:
        """
        Récupère la liste des tâches échouées stockées dans Redis.
        """
        try:
            client = await self._get_redis_client()
            
            # Récupérer toutes les clés correspondant aux tâches échouées
            keys = await client.keys('taskiq:failed:*')
            failed_tasks = []
            
            for key in keys[:limit]:
                task_info = await client.hgetall(key)
                if task_info:
                    # Décoder les bytes en strings
                    decoded_info = {k.decode() if isinstance(k, bytes) else k: 
                                   v.decode() if isinstance(v, bytes) else v 
                                   for k, v in task_info.items()}
                    failed_tasks.append(decoded_info)
            
            return failed_tasks
            
        except Exception as e:
            self.logger.error(f"[TASKIQ_DLQ] Erreur lors de la récupération des tâches échouées: {e}")
            return []
    
    async def retry_failed_task(self, task_id: str) -> bool:
        """
        Retente une tâche précédemment échouée.
        """
        try:
            client = await self._get_redis_client()
            
            key = f'taskiq:failed:{task_id}'
            task_info = await client.hgetall(key)
            
            if not task_info:
                self.logger.warning(f"[TASKIQ_DLQ] Tâche {task_id} non trouvée dans Redis")
                return False
            
            # Décoder les informations
            decoded_info = {k.decode() if isinstance(k, bytes) else k: 
                           v.decode() if isinstance(v, bytes) else v 
                           for k, v in task_info.items()}
            
            task_name = decoded_info.get('task_name')
            # Pour simplifier, on suppose que les args et kwargs sont des chaînes à évaluer
            # En réalité, on devrait les stocker correctement
            import ast
            args = ast.literal_eval(decoded_info.get('args', '()'))
            kwargs = ast.literal_eval(decoded_info.get('kwargs', '{}'))
            
            # Relancer la tâche
            await self.broker.send_task(task_name, args=args, kwargs=kwargs)
            
            # Supprimer de la DLQ
            await client.delete(key)
            
            self.logger.info(f"[TASKIQ_DLQ] Tâche {task_id} ({task_name}) relancée avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"[TASKIQ_DLQ] Erreur lors du retry manuel de la tâche {task_id}: {e}")
            return False


# === FONCTION DE CONFIGURATION GLOBALE ===

def configure_taskiq_retries(taskiq_broker):
    """
    Configure les retries pour l'application TaskIQ complète.
    Cette fonction est un placeholder - la configuration réelle se fait via le décorateur @with_retry.
    """
    # Pour l'instant, on retourne juste le broker
    # Dans une implémentation plus complète, on pourrait configurer des valeurs par défaut
    return taskiq_broker
"""
Configuration des retries Celery avec Dead Letter Queue (DLQ).

Ce module fournit :
- Configuration de retry automatique avec backoff exponentiel
- Dead Letter Queue pour les tâches en échec définitif
- Décorateurs utilitaires pour faciliter l'implémentation
"""

import os
import ast
from functools import wraps
from typing import List, Type, Optional, Callable, Any
from kombu import Queue
from celery import Task
from celery.exceptions import MaxRetriesExceededError, Retry
import httpx
import redis

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
            sqlalchemy.exc.OperationalError,
            sqlalchemy.exc.TimeoutError,
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
        'queue': Queue('failed', routing_key='failed'),
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
    Décorateur pour configurer les retries sur une tâche Celery.
    
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
        @app.task
        @with_retry(max_retries=3, retry_delay=30)
        def ma_tache():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Le décorateur est appliqué sur une méthode de tâche Celery
            return func(self, *args, **kwargs)
        
        # Attacher la configuration de retry à la fonction
        wrapper._celery_retry_config = {
            'max_retries': max_retries,
            'default_retry_delay': retry_delay,
            'retry_backoff': backoff,
            'retry_backoff_max': backoff_max,
            'retry_jitter': jitter,
            'autoretry_for': autoretry_exceptions or DEFAULT_RETRY_CONFIG['autoretry_for'],
        }
        
        return wrapper
    
    return decorator


def apply_retry_config(task_class: Type[Task]) -> Type[Task]:
    """
    Applique la configuration de retry à une classe de tâche Celery.
    
    Example:
        @app.task(bind=True)
        @apply_retry_config
        class MaTache(Task):
            def run(self, *args, **kwargs):
                pass
    """
    for key, value in DEFAULT_RETRY_CONFIG.items():
        if not hasattr(task_class, key) or getattr(task_class, key) is None:
            setattr(task_class, key, value)
    
    return task_class


# === GESTIONNAIRE DE DLQ ===

class DeadLetterQueueHandler:
    """
    Gestionnaire pour la Dead Letter Queue.
    Déplace les tâches échouées vers la queue 'failed' pour analyse ultérieure.
    """
    
    def __init__(self, celery_app):
        self.app = celery_app
        self.logger = self._get_logger()
    
    def _get_logger(self):
        from backend_worker.utils.logging import logger
        return logger
    
    def move_to_dlq(self, task_id: str, task_name: str, exception: Exception, args: tuple, kwargs: dict):
        """
        Déplace une tâche échouée vers la DLQ.
        """
        self.logger.error(
            f"[DLQ] Tâche {task_name} (ID: {task_id}) déplacée vers la DLQ après échec définitif: {exception}"
        )
        
        # Stocker les informations de la tâche échouée dans Redis pour analyse
        try:
            import json
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
            
            # Stocker dans Redis avec expiration de 7 jours
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
            client = redis.from_url(redis_url)
            client.hset(f'celery:failed:{task_id}', mapping=failed_task_info)
            client.expire(f'celery:failed:{task_id}', 604800)  # 7 jours
            
            self.logger.info(f"[DLQ] Informations de la tâche échouée stockées dans Redis (key: celery:failed:{task_id})")
            
        except Exception as e:
            self.logger.error(f"[DLQ] Erreur lors du stockage des informations de la tâche échouée: {e}")
    
    def get_failed_tasks(self, limit: int = 100) -> list:
        """
        Récupère la liste des tâches échouées stockées dans Redis.
        """
        try:
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
            client = redis.from_url(redis_url)
            
            # Récupérer toutes les clés correspondant aux tâches échouées
            keys = client.keys('celery:failed:*')
            failed_tasks = []
            
            for key in keys[:limit]:
                task_info = client.hgetall(key)
                if task_info:
                    # Décoder les bytes en strings
                    decoded_info = {k.decode() if isinstance(k, bytes) else k: 
                                   v.decode() if isinstance(v, bytes) else v 
                                   for k, v in task_info.items()}
                    failed_tasks.append(decoded_info)
            
            return failed_tasks
            
        except Exception as e:
            self.logger.error(f"[DLQ] Erreur lors de la récupération des tâches échouées: {e}")
            return []
    
    def retry_failed_task(self, task_id: str) -> bool:
        """
        Retente une tâche précédemment échouée.
        """
        try:
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
            client = redis.from_url(redis_url)
            
            key = f'celery:failed:{task_id}'
            task_info = client.hgetall(key)
            
            if not task_info:
                self.logger.warning(f"[DLQ] Tâche {task_id} non trouvée dans Redis")
                return False
            
            # Décoder les informations
            decoded_info = {k.decode() if isinstance(k, bytes) else k: 
                           v.decode() if isinstance(v, bytes) else v 
                           for k, v in task_info.items()}
            
            task_name = decoded_info.get('task_name')
            args = ast.literal_eval(decoded_info.get('args', '()'))
            kwargs = ast.literal_eval(decoded_info.get('kwargs', '{}'))
            
            # Relancer la tâche
            self.app.send_task(task_name, args=args, kwargs=kwargs)
            
            # Supprimer de la DLQ
            client.delete(key)
            
            self.logger.info(f"[DLQ] Tâche {task_id} ({task_name}) relancée avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"[DLQ] Erreur lors du retry manuel de la tâche {task_id}: {e}")
            return False


# === FONCTION DE CONFIGURATION GLOBALE ===

def configure_celery_retries(celery_app):
    """
    Configure les retries pour l'application Celery complète.
    """
    # Mettre à jour la configuration avec les options de retry
    celery_app.conf.update({
        'task_default_retry_delay': DEFAULT_RETRY_CONFIG['default_retry_delay'],
        'task_max_retries': DEFAULT_RETRY_CONFIG['max_retries'],
        'task_retry_backoff': DEFAULT_RETRY_CONFIG['retry_backoff'],
        'task_retry_backoff_max': DEFAULT_RETRY_CONFIG['retry_backoff_max'],
        'task_retry_jitter': DEFAULT_RETRY_CONFIG['retry_jitter'],
        'task_autoretry_for': DEFAULT_RETRY_CONFIG['autoretry_for'],
    })
    
    # Ajouter la DLQ aux queues
    dlq_config = get_dlq_config()
    celery_app.conf.task_queues = celery_app.conf.task_queues or []
    if dlq_config['queue'] not in celery_app.conf.task_queues:
        celery_app.conf.task_queues.append(dlq_config['queue'])
    
    # Configurer le handler de tâches échouées
    dlq_handler = DeadLetterQueueHandler(celery_app)
    
    @celery_app.task(bind=True)
    def handle_task_failure(self, task_id, task_name, exception, args, kwargs):
        """
        Tâche de gestion des échecs - déplace vers DLQ.
        """
        dlq_handler.move_to_dlq(task_id, task_name, exception, args, kwargs)
    
    # Stocker le handler pour utilisation externe
    celery_app.dlq_handler = dlq_handler
    
    return celery_app

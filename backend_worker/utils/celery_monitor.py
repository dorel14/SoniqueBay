"""
Utilitaire de monitoring des arguments Celery pour mesurer et optimiser les limites.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict

import redis

from backend_worker.utils.logging import logger

# Métriques globales pour le monitoring
CELERY_SIZE_METRICS = {
    'args_max_size': 0,
    'kwargs_max_size': 0,
    'args_avg_size': 0,
    'kwargs_avg_size': 0,
    'total_measurements': 0,
    'args_size_samples': [],
    'kwargs_size_samples': [],
    'truncated_count': 0,
    'max_task_name': '',
    'recommended_max': 0,
    'last_updated': None
}

# Configuration Redis pour le partage inter-conteneurs
def get_redis_client():
    """Retourne un client Redis configuré."""
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        # Nettoyer l'URL si elle a des doubles "redis://"
        if redis_url.startswith('redis://redis://'):
            redis_url = redis_url.replace('redis://redis://', 'redis://', 1)
        
        # Test de connexion avant de créer le client
        logger.debug(f"[CELERY MONITOR] Test connexion Redis: {redis_url}")
        client = redis.from_url(redis_url)
        
        # Test ping pour vérifier la connectivité
        try:
            client.ping()
            logger.debug("[CELERY MONITOR] Connexion Redis OK pour monitoring")
            return client
        except redis.ConnectionError as e:
            logger.warning(f"[CELERY MONITOR] Redis non accessible depuis ce contexte: {e}")
            return None
            
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Impossible de créer le client Redis: {e}")
        return None


def save_metrics_to_file():
    """Sauvegarde les métriques dans un fichier JSON pour accès local."""
    try:
        # Sauvegarder les métriques principales (sans les échantillons volumineux)
        metrics_to_save = {
            'args_max_size': CELERY_SIZE_METRICS['args_max_size'],
            'kwargs_max_size': CELERY_SIZE_METRICS['kwargs_max_size'],
            'args_avg_size': CELERY_SIZE_METRICS['args_avg_size'],
            'kwargs_avg_size': CELERY_SIZE_METRICS['kwargs_avg_size'],
            'total_measurements': CELERY_SIZE_METRICS['total_measurements'],
            'truncated_count': CELERY_SIZE_METRICS['truncated_count'],
            'max_task_name': CELERY_SIZE_METRICS['max_task_name'],
            'recommended_max': CELERY_SIZE_METRICS['recommended_max'],
            'last_updated': datetime.now().isoformat()
        }
        
        # Créer le répertoire s'il n'existe pas
        import os
        metrics_dir = '/tmp/celery_metrics'
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Sauvegarder avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{metrics_dir}/celery_metrics_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(metrics_to_save, f, indent=2)
        
        # Sauvegarder aussi la dernière version
        latest_file = f'{metrics_dir}/celery_metrics_latest.json'
        with open(latest_file, 'w') as f:
            json.dump(metrics_to_save, f, indent=2)
        
        logger.debug(f"[CELERY MONITOR] Métriques sauvegardées dans {latest_file}")
        return True
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Erreur sauvegarde fichier: {e}")
        return False


def save_metrics_to_redis():
    """Sauvegarde les métriques dans Redis pour accès depuis l'extérieur."""
    try:
        redis_client = get_redis_client()
        if redis_client is None:
            return False
        
        # Sauvegarder les métriques principales (sans les échantillons volumineux)
        metrics_to_save = {
            'args_max_size': CELERY_SIZE_METRICS['args_max_size'],
            'kwargs_max_size': CELERY_SIZE_METRICS['kwargs_max_size'],
            'args_avg_size': CELERY_SIZE_METRICS['args_avg_size'],
            'kwargs_avg_size': CELERY_SIZE_METRICS['kwargs_avg_size'],
            'total_measurements': CELERY_SIZE_METRICS['total_measurements'],
            'truncated_count': CELERY_SIZE_METRICS['truncated_count'],
            'max_task_name': CELERY_SIZE_METRICS['max_task_name'],
            'recommended_max': CELERY_SIZE_METRICS['recommended_max'],
            'last_updated': datetime.now().isoformat()
        }
        
        redis_client.set('celery_metrics', json.dumps(metrics_to_save), ex=3600)  # 1 heure
        return True
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Erreur sauvegarde Redis: {e}")
        return False


def get_metrics_from_file():
    """Récupère les métriques depuis les fichiers JSON."""
    try:
        import os
        metrics_dir = '/tmp/celery_metrics'
        latest_file = f'{metrics_dir}/celery_metrics_latest.json'
        
        if not os.path.exists(latest_file):
            return None
        
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Erreur récupération fichier: {e}")
        return None


def get_metrics_from_redis():
    """Récupère les métriques depuis Redis."""
    try:
        redis_client = get_redis_client()
        if redis_client is None:
            return None
        
        data = redis_client.get('celery_metrics')
        if data is None:
            return None
        
        return json.loads(data)
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Erreur récupération Redis: {e}")
        return None


def measure_json_size(obj: Any) -> int:
    """Mesure la taille d'un objet JSON en caractères."""
    try:
        json_str = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        return len(json_str)
    except (TypeError, ValueError):
        return 0


def measure_celery_task_size(task: Any, task_id: str = None) -> Dict[str, int]:
    """
    Mesure la taille des arguments d'une tâche Celery.
    
    Args:
        task: Objet tâche Celery
        task_id: Identifiant de la tâche pour les logs
    
    Returns:
        Dict avec les tailles mesurées
    """
    metrics = {
        'args_size': 0,
        'kwargs_size': 0,
        'task_name': getattr(task, 'name', 'unknown'),
        'task_id': task_id or getattr(task, 'request', {}).get('id', 'unknown')
    }
    
    try:
        # Mesure des args
        if hasattr(task, 'args') and task.args is not None:
            metrics['args_size'] = measure_json_size(task.args)
        
        # Mesure des kwargs
        if hasattr(task, 'kwargs') and task.kwargs is not None:
            metrics['kwargs_size'] = measure_json_size(task.kwargs)
        
        # Alternative via request
        if hasattr(task, 'request') and hasattr(task.request, 'args'):
            metrics['args_size'] = max(metrics['args_size'], measure_json_size(task.request.args))
        
        if hasattr(task, 'request') and hasattr(task.request, 'kwargs'):
            metrics['kwargs_size'] = max(metrics['kwargs_size'], measure_json_size(task.request.kwargs))
            
    except Exception as e:
        logger.warning(f"[CELERY MONITOR] Erreur mesure taille tâche {task_id}: {e}")
    
    return metrics


def update_size_metrics(metrics: Dict[str, int]):
    """Met à jour les métriques globales."""
    global CELERY_SIZE_METRICS
    
    CELERY_SIZE_METRICS['total_measurements'] += 1
    CELERY_SIZE_METRICS['last_updated'] = datetime.now().isoformat()
    
    # Mise à jour des maxima
    if metrics['args_size'] > CELERY_SIZE_METRICS['args_max_size']:
        CELERY_SIZE_METRICS['args_max_size'] = metrics['args_size']
        CELERY_SIZE_METRICS['max_task_name'] = f"{metrics['task_name']} (args)"
    
    if metrics['kwargs_size'] > CELERY_SIZE_METRICS['kwargs_max_size']:
        CELERY_SIZE_METRICS['kwargs_max_size'] = metrics['kwargs_size']
        CELERY_SIZE_METRICS['max_task_name'] = f"{metrics['task_name']} (kwargs)"
    
    # Ajout aux échantillons
    CELERY_SIZE_METRICS['args_size_samples'].append(metrics['args_size'])
    CELERY_SIZE_METRICS['kwargs_size_samples'].append(metrics['kwargs_size'])
    
    # Calcul des moyennes (dernières 100 mesures)
    sample_limit = 100
    if len(CELERY_SIZE_METRICS['args_size_samples']) > sample_limit:
        CELERY_SIZE_METRICS['args_size_samples'] = CELERY_SIZE_METRICS['args_size_samples'][-sample_limit:]
    if len(CELERY_SIZE_METRICS['kwargs_size_samples']) > sample_limit:
        CELERY_SIZE_METRICS['kwargs_size_samples'] = CELERY_SIZE_METRICS['kwargs_size_samples'][-sample_limit:]
    
    if CELERY_SIZE_METRICS['args_size_samples']:
        CELERY_SIZE_METRICS['args_avg_size'] = sum(CELERY_SIZE_METRICS['args_size_samples']) / len(CELERY_SIZE_METRICS['args_size_samples'])
    
    if CELERY_SIZE_METRICS['kwargs_size_samples']:
        CELERY_SIZE_METRICS['kwargs_avg_size'] = sum(CELERY_SIZE_METRICS['kwargs_size_samples']) / len(CELERY_SIZE_METRICS['kwargs_size_samples'])
    
    # Calcul de la recommandation (max + 20% de marge)
    max_args = max(CELERY_SIZE_METRICS['args_max_size'], CELERY_SIZE_METRICS['kwargs_max_size'])
    CELERY_SIZE_METRICS['recommended_max'] = int(max_args * 1.2)
    
    # Sauvegarde automatique (fichier + Redis si possible)
    save_metrics_to_file()  # Toujours dans le fichier
    save_metrics_to_redis()  # Redis si disponible


def log_task_size_report(metrics: Dict[str, int]):
    """Affiche un rapport détaillé de la taille de la tâche."""
    task_name = metrics['task_name']
    task_id = metrics['task_id']
    args_size = metrics['args_size']
    kwargs_size = metrics['kwargs_size']
    
    # Référence de comparaison - accès sécurisé à la configuration Celery
    try:
        import celery
        if hasattr(celery, 'amqp') and hasattr(celery.amqp, 'argsrepr_maxsize'):
            current_limit = celery.amqp.argsrepr_maxsize
        else:
            current_limit = 1024  # Valeur par défaut
    except (ImportError, AttributeError):
        current_limit = 1024  # Valeur par défaut si pas accessible
    
    logger.info(f"[CELERY MONITOR] Tâche: {task_name}")
    logger.info(f"[CELERY MONITOR] ID: {task_id}")
    logger.info(f"[CELERY MONITOR] Args: {args_size:,} caractères ({'✓' if args_size < current_limit else '⚠ TRONQUÉ'})")
    logger.info(f"[CELERY MONITOR] Kwargs: {kwargs_size:,} caractères ({'✓' if kwargs_size < current_limit else '⚠ TRONQUÉ'})")
    logger.info(f"[CELERY MONITOR] Limite actuelle: {current_limit:,} caractères")


def get_size_summary() -> str:
    """Retourne un résumé des métriques de taille."""
    # Essayer de récupérer les métriques depuis les fichiers d'abord
    file_metrics = get_metrics_from_file()
    
    if file_metrics:
        # Utiliser les métriques depuis les fichiers
        m = file_metrics
        source = "📁 Données fichier JSON (partagées)"
    else:
        # Essayer Redis comme fallback
        redis_metrics = get_metrics_from_redis()
        
        if redis_metrics:
            # Utiliser les métriques Redis
            m = redis_metrics
            source = "📡 Données Redis (partagées)"
        else:
            # Utiliser les métriques locales (memory-only)
            m = CELERY_SIZE_METRICS
            source = "💾 Données mémoire locale"
    
    last_updated = m.get('last_updated', 'Jamais')
    
    return f"""
=== MÉTRIQUES DE TAILLE CELERY ===
Source: {source}
Dernière mise à jour: {last_updated}

Tâches analysées: {m['total_measurements']:,}
Taille max args: {m['args_max_size']:,} caractères
Taille max kwargs: {m['kwargs_max_size']:,} caractères  
Taille moyenne args: {m['args_avg_size']:.0f} caractères
Taille moyenne kwargs: {m['kwargs_avg_size']:.0f} caractères
Tâches tronquées: {m['truncated_count']:,}
Tâche la plus volumineuse: {m['max_task_name']}
Limite recommandée: {m['recommended_max']:,} caractères

Recommandations:
- Si le max est < 100KB → limite = 131072 (128KB)
- Si le max est < 500KB → limite = 524288 (512KB)  
- Si le max est < 1MB → limite = 1048576 (1MB)
- Si le max est > 1MB → limite = 2097152 (2MB)
"""


def auto_configure_celery_limits():
    """Configure automatiquement les limites Celery selon les métriques."""
    recommended = CELERY_SIZE_METRICS['recommended_max']
    
    if recommended == 0:
        logger.info("[CELERY MONITOR] Pas assez de données pour recommandation")
        return False
    
    # Mapping des recommandations
    if recommended <= 100 * 1024:  # 100KB
        new_limit = 131072  # 128KB
    elif recommended <= 500 * 1024:  # 500KB
        new_limit = 524288  # 512KB
    elif recommended <= 1024 * 1024:  # 1MB
        new_limit = 1048576  # 1MB
    else:
        new_limit = 2097152  # 2MB
    
    logger.info(f"[CELERY MONITOR] Limite recommandée: {recommended:,} → Appliquer: {new_limit:,}")
    return new_limit


def reset_metrics():
    """Remet à zéro les métriques."""
    global CELERY_SIZE_METRICS
    CELERY_SIZE_METRICS = {
        'args_max_size': 0,
        'kwargs_max_size': 0,
        'args_avg_size': 0,
        'kwargs_avg_size': 0,
        'total_measurements': 0,
        'args_size_samples': [],
        'kwargs_size_samples': [],
        'truncated_count': 0,
        'max_task_name': '',
        'recommended_max': 0
    }
    logger.info("[CELERY MONITOR] Métriques remises à zéro")
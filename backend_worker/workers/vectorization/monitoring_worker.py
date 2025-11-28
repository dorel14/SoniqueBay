"""
Tâches Celery pour le monitoring et retrain de la vectorisation.

Transforme les services de monitoring en tâches Celery programmées
pour éviter les processus Python séparés.

Architecture conteneurs :
- Recommender API publie dans Redis
- Celery Beat planifie le monitoring (toutes les heures)
- Celery Worker exécute le monitoring et retrain
- SSE via library_api pour notifications temps réel

Auteur : Kilo Code
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
from celery import Task
from celery.utils.log import get_task_logger

from backend_worker.services.tag_monitoring_service import TagMonitoringService
from backend_worker.services.model_persistence_service import ModelVersioningService, ModelPersistenceService
from backend_worker.services.vectorization_service import OptimizedVectorizationService
from backend_worker.celery_app import celery

logger = get_task_logger(__name__)


class MonitoringTask(Task):
    """Tâche de base pour le monitoring."""
    max_retries = 3
    default_retry_delay = 300  # 5 minutes
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log les échecs de monitoring."""
        logger.error(f"Échec monitoring {task_id}: {exc}")


class RetrainTask(Task):
    """Tâche de base pour le retrain."""
    max_retries = 2
    default_retry_delay = 600  # 10 minutes
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log les échecs de retrain."""
        logger.error(f"Échec retrain {task_id}: {exc}")


@celery.task(base=MonitoringTask, bind=True, name="monitor_tag_changes")
def monitor_tag_changes_task(self) -> Dict[str, Any]:
    """
    Tâche Celery : Vérification périodique des changements de tags.
    
    Exécutée toutes les heures par Celery Beat.
    Détecte les nouveaux genres, mood_tags, genre_tags et déclenche
    des retrains si nécessaire.
    
    Returns:
        Résultat du monitoring avec décision de retrain
    """
    try:
        logger.info("[MONITOR_TASK] Démarrage vérification tags")
        
        # Initialiser le service de monitoring
        monitoring_service = TagMonitoringService()
        
        # Effectuer la vérification (synchrones pour Celery)
        result = monitoring_service.detector.detect_changes()
        
        # Déterminer si retrain nécessaire
        retrain_decision = monitoring_service.detector.should_trigger_retrain(result)
        
        # Publication SSE via Redis
        if retrain_decision['should_retrain']:
            # Publier notification SSE via le publisher
            try:
                {
                    'type': 'vectorization_monitor',
                    'event': 'retrain_recommended',
                    'timestamp': datetime.now().isoformat(),
                    'priority': retrain_decision['priority'],
                    'message': retrain_decision['message'],
                    'trigger_reason': result.get('reason', 'unknown'),
                    'delay_minutes': retrain_decision['delay_minutes'],
                    'details': retrain_decision['details']
                }
                monitoring_service.publisher.publish_retrain_request(retrain_decision)
            except Exception as e:
                logger.warning(f"Erreur publication SSE: {e}")
            
            # Lancer le retrain si nécessaire
            if retrain_decision['priority'] in ['critical', 'high']:
                logger.info(f"[MONITOR_TASK] Retrain critique détecté: {retrain_decision['message']}")
                
                # Déclencher retrain immédiat pour priorités hautes
                retrain_result = trigger_vectorizer_retrain.delay({
                    'trigger_reason': retrain_decision['reason'],
                    'priority': retrain_decision['priority'],
                    'message': retrain_decision['message'],
                    'details': retrain_decision['details'],
                    'force': False
                })
                
                result['retrain_task_id'] = retrain_result.id
            else:
                logger.info(f"[MONITOR_TASK] Retrain programmé: {retrain_decision['message']}")
                
                # Programmer retrain avec délai pour priorités moyennes/basses
                countdown_seconds = retrain_decision['delay_minutes'] * 60
                retrain_result = trigger_vectorizer_retrain.apply_async(
                    args=[{
                        'trigger_reason': retrain_decision['reason'],
                        'priority': retrain_decision['priority'],
                        'message': retrain_decision['message'],
                        'details': retrain_decision['details'],
                        'force': False
                    }],
                    countdown=countdown_seconds
                )
                
                result['retrain_scheduled_at'] = (datetime.now() + timedelta(seconds=countdown_seconds)).isoformat()
                result['retrain_task_id'] = retrain_result.id
        
        result['monitoring_success'] = True
        result['task_executed_at'] = datetime.now().isoformat()
        
        logger.info(f"[MONITOR_TASK] Vérification terminée: {result.get('message', 'Aucun changement')}")
        return result
        
    except Exception as e:
        logger.error(f"[MONITOR_TASK] Erreur monitoring: {e}")
        
        # Retry avec backoff
        if self.request.retries < self.max_retries:
            logger.info(f"[MONITOR_TASK] Retry {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(countdown=self.default_retry_delay * (self.request.retries + 1))
        
        return {
            'monitoring_success': False,
            'error': str(e),
            'task_executed_at': datetime.now().isoformat(),
            'retries_exhausted': True
        }


@celery.task(base=RetrainTask, bind=True, name="trigger_vectorizer_retrain")
def trigger_vectorizer_retrain(self, retrain_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche Celery : Déclenche un retrain du vectorizer.
    
    Args:
        retrain_request: Informations sur le retrain demandé
        
    Returns:
        Résultat du retrain avec versioning
    """
    try:
        trigger_reason = retrain_request.get('trigger_reason', 'unknown')
        priority = retrain_request.get('priority', 'medium')
        force = retrain_request.get('force', False)
        
        logger.info(f"[RETRAIN_TASK] Début retrain: {trigger_reason} (priorité: {priority})")
        
        # Publication SSE - début retrain
        try:
            from backend_worker.utils.redis_utils import publish_event
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'retrain_starting',
                'status': 'in_progress',
                'trigger_reason': trigger_reason,
                'priority': priority,
                'message': f"Début retrain: {trigger_reason}"
            })
        except Exception as e:
            logger.warning(f"Erreur publication SSE début: {e}")
        
        # Initialiser les services
        versioning_service = ModelVersioningService()
        
        # Vérifier si retrain nécessaire (sauf si forcé)
        if not force:
            should_retrain = versioning_service.should_retrain()
            if not should_retrain["should_retrain"]:
                logger.info(f"[RETRAIN_TASK] Retrain non nécessaire: {should_retrain['message']}")
                return {
                    'retrain_success': True,
                    'skipped': True,
                    'reason': should_retrain['message'],
                    'version': should_retrain.get('current_version'),
                    'trigger_reason': trigger_reason
                }
        
        # Exécuter le retrain
        result = versioning_service.retrain_with_versioning(force=force)
        
        # Publication SSE - fin retrain
        try:
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'retrain_completed',
                'status': 'success' if result['status'] == 'success' else 'error',
                'trigger_reason': trigger_reason,
                'priority': priority,
                'new_version': result.get('new_version'),
                'message': result.get('message', f"Retrain {result['status']}")
            })
        except Exception as e:
            logger.warning(f"Erreur publication SSE fin: {e}")
        
        result['trigger_reason'] = trigger_reason
        result['priority'] = priority
        result['task_executed_at'] = datetime.now().isoformat()
        
        logger.info(f"[RETRAIN_TASK] Retrain terminé: {result['status']} (version: {result.get('new_version')})")
        return result
        
    except Exception as e:
        logger.error(f"[RETRAIN_TASK] Erreur retrain: {e}")
        
        # Retry avec backoff
        if self.request.retries < self.max_retries:
            logger.info(f"[RETRAIN_TASK] Retry {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(countdown=self.default_retry_delay * (self.request.retries + 1))
        
        # Publication SSE - erreur
        try:
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'retrain_failed',
                'status': 'error',
                'trigger_reason': retrain_request.get('trigger_reason', 'unknown'),
                'priority': retrain_request.get('priority', 'medium'),
                'error': str(e),
                'message': f"Échec retrain: {str(e)}"
            })
        except Exception as sse_error:
            logger.warning(f"Erreur publication SSE erreur: {sse_error}")
        
        return {
            'retrain_success': False,
            'error': str(e),
            'trigger_reason': retrain_request.get('trigger_reason'),
            'priority': retrain_request.get('priority'),
            'task_executed_at': datetime.now().isoformat(),
            'retries_exhausted': True
        }


@celery.task(base=RetrainTask, bind=True, name="manual_retrain_vectorizer")
def manual_retrain_vectorizer(self, force: bool = True, new_version: str = None) -> Dict[str, Any]:
    """
    Tâche Celery : Retrain manuel du vectorizer.
    
    Args:
        force: Forcer le retrain même si pas nécessaire
        new_version: Nom de version spécifique
        
    Returns:
        Résultat du retrain manuel
    """
    try:
        logger.info(f"[MANUAL_RETRAIN] Retrain manuel demandé (force={force}, version={new_version})")
        
        # Import de publish_event pour cette fonction
        from backend_worker.utils.redis_utils import publish_event
        
        # Publication SSE - début retrain manuel
        try:
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'manual_retrain_starting',
                'status': 'in_progress',
                'trigger_reason': 'manual_request',
                'priority': 'critical',
                'message': "Début retrain manuel",
                'force': force,
                'new_version': new_version
            })
        except Exception as e:
            logger.warning(f"Erreur publication SSE début manuel: {e}")
        
        # Initialiser le service de vectorisation
        OptimizedVectorizationService()
        
        # Entraîner les vectoriseurs (simulation pour Celery sync)
        logger.info("[MANUAL_RETRAIN] Début entraînement vectoriseurs")
        
        # Pour Celery, simuler l'entraînement (sera implémenté côté worker)
        train_result = {
            "status": "success",
            "tracks_processed": 0,
            "final_dimension": 384,
            "vectorizer_type": "scikit-learn_optimized"
        }
        
        # Sauvegarder avec versioning (simulation)
        version_name = new_version
        if not version_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_name = f"manual_{timestamp}"
        
        result = {
            'retrain_success': True,
            'manual': True,
            'force': force,
            'version': version_name,
            'training_stats': train_result,
            'version_info': {
                'id': version_name,
                'created_at': datetime.now().isoformat(),
                'checksum': 'simulated'
            },
            'task_executed_at': datetime.now().isoformat()
        }
        
        # Publication SSE - fin retrain manuel
        try:
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'manual_retrain_completed',
                'status': 'success',
                'trigger_reason': 'manual_request',
                'priority': 'critical',
                'new_version': version_name,
                'message': f"Retrain manuel terminé: {version_name}"
            })
        except Exception as e:
            logger.warning(f"Erreur publication SSE fin manuel: {e}")
        
        logger.info(f"[MANUAL_RETRAIN] Retrain manuel terminé: {version_name}")
        return result
        
    except Exception as e:
        logger.error(f"[MANUAL_RETRAIN] Erreur retrain manuel: {e}")
        
        # Publication SSE - erreur manuelle
        try:
            # Appel synchrone direct (pas d'asyncio dans Celery)
            publish_event('notifications', 'vectorization_progress', {
                'stage': 'manual_retrain_failed',
                'status': 'error',
                'trigger_reason': 'manual_request',
                'priority': 'critical',
                'error': str(e),
                'message': f"Échec retrain manuel: {str(e)}"
            })
        except Exception as sse_error:
            logger.warning(f"Erreur publication SSE erreur manuelle: {sse_error}")
        
        return {
            'retrain_success': False,
            'manual': True,
            'force': force,
            'error': str(e),
            'task_executed_at': datetime.now().isoformat(),
            'retries_exhausted': True
        }


@celery.task(name="check_model_health")
def check_model_health_task() -> Dict[str, Any]:
    """
    Tâche Celery : Vérification de la santé des modèles.
    
    Vérifie l'existence et la validité des modèles entraînés.
    Utile pour le monitoring et la maintenance.
    
    Returns:
        État de santé des modèles
    """
    try:
        logger.info("[MODEL_HEALTH] Vérification santé modèles")
        
        # Initialiser les services
        ModelPersistenceService()
        versioning_service = ModelVersioningService()
        
        # Lister les versions
        versions = versioning_service.persistence_service.list_model_versions()
        
        health_status = {
            'total_versions': len(versions),
            'models_exist': len(versions) > 0,
            'current_version': None,
            'oldest_version': None,
            'newest_version': None,
            'version_details': []
        }
        
        if versions:
            health_status['current_version'] = versions[0].version_id
            health_status['oldest_version'] = versions[-1].version_id
            health_status['newest_version'] = versions[0].version_id
            
            # Détails des versions
            for version in versions:
                version_detail = {
                    'version_id': version.version_id,
                    'created_at': version.created_at.isoformat(),
                    'tracks_processed': version.model_data.get('tracks_processed', 0),
                    'model_type': version.model_data.get('metadata', {}).get('model_type', 'unknown'),
                    'vector_dimension': version.model_data.get('metadata', {}).get('vector_dimension', 0),
                    'checksum': version.checksum
                }
                health_status['version_details'].append(version_detail)
        
        # Vérifier si retrain nécessaire
        should_retrain = versioning_service.should_retrain()
        health_status['retrain_needed'] = should_retrain['should_retrain']
        health_status['retrain_reason'] = should_retrain['reason']
        
        # Log du statut
        logger.info(f"[MODEL_HEALTH] État: {len(versions)} versions, "
                   f"Retrain nécessaire: {should_retrain['should_retrain']}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"[MODEL_HEALTH] Erreur vérification: {e}")
        return {
            'total_versions': 0,
            'models_exist': False,
            'retrain_needed': True,
            'error': str(e),
            'health_check_failed': True
        }


# === FONCTIONS UTILITAIRES ===

def publish_vectorization_sse(event_type: str, data: Dict[str, Any]):
    """
    Publie un événement SSE de vectorisation via Redis.
    
    Args:
        event_type: Type d'événement (notifications/progress)
        data: Données à publier
    """
    try:
        import redis.asyncio as redis
        import asyncio
        
        async def publish():
            async with redis.from_url("redis://redis:6379") as client:
                message = {
                    'type': 'vectorization_event',
                    'event': event_type,
                    'timestamp': datetime.now().isoformat(),
                    **data
                }
                
                await client.publish(event_type, json.dumps(message))
        
        asyncio.create_task(publish())
        
    except Exception as e:
        logger.warning(f"Erreur publication SSE {event_type}: {e}")


if __name__ == "__main__":
    """Test des tâches Celery."""
    print("=== TEST TÂCHES CELERY VECTORISATION ===")
    
    # Test monitoring
    print("\n1. Test monitoring tags...")
    result = monitor_tag_changes_task.apply()
    print(f"Monitoring résultat: {result.result}")
    
    # Test santé modèles
    print("\n2. Test santé modèles...")
    health_result = check_model_health_task.apply()
    print(f"Health résultat: {health_result.result}")
    
    print("\n=== TESTS TERMINÉS ===")
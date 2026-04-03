"""Tâches TaskIQ pour le monitoring et le retrain de la vectorisation.
Migration de backend_worker/workers/vectorization/monitoring_worker.py vers TaskIQ.
"""
import asyncio
from typing import Dict, Any
from backend.tasks.taskiq_app import broker
from backend.utils.logging import logger

# Note: We are migrating the internal async functions of the Celery tasks.
# The Celery tasks had retry logic and base classes that we are not replicating here.
# This is a known limitation: the TaskIQ tasks do not have the same retry behavior as the Celery tasks.
# For now, we focus on converting the core logic to async.

@broker.task
async def trigger_vectorizer_retrain(retrain_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche TaskIQ : Déclenche un retrain du vectorizer.
    Converti en async pour TaskIQ à partir de la tâche Celery trigger_vectorizer_retrain.

    Args:
        retrain_request: Informations sur le retrain demandé

    Returns:
        Résultat du retrain avec versioning
    """
    logger.info(f"[TASKIQ|RETRAIN] Début retrain: {retrain_request.get('trigger_reason', 'unknown')} (priorité: {retrain_request.get('priority', 'medium')})")

    try:
        # Import des services nécessaires
        from backend.services.model_persistence_service import ModelVersioningService
        from backend.utils.pubsub import publish_event
        from datetime import datetime

        trigger_reason = retrain_request.get('trigger_reason', 'unknown')
        priority = retrain_request.get('priority', 'medium')
        force = retrain_request.get('force', False)

        # Publication SSE - début retrain
        try:
            publish_event('vectorization_progress', {
                'stage': 'retrain_starting',
                'status': 'in_progress',
                'trigger_reason': trigger_reason,
                'priority': priority,
                'message': f"Début retrain: {trigger_reason}"
            }, channel='notifications')
        except Exception as e:
            logger.warning(f"[TASKIQ|RETRAIN] Erreur publication SSE début: {e}")

        # Initialiser les services
        versioning_service = ModelVersioningService()

        # Vérifier si retrain nécessaire (sauf si forcé)
        if not force:
            should_retrain = await versioning_service.should_retrain()
            if not should_retrain["should_retrain"]:
                logger.info(f"[TASKIQ|RETRAIN] Retrain non nécessaire: {should_retrain['message']}")
                return {
                    'retrain_success': True,
                    'skipped': True,
                    'reason': should_retrain['message'],
                    'version': should_retrain.get('current_version'),
                    'trigger_reason': trigger_reason,
                    'task_executed_at': datetime.now().isoformat()
                }

        # Exécuter le retrain
        result = await versioning_service.retrain_with_versioning(force=force)

        # Publication SSE - fin retrain
        try:
            publish_event('vectorization_progress', {
                'stage': 'retrain_completed',
                'status': 'success' if result['status'] == 'success' else 'error',
                'trigger_reason': trigger_reason,
                'priority': priority,
                'new_version': result.get('new_version'),
                'message': result.get('message', f"Retrain {result['status']}")
            }, channel='notifications')
        except Exception as e:
            logger.warning(f"[TASKIQ|RETRAIN] Erreur publication SSE fin: {e}")

        # Add our standard keys
        result['retrain_success'] = result['status'] == 'success'
        result['skipped'] = False
        result['version'] = result.get('new_version')
        result['trigger_reason'] = trigger_reason
        result['priority'] = priority
        result['task_executed_at'] = datetime.now().isoformat()

        logger.info(f"[TASKIQ|RETRAIN] Retrain terminé: {result['status']} (version: {result.get('new_version')})")
        return result

    except Exception as e:
        logger.error(f"[TASKIQ|RETRAIN] Erreur retrain: {e}")
        # Publication SSE - erreur
        try:
            publish_event('vectorization_progress', {
                'stage': 'retrain_failed',
                'status': 'error',
                'trigger_reason': retrain_request.get('trigger_reason', 'unknown'),
                'priority': retrain_request.get('priority', 'medium'),
                'error': str(e),
                'message': f"Échec retrain: {str(e)}"
            }, channel='notifications')
        except Exception as sse_error:
            logger.warning(f"[TASKIQ|RETRAIN] Erreur publication SSE erreur: {sse_error}")

        return {
            'retrain_success': False,
            'error': str(e),
            'trigger_reason': retrain_request.get('trigger_reason'),
            'priority': retrain_request.get('priority'),
            'task_executed_at': datetime.now().isoformat(),
            'retries_exhausted': True
        }


@broker.task
async def monitor_tag_changes_task() -> Dict[str, Any]:
    """
    Tâche TaskIQ : Vérification périodique des changements de tags.
    Converti en async pour TaskIQ à partir de la tâche Celery monitor_tag_changes_task.

    Returns:
        Résultat du monitoring avec décision de retrain
    """
    logger.info("[TASKIQ|MONITORING] Démarrage vérification tags")

    try:
        # Import des services nécessaires
        from backend.services.tag_monitoring_service import TagMonitoringService
        from backend.services.model_persistence_service import ModelVersioningService
        from backend.utils.pubsub import publish_event
        from backend.services.deferred_queue_service import deferred_queue_service
        from backend.deferred.deferred_enrichment_worker import process_enrichment_batch_task
        from datetime import datetime, timedelta

        # Initialiser le service de monitoring
        monitoring_service = TagMonitoringService()

        # Effectuer la vérification (async)
        result = await monitoring_service.detector.detect_changes()

        # Get failed tasks for deferred enrichment queue
        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_enrichment", limit=5)

        # Déterminer si retrain nécessaire
        retrain_decision = await monitoring_service.detector.should_trigger_retrain(result)

        # Publication SSE via Redis
        if retrain_decision['should_retrain']:
            # Publier notification SSE via le publisher
            try:
                await monitoring_service.publisher.publish_retrain_request(retrain_decision)
            except Exception as e:
                logger.warning(f"[TASKIQ|MONITORING] Erreur publication SSE: {e}")

            # Lancer le retrain si nécessaire
            if retrain_decision['priority'] in ['critical', 'high']:
                logger.info(f"[TASKIQ|MONITORING] Retrain critique détecté: {retrain_decision['message']}")

                # Déclencher retrain immédiat pour priorités hautes
                retrain_task = await trigger_vectorizer_retrain.kiq({
                    'trigger_reason': retrain_decision['reason'],
                    'priority': retrain_decision['priority'],
                    'message': retrain_decision['message'],
                    'details': retrain_decision['details'],
                    'force': False
                })
                retrain_result_task = await retrain_task.wait_result()
                retrain_result = retrain_result_task.return_value

                result['retrain_task_id'] = retrain_result.get('task_id') if isinstance(retrain_result, dict) else None
            else:
                logger.info(f"[TASKIQ|MONITORING] Retrain programmé: {retrain_decision['message']}")

                # Programmer retrain avec délai pour priorités moyennes/basses
                countdown_seconds = retrain_decision['delay_minutes'] * 60

                # Note: TaskIQ doesn't have native delay support like Celery's countdown
                # We run it immediately but log the intended delay
                logger.warning("[TASKIQ|MONITORING] Delayed retrain not supported in TaskIQ version, running immediately")

                retrain_task = await trigger_vectorizer_retrain.kiq({
                    'trigger_reason': retrain_decision['reason'],
                    'priority': retrain_decision['priority'],
                    'message': retrain_decision['message'],
                    'details': retrain_decision['details'],
                    'force': False
                })
                retrain_result_task = await retrain_task.wait_result()
                retrain_result = retrain_result_task.return_value if retrain_result_task else None

                result['retrain_scheduled_at'] = (datetime.now() + timedelta(seconds=countdown_seconds)).isoformat()
                result['retrain_task_id'] = retrain_result.get('task_id') if isinstance(retrain_result, dict) else None

        result['monitoring_success'] = True
        result['task_executed_at'] = datetime.now().isoformat()

        logger.info(f"[TASKIQ|MONITORING] Vérification terminée: {result.get('message', 'Aucun changement')}")
        return result

    except Exception as e:
        logger.error(f"[TASKIQ|MONITORING] Erreur monitoring: {e}")
        return {
            'monitoring_success': False,
            'error': str(e),
            'task_executed_at': datetime.now().isoformat(),
            'retries_exhausted': True
        }


@broker.task
async def check_model_health_task() -> Dict[str, Any]:
    """
    Tâche TaskIQ : Vérification de la santé des modèles.
    Converti en async pour TaskIQ à partir de la tâche Celery check_model_health_task.

    Returns:
        État de santé des modèles
    """
    logger.info("[TASKIQ|MODEL_HEALTH] Vérification santé modèles")

    try:
        # Import des services nécessaires
        from backend.services.model_persistence_service import ModelPersistenceService, ModelVersioningService
        from datetime import datetime

        # Initialiser les services
        ModelPersistenceService()
        versioning_service = ModelVersioningService()

        # Lister les versions (async)
        versions = await versioning_service.persistence_service.list_model_versions()

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

        # Vérifier si retrain nécessaire (async)
        should_retrain = await versioning_service.should_retrain()
        health_status['retrain_needed'] = should_retrain['should_retrain']
        health_status['retrain_reason'] = should_retrain['reason']

        # Add task execution timestamp
        health_status['task_executed_at'] = datetime.now().isoformat()

        # Log du statut
        logger.info(f"[TASKIQ|MODEL_HEALTH] État: {len(versions)} versions, "
                   f"Retrain nécessaire: {should_retrain['should_retrain']}")

        return health_status

    except Exception as e:
        logger.error(f"[TASKIQ|MODEL_HEALTH] Erreur vérification: {e}")
        return {
            'total_versions': 0,
            'models_exist': False,
            'retrain_needed': True,
            'error': str(e),
            'health_check_failed': True
        }
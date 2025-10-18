"""
Worker Deferred Vectors - Traitement différé des vecteurs
Traite les tâches de calcul de vecteurs de manière différée.
"""

import asyncio
from typing import Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.vectorization_service import vectorize_single_track
from backend_worker.services.deferred_queue_service import deferred_queue_service


@celery.task(name="worker_deferred_vectors.process_vectors_batch", queue="worker_deferred_vectors")
def process_vectors_batch_task(batch_size: int = 3) -> Dict[str, Any]:
    """
    Traite un lot de tâches de calcul de vecteurs.

    Args:
        batch_size: Nombre maximum de tâches à traiter (limité car CPU intensif)

    Returns:
        Résultats du traitement par lot
    """
    try:
        logger.info(f"[WORKER_DEFERRED_VECTORS] Démarrage traitement batch de {batch_size} tâches")

        processed = 0
        successful = 0
        failed = 0
        results = []

        for _ in range(batch_size):
            # Récupère la prochaine tâche
            task = deferred_queue_service.dequeue_task("deferred_vectors")

            if not task:
                break  # Plus de tâches

            processed += 1
            task_result = _process_single_vector_task(task)

            results.append(task_result)

            if task_result.get("success", False):
                successful += 1
            else:
                failed += 1

        result = {
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "results": results
        }

        logger.info(f"[WORKER_DEFERRED_VECTORS] Batch terminé: {successful}/{processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_VECTORS] Erreur traitement batch: {str(e)}", exc_info=True)
        return {"error": str(e)}


def _process_single_vector_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite une seule tâche de calcul de vecteur.

    Args:
        task: Tâche à traiter

    Returns:
        Résultat du traitement
    """
    try:
        task_data = task["data"]
        track_id = task_data.get("track_id")

        logger.info(f"[WORKER_DEFERRED_VECTORS] Calcul vecteur pour track ID: {track_id}")

        # Calcul du vecteur (CPU intensif)
        result = asyncio.run(vectorize_single_track(track_id))

        success = result.get("status") == "success"
        error_message = None if success else result.get("error", "Erreur inconnue")

        # Met à jour le statut dans la queue
        deferred_queue_service.complete_task(
            "deferred_vectors",
            task["id"],
            success=success,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "track_id": track_id,
            "success": success,
            "vector_dimension": result.get("vector_dimension"),
            "error": error_message
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"[WORKER_DEFERRED_VECTORS] Erreur traitement tâche {task['id']}: {error_message}")

        # Marque comme échoué
        deferred_queue_service.complete_task(
            "deferred_vectors",
            task["id"],
            success=False,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "success": False,
            "error": error_message
        }


@celery.task(name="worker_deferred_vectors.get_vectors_stats", queue="worker_deferred_vectors")
def get_vectors_stats_task() -> Dict[str, Any]:
    """
    Retourne les statistiques de la queue des vecteurs.

    Returns:
        Statistiques détaillées
    """
    try:
        stats = deferred_queue_service.get_queue_stats("deferred_vectors")
        stats["queue_health"] = _calculate_vectors_queue_health(stats)
        return stats

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_VECTORS] Erreur récupération stats: {str(e)}")
        return {"error": str(e)}


@celery.task(name="worker_deferred_vectors.retry_failed_vectors", queue="worker_deferred_vectors")
def retry_failed_vectors_task(max_retries: int = 2) -> Dict[str, Any]:
    """
    Retente les calculs de vecteurs échoués.

    Args:
        max_retries: Nombre maximum de tâches à retenter

    Returns:
        Résultats des retries
    """
    try:
        logger.info(f"[WORKER_DEFERRED_VECTORS] Démarrage retry de {max_retries} tâches échouées")

        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_vectors", limit=max_retries)

        if not failed_tasks:
            return {"message": "Aucune tâche échouée à retenter"}

        retried = 0

        for task in failed_tasks:
            if task.get("retries", 0) >= task.get("max_retries", 3):
                continue

            # Remet en queue avec délai (calculs CPU peuvent être temporaires)
            deferred_queue_service.enqueue_task(
                "deferred_vectors",
                task["data"],
                priority=task.get("priority", "normal"),
                delay_seconds=600,  # 10 minutes
                max_retries=task.get("max_retries", 3)
            )

            retried += 1

        return {
            "failed_tasks_found": len(failed_tasks),
            "retried": retried,
            "message": f"{retried} tâches remises en queue"
        }

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_VECTORS] Erreur retry: {str(e)}")
        return {"error": str(e)}


def _calculate_vectors_queue_health(stats: Dict[str, Any]) -> str:
    """
    Calcule l'état de santé de la queue des vecteurs.

    Args:
        stats: Statistiques de la queue

    Returns:
        État de santé
    """
    pending = stats.get("pending", 0)
    failed = stats.get("failed", 0)
    oldest_seconds = stats.get("oldest_pending_seconds", 0)

    # Vecteurs sont CPU intensifs, donc plus strict
    if pending > 500 or failed > 50 or (oldest_seconds and oldest_seconds > 1800):  # 30 minutes
        return "critical"
    elif pending > 200 or failed > 20 or (oldest_seconds and oldest_seconds > 900):  # 15 minutes
        return "warning"
    else:
        return "healthy"
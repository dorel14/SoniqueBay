"""
Worker Deferred Enrichment - Traitement différé de l'enrichissement
Traite les tâches d'enrichissement (artistes, albums, tracks) de manière différée.
"""

import asyncio
import httpx
from typing import Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.enrichment_service import enrich_artist, enrich_album
from backend_worker.services.audio_features_service import analyze_audio_with_librosa
from backend_worker.services.deferred_queue_service import deferred_queue_service


@celery.task(name="worker_deferred_enrichment.process_enrichment_batch", queue="worker_deferred_enrichment")
def process_enrichment_batch_task(batch_size: int = 10) -> Dict[str, Any]:
    """
    Traite un lot de tâches d'enrichissement en attente.

    Args:
        batch_size: Nombre maximum de tâches à traiter

    Returns:
        Résultats du traitement par lot
    """
    try:
        logger.info(f"[WORKER_DEFERRED_ENRICHMENT] Démarrage traitement batch de {batch_size} tâches")

        processed = 0
        successful = 0
        failed = 0
        results = []

        for _ in range(batch_size):
            # Récupère la prochaine tâche
            task = deferred_queue_service.dequeue_task("deferred_enrichment")

            if not task:
                break  # Plus de tâches

            processed += 1
            task_result = _process_single_enrichment_task(task)

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

        logger.info(f"[WORKER_DEFERRED_ENRICHMENT] Batch terminé: {successful}/{processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_ENRICHMENT] Erreur traitement batch: {str(e)}", exc_info=True)
        return {"error": str(e)}


def _process_single_enrichment_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite une seule tâche d'enrichissement.

    Args:
        task: Tâche à traiter

    Returns:
        Résultat du traitement
    """
    try:
        task_data = task["data"]
        task_type = task_data.get("type")
        entity_id = task_data.get("id")

        logger.info(f"[WORKER_DEFERRED_ENRICHMENT] Traitement {task_type} ID: {entity_id}")

        success = False
        error_message = None

        if task_type == "artist":
            # Enrichissement artiste
            result = asyncio.run(enrich_artist(entity_id))
            success = result is not None

        elif task_type == "album":
            # Enrichissement album
            result = asyncio.run(enrich_album(entity_id))
            success = result is not None

        elif task_type == "track_audio":
            # Analyse audio de la track
            file_path = task_data.get("file_path")
            if file_path:
                result = asyncio.run(analyze_audio_with_librosa(entity_id, file_path))
                success = result is not None and bool(result)
            else:
                error_message = "Chemin de fichier manquant"

        else:
            error_message = f"Type de tâche inconnu: {task_type}"

        # Met à jour le statut dans la queue
        deferred_queue_service.complete_task(
            "deferred_enrichment",
            task["id"],
            success=success,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "type": task_type,
            "entity_id": entity_id,
            "success": success,
            "error": error_message
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"[WORKER_DEFERRED_ENRICHMENT] Erreur traitement tâche {task['id']}: {error_message}")

        # Marque comme échoué
        deferred_queue_service.complete_task(
            "deferred_enrichment",
            task["id"],
            success=False,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "success": False,
            "error": error_message
        }


@celery.task(name="worker_deferred_enrichment.get_enrichment_stats", queue="worker_deferred_enrichment")
def get_enrichment_stats_task() -> Dict[str, Any]:
    """
    Retourne les statistiques de la queue d'enrichissement.

    Returns:
        Statistiques détaillées
    """
    try:
        stats = deferred_queue_service.get_queue_stats("deferred_enrichment")

        # Ajoute des métriques supplémentaires
        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_enrichment", limit=10)

        stats["recent_failures"] = failed_tasks
        stats["queue_health"] = _calculate_queue_health(stats)

        return stats

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_ENRICHMENT] Erreur récupération stats: {str(e)}")
        return {"error": str(e)}


@celery.task(name="worker_deferred_enrichment.retry_failed_enrichments", queue="worker_deferred_enrichment")
def retry_failed_enrichments_task(max_retries: int = 5) -> Dict[str, Any]:
    """
    Retente les enrichissements échoués.

    Args:
        max_retries: Nombre maximum de tâches à retenter

    Returns:
        Résultats des retries
    """
    try:
        logger.info(f"[WORKER_DEFERRED_ENRICHMENT] Démarrage retry de {max_retries} tâches échouées")

        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_enrichment", limit=max_retries)

        if not failed_tasks:
            return {"message": "Aucune tâche échouée à retenter"}

        retried = 0
        successful = 0

        for task in failed_tasks:
            if task.get("retries", 0) >= task.get("max_retries", 3):
                continue  # Déjà max retries atteint

            # Remet en queue avec délai
            deferred_queue_service.enqueue_task(
                "deferred_enrichment",
                task["data"],
                priority=task.get("priority", "normal"),
                delay_seconds=300,  # 5 minutes
                max_retries=task.get("max_retries", 3)
            )

            retried += 1

        return {
            "failed_tasks_found": len(failed_tasks),
            "retried": retried,
            "message": f"{retried} tâches remises en queue"
        }

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_ENRICHMENT] Erreur retry: {str(e)}")
        return {"error": str(e)}


def _calculate_queue_health(stats: Dict[str, Any]) -> str:
    """
    Calcule l'état de santé de la queue.

    Args:
        stats: Statistiques de la queue

    Returns:
        État de santé ("healthy", "warning", "critical")
    """
    pending = stats.get("pending", 0)
    failed = stats.get("failed", 0)
    oldest_seconds = stats.get("oldest_pending_seconds", 0)

    # Logique de calcul de santé
    if pending > 1000 or failed > 100 or (oldest_seconds and oldest_seconds > 3600):  # 1 heure
        return "critical"
    elif pending > 500 or failed > 50 or (oldest_seconds and oldest_seconds > 1800):  # 30 minutes
        return "warning"
    else:
        return "healthy"
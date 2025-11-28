"""
Worker Deferred Covers - Traitement différé des couvertures
Traite les tâches de récupération de couvertures (albums, artistes) de manière différée.
"""

import asyncio
import httpx
from typing import Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.deferred_queue_service import deferred_queue_service


@celery.task(name="worker_deferred_covers.process_covers_batch", queue="worker_deferred_covers")
def process_covers_batch_task(batch_size: int = 5) -> Dict[str, Any]:
    """
    Traite un lot de tâches de récupération de couvertures en attente.

    Args:
        batch_size: Nombre maximum de tâches à traiter

    Returns:
        Résultats du traitement par lot
    """
    try:
        logger.info(f"[WORKER_DEFERRED_COVERS] Démarrage traitement batch de {batch_size} tâches")

        processed = 0
        successful = 0
        failed = 0
        results = []

        for _ in range(batch_size):
            # Récupère la prochaine tâche
            task = deferred_queue_service.dequeue_task("deferred_covers")

            if not task:
                break  # Plus de tâches

            processed += 1
            task_result = _process_single_cover_task(task)

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

        logger.info(f"[WORKER_DEFERRED_COVERS] Batch terminé: {successful}/{processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur traitement batch: {str(e)}", exc_info=True)
        return {"error": str(e)}


def _process_single_cover_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite une seule tâche de récupération de couverture.

    Args:
        task: Tâche à traiter

    Returns:
        Résultat du traitement
    """
    try:
        task_data = task["data"]
        task_type = task_data.get("type")
        entity_id = task_data.get("id")
        mb_release_id = task_data.get("mb_release_id")

        logger.info(f"[WORKER_DEFERRED_COVERS] Traitement {task_type} ID: {entity_id}")

        success = False
        error_message = None

        if task_type == "album_cover" and mb_release_id:
            # Récupération couverture album
            result = asyncio.run(_fetch_album_cover(entity_id, mb_release_id))
            success = result is not None

        elif task_type == "artist_cover":
            # Récupération couverture artiste (pas encore implémenté)
            error_message = "Récupération couverture artiste non implémentée"
            success = False

        else:
            error_message = f"Type de tâche inconnu ou données manquantes: {task_type}"

        # Met à jour le statut dans la queue
        deferred_queue_service.complete_task(
            "deferred_covers",
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
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur traitement tâche {task['id']}: {error_message}")

        # Marque comme échoué
        deferred_queue_service.complete_task(
            "deferred_covers",
            task["id"],
            success=False,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "success": False,
            "error": error_message
        }


async def _fetch_album_cover(album_id: str, mb_release_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère la couverture d'un album depuis Cover Art Archive.

    Args:
        album_id: ID de l'album dans la DB
        mb_release_id: ID MusicBrainz de la release

    Returns:
        Données de couverture ou None
    """
    try:
        async with httpx.AsyncClient() as client:
            cover_data = await get_coverart_image(client, mb_release_id)

            if cover_data:
                image_data, mime_type = cover_data

                # Ici on pourrait sauvegarder en DB ou envoyer à l'API
                # Pour l'instant, on log juste le succès
                logger.info(f"[WORKER_DEFERRED_COVERS] Cover récupérée pour album {album_id}")

                return {
                    "album_id": album_id,
                    "image_data": image_data,
                    "mime_type": mime_type
                }

            return None

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur récupération cover album {album_id}: {str(e)}")
        return None


@celery.task(name="worker_deferred_covers.get_covers_stats", queue="worker_deferred_covers")
def get_covers_stats_task() -> Dict[str, Any]:
    """
    Retourne les statistiques de la queue de couvertures.

    Returns:
        Statistiques détaillées
    """
    try:
        stats = deferred_queue_service.get_queue_stats("deferred_covers")

        # Ajoute des métriques supplémentaires
        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_covers", limit=10)

        stats["recent_failures"] = failed_tasks
        stats["queue_health"] = _calculate_queue_health(stats)

        return stats

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur récupération stats: {str(e)}")
        return {"error": str(e)}


@celery.task(name="worker_deferred_covers.retry_failed_covers", queue="worker_deferred_covers")
def retry_failed_covers_task(max_retries: int = 3) -> Dict[str, Any]:
    """
    Retente les récupérations de couvertures échouées.

    Args:
        max_retries: Nombre maximum de tâches à retenter

    Returns:
        Résultats des retries
    """
    try:
        logger.info(f"[WORKER_DEFERRED_COVERS] Démarrage retry de {max_retries} tâches échouées")

        failed_tasks = deferred_queue_service.get_failed_tasks("deferred_covers", limit=max_retries)

        if not failed_tasks:
            return {"message": "Aucune tâche échouée à retenter"}

        retried = 0

        for task in failed_tasks:
            if task.get("retries", 0) >= task.get("max_retries", 3):
                continue  # Déjà max retries atteint

            # Remet en queue avec délai
            deferred_queue_service.enqueue_task(
                "deferred_covers",
                task["data"],
                priority=task.get("priority", "normal"),
                delay_seconds=900,  # 15 minutes (APIs externes lentes)
                max_retries=task.get("max_retries", 3)
            )

            retried += 1

        return {
            "failed_tasks_found": len(failed_tasks),
            "retried": retried,
            "message": f"{retried} tâches remises en queue"
        }

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur retry: {str(e)}")
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

    # Logique de calcul de santé (plus tolérant car APIs externes)
    if pending > 2000 or failed > 200 or (oldest_seconds and oldest_seconds > 7200):  # 2 heures
        return "critical"
    elif pending > 1000 or failed > 100 or (oldest_seconds and oldest_seconds > 3600):  # 1 heure
        return "warning"
    else:
        return "healthy"
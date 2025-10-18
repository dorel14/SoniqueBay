"""
Worker Deferred Covers - Traitement différé des covers
Traite les tâches de recherche de covers manquantes de manière différée.
"""

import asyncio
import httpx
from typing import Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.lastfm_service import get_lastfm_artist_image
from backend_worker.services.entity_manager import create_or_update_cover
from backend_worker.services.deferred_queue_service import deferred_queue_service


@celery.task(name="worker_deferred_covers.process_covers_batch", queue="worker_deferred_covers")
def process_covers_batch_task(batch_size: int = 5) -> Dict[str, Any]:
    """
    Traite un lot de tâches de recherche de covers.

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
    Traite une seule tâche de recherche de cover.

    Args:
        task: Tâche à traiter

    Returns:
        Résultat du traitement
    """
    try:
        task_data = task["data"]
        entity_type = task_data.get("entity_type")
        entity_id = task_data.get("entity_id")

        logger.info(f"[WORKER_DEFERRED_COVERS] Recherche cover {entity_type} ID: {entity_id}")

        success = False
        error_message = None
        cover_found = False

        # Traitement synchrone avec asyncio.run()
        if entity_type == "album":
            # Recherche cover d'album
            musicbrainz_id = task_data.get("musicbrainz_albumid")
            if musicbrainz_id:
                cover_result = asyncio.run(_search_album_cover(musicbrainz_id, entity_id))
                cover_found = cover_result
            else:
                error_message = "MusicBrainz ID manquant pour l'album"

        elif entity_type == "artist":
            # Recherche image d'artiste
            artist_name = task_data.get("artist_name")
            if artist_name:
                cover_result = asyncio.run(_search_artist_image(artist_name, entity_id))
                cover_found = cover_result
            else:
                error_message = "Nom d'artiste manquant"

        else:
            error_message = f"Type d'entité inconnu: {entity_type}"

        success = cover_found and error_message is None

        # Met à jour le statut dans la queue
        deferred_queue_service.complete_task(
            "deferred_covers",
            task["id"],
            success=success,
            error_message=error_message
        )

        return {
            "task_id": task["id"],
            "entity_type": entity_type,
            "entity_id": entity_id,
            "success": success,
            "cover_found": cover_found,
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


@celery.task(name="worker_deferred_covers.get_covers_stats", queue="worker_deferred_covers")
def get_covers_stats_task() -> Dict[str, Any]:
    """
    Retourne les statistiques de la queue des covers.

    Returns:
        Statistiques détaillées
    """
    try:
        stats = deferred_queue_service.get_queue_stats("deferred_covers")
        stats["queue_health"] = _calculate_covers_queue_health(stats)
        return stats

    except Exception as e:
        logger.error(f"[WORKER_DEFERRED_COVERS] Erreur récupération stats: {str(e)}")
        return {"error": str(e)}


@celery.task(name="worker_deferred_covers.retry_failed_covers", queue="worker_deferred_covers")
def retry_failed_covers_task(max_retries: int = 3) -> Dict[str, Any]:
    """
    Retente les recherches de covers échouées.

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
                continue

            # Remet en queue avec délai plus long (APIs externes)
            deferred_queue_service.enqueue_task(
                "deferred_covers",
                task["data"],
                priority=task.get("priority", "low"),
                delay_seconds=1800,  # 30 minutes (rate limits)
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


def _calculate_covers_queue_health(stats: Dict[str, Any]) -> str:
    """
    Calcule l'état de santé de la queue des covers.

    Args:
        stats: Statistiques de la queue

    Returns:
        État de santé
    """
    pending = stats.get("pending", 0)
    failed = stats.get("failed", 0)
    oldest_seconds = stats.get("oldest_pending_seconds", 0)

    # Plus tolérant car les APIs externes sont lentes
    if pending > 2000 or failed > 200 or (oldest_seconds and oldest_seconds > 7200):  # 2 heures
        return "critical"
    elif pending > 1000 or failed > 100 or (oldest_seconds and oldest_seconds > 3600):  # 1 heure
        return "warning"
    else:
        return "healthy"


async def _search_album_cover(musicbrainz_id: str, entity_id: int) -> bool:
    """
    Recherche une cover d'album via Cover Art Archive.

    Args:
        musicbrainz_id: ID MusicBrainz de l'album
        entity_id: ID de l'entité en base

    Returns:
        True si cover trouvée et sauvegardée
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            from backend_worker.services.coverart_service import get_coverart_image
            from backend_worker.services.entity_manager import create_or_update_cover

            cover_result = await get_coverart_image(client, musicbrainz_id)
            if cover_result:
                cover_data, mime_type = cover_result
                await create_or_update_cover(
                    client, "album", entity_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"coverart://{musicbrainz_id}"
                )
                return True
        return False
    except Exception as e:
        logger.error(f"Erreur recherche cover album {musicbrainz_id}: {str(e)}")
        return False


async def _search_artist_image(artist_name: str, entity_id: int) -> bool:
    """
    Recherche une image d'artiste via Last.fm.

    Args:
        artist_name: Nom de l'artiste
        entity_id: ID de l'entité en base

    Returns:
        True si image trouvée et sauvegardée
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            from backend_worker.services.lastfm_service import get_lastfm_artist_image
            from backend_worker.services.entity_manager import create_or_update_cover

            cover_result = await get_lastfm_artist_image(client, artist_name)
            if cover_result:
                cover_data, mime_type = cover_result
                await create_or_update_cover(
                    client, "artist", entity_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"lastfm://{artist_name}"
                )
                return True
        return False
    except Exception as e:
        logger.error(f"Erreur recherche image artiste {artist_name}: {str(e)}")
        return False
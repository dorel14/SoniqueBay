"""
Router pour l'API de vectorisation - Communication HTTP avec recommender_api
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
from backend_worker.utils.logging import logger

router = APIRouter(prefix="/api/vectorization", tags=["vectorization"])


@router.post("/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_vectorization_event(data: Dict[str, Any]):
    """
    Endpoint pour publier un événement de vectorisation.

    Args:
        data: Données de l'événement (track_id, metadata, event_type)

    Returns:
        Confirmation de publication
    """
    try:
        track_id = data.get("track_id")
        metadata = data.get("metadata", {})
        event_type = data.get("event_type", "track_created")

        if not track_id:
            raise HTTPException(status_code=400, detail="track_id requis")

        logger.info(f"[VECTOR_API] Publication événement {event_type} pour track {track_id}")

        # Publier via Redis
        from backend_worker.utils.redis_utils import publish_vectorization_event as publish_event
        success = await publish_event(track_id, metadata, event_type)

        if success:
            return {"message": f"Événement {event_type} publié pour track {track_id}"}
        else:
            raise HTTPException(status_code=500, detail="Échec publication événement")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VECTOR_API] Erreur publication événement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.post("/vectorize/batch", status_code=status.HTTP_202_ACCEPTED)
async def trigger_batch_vectorization(track_ids: List[int]):
    """
    Déclenche la vectorisation d'un batch de tracks.

    Args:
        track_ids: Liste des IDs de tracks à vectoriser

    Returns:
        Informations sur la tâche lancée
    """
    try:
        if not track_ids:
            raise HTTPException(status_code=400, detail="Liste de track_ids vide")

        logger.info(f"[VECTOR_API] Déclenchement vectorisation batch: {len(track_ids)} tracks")

        # Lancer la tâche Celery via le nouveau système
        from backend_worker.celery_tasks import vectorization_tasks
        result = vectorization_tasks.vectorize_tracks_batch.delay(track_ids)

        return {
            "task_id": result.id,
            "message": f"Vectorisation batch lancée pour {len(track_ids)} tracks",
            "track_count": len(track_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VECTOR_API] Erreur déclenchement vectorisation batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.post("/vectorize/single/{track_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_single_vectorization(track_id: int):
    """
    Déclenche la vectorisation d'une track unique.

    Args:
        track_id: ID de la track à vectoriser

    Returns:
        Informations sur la tâche lancée
    """
    try:
        logger.info(f"[VECTOR_API] Déclenchement vectorisation track {track_id}")

        # Lancer la tâche Celery via le nouveau système
        from backend_worker.celery_tasks import vectorization_tasks
        result = vectorization_tasks.vectorize_single_track.delay(track_id)

        return {
            "task_id": result.id,
            "message": f"Vectorisation lancée pour track {track_id}",
            "track_id": track_id
        }

    except Exception as e:
        logger.error(f"[VECTOR_API] Erreur déclenchement vectorisation track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.post("/train", status_code=status.HTTP_202_ACCEPTED)
async def trigger_vectorizer_training():
    """
    Déclenche l'entraînement du vectorizer avec tous les tags de la BDD.

    Returns:
        Informations sur la tâche lancée
    """
    try:
        logger.info("[VECTOR_API] Déclenchement entraînement vectorizer")

        # Lancer la tâche Celery d'entraînement via le nouveau système
        from backend_worker.celery_tasks import vectorization_tasks
        result = vectorization_tasks.train_vectorizer.delay()

        return {
            "task_id": result.id,
            "message": "Entraînement du vectorizer lancé"
        }

    except Exception as e:
        logger.error(f"[VECTOR_API] Erreur déclenchement entraînement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.get("/status")
async def get_vectorization_status():
    """
    Retourne le statut du système de vectorisation.

    Returns:
        Informations sur le système de vectorisation
    """
    try:
        # Récupérer les informations depuis le service de vectorisation
        from backend_worker.services.vectorization_service import VectorizationService
        VectorizationService()

        status_info = {
            "worker_status": "active",
            "queue_status": "operational",
            "embedding_model": "all-MiniLM-L6-v2",
            "supported_operations": [
                "batch_vectorization",
                "single_vectorization",
                "vectorizer_training",
                "similarity_search"
            ]
        }

        return status_info

    except Exception as e:
        logger.error(f"[VECTOR_API] Erreur récupération statut: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")
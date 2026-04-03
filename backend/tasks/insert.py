from backend.tasks.taskiq_app import broker
from backend.feature_flags import WORKER_DIRECT_DB_ENABLED
from backend.utils.logging import logger

@broker.task
async def insert_direct_batch_task(insertion_data: dict) -> dict:
    """Insertion directe en DB via TaskIQ.
    
    Args:
        insertion_data: Données à insérer (artists, albums, tracks)
        
    Returns:
        Résultat de l'insertion
    """
    if not WORKER_DIRECT_DB_ENABLED:
        logger.warning("[TASKIQ|INSERT] Tentative d'exécution de insert_direct_batch_task alors que WORKER_DIRECT_DB_ENABLED=False")
        return {
            "tracks_inserted": 0,
            "track_ids": [],
            "success": False,
            "error": "WORKER_DIRECT_DB_ENABLED est désactivé. Aucune insertion effectuée."
        }

    # Import DB modules only when needed to avoid import errors when WORKER_DATABASE_URL is not configured
    from backend.db.repositories.track_repository import TrackRepository
    from backend.db.session import get_worker_session

    logger.info("[TASKIQ|INSERT] Démarrage insertion directe batch")
    session_factory = get_worker_session()
    async with session_factory() as session:
        repo = TrackRepository(session)
        
        # Insertion des tracks
        track_ids = await repo.bulk_insert_tracks(insertion_data['tracks'])
        
        await session.commit()
        
        result = {
            "tracks_inserted": len(track_ids),
            "track_ids": track_ids,
            "success": True
        }
        logger.info(f"[TASKIQ|INSERT] Insertion terminée: {result}")
        return result
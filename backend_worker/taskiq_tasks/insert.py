from backend_worker.taskiq_app import broker
from backend_worker.db.repositories.track_repository import TrackRepository
from backend_worker.db.session import get_worker_session

@broker.task
async def insert_direct_batch_task(insertion_data: dict) -> dict:
    """Insertion directe en DB via TaskIQ.
    
    Args:
        insertion_data: Données à insérer (artists, albums, tracks)
        
    Returns:
        Résultat de l'insertion
    """
    session_factory = get_worker_session()
    async with session_factory() as session:
        repo = TrackRepository(session)
        
        # Insertion des tracks
        track_ids = await repo.bulk_insert_tracks(insertion_data['tracks'])
        
        await session.commit()
        
        return {
            "tracks_inserted": len(track_ids),
            "track_ids": track_ids,
            "success": True
        }

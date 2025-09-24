import asyncio

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.scanner import scan_music_task
from backend_worker.services.audio_features_service import analyze_audio_with_librosa, retry_failed_updates
from backend_worker.services.enrichment_service import enrich_artist, enrich_album
from backend_worker.services.vectorization_service import vectorize_tracks, vectorize_single_track
from backend_worker.services.audio_features_service import analyze_audio_batch
from backend_worker.utils.pubsub import publish_event


@celery.task(name="scan_music_task", bind=True)
def scan_music_tasks(self, directory: str):
    """Tâche d'indexation synchrone, exécute une coroutine dans un event loop."""
    def progress_callback(progress):
        # progress = {"current": x, "total": y, "percent": z}
        payload = {
            "task_id": self.request.id,
            **progress
        }
        publish_event("progress", payload, channel="progress")
        self.update_state(state='PROGRESS', meta=progress)
    
    return asyncio.run(scan_music_task(directory, progress_callback=progress_callback))

@celery.task(name='analyze_audio_with_librosa')
def analyze_audio_with_librosa_task(track_id: int, file_path: str):
    """Tâche d'analyse audio avec Librosa."""
    return asyncio.run(analyze_audio_with_librosa(track_id, file_path))

@celery.task(name='retry_failed_updates')
def retry_failed_updates_task():
    """Tâche de reprise des mises à jour en échec."""
    return asyncio.run(retry_failed_updates())

@celery.task(name='enrich_artist_task')
def enrich_artist_task(artist_id: int):
    """Tâche d'enrichissement pour un artiste."""
    logger.info(f"Lancement de la tâche d'enrichissement pour l'artiste ID: {artist_id}")
    return asyncio.run(enrich_artist(artist_id))

@celery.task(name='enrich_album_task')
def enrich_album_task(album_id: int):
    """Tâche d'enrichissement pour un album."""
    logger.info(f"Lancement de la tâche d'enrichissement pour l'album ID: {album_id}")
    return asyncio.run(enrich_album(album_id))

@celery.task(name='vectorize_tracks_task')
def vectorize_tracks_task(track_ids: list[int]):
    """Tâche de calcul des vecteurs pour une liste de tracks."""
    logger.info(f"Lancement de la tâche de vectorisation pour {len(track_ids)} tracks")
    return asyncio.run(vectorize_tracks(track_ids))

@celery.task(name='vectorize_single_track_task')
def vectorize_single_track_task(track_id: int):
    """Tâche de calcul du vecteur pour un track unique."""
    logger.info(f"Lancement de la tâche de vectorisation pour le track ID: {track_id}")
    return asyncio.run(vectorize_single_track(track_id))

@celery.task(name='analyze_audio_batch_task')
def analyze_audio_batch_task(track_data_list: list):
    """Tâche d'analyse audio pour un lot de tracks."""
    logger.info(f"Lancement de l'analyse audio batch pour {len(track_data_list)} tracks")
    return asyncio.run(analyze_audio_batch(track_data_list))

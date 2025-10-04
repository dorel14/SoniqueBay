import asyncio
import httpx

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.scanner import scan_music_task
from backend_worker.services.audio_features_service import analyze_audio_with_librosa, retry_failed_updates
from backend_worker.services.enrichment_service import enrich_artist, enrich_album
from backend_worker.services.vectorization_service import vectorize_tracks, vectorize_single_track
from backend_worker.services.audio_features_service import analyze_audio_batch
from backend_worker.utils.pubsub import publish_event


@celery.task(name="scan_music_task", bind=True)
def scan_music_tasks(self, directory: str, cleanup_deleted: bool = False):
    """Tâche d'indexation synchrone, exécute une coroutine dans un event loop."""
    def progress_callback(progress):
        # progress = {"current": x, "total": y, "percent": z}
        payload = {
            "task_id": self.request.id,
            **progress
        }
        publish_event("progress", payload, channel="progress")
        self.update_state(state='PROGRESS', meta=progress)

        # Update scan session progress
        try:
            import httpx
            api_url = "http://backend:8001"
            # Find session by task_id
            response = httpx.get(f"{api_url}/api/scan-sessions/", timeout=5)
            if response.status_code == 200:
                sessions = response.json()
                for session in sessions:
                    if session.get("task_id") == self.request.id:
                        httpx.put(f"{api_url}/api/scan-sessions/{session['id']}/progress",
                                json={"processed_files": progress.get("current", 0),
                                      "total_files": progress.get("total", 0)},
                                timeout=5)
                        break
        except Exception as e:
            logger.warning(f"Failed to update scan session progress: {e}")

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

@celery.task(name='cleanup_deleted_tracks_task')
def cleanup_deleted_tracks_task(directory: str):
    """Tâche de nettoyage des pistes supprimées."""
    from pathlib import Path

    logger.info(f"Démarrage du nettoyage des pistes supprimées pour {directory}")

    # Get all tracks in DB for this directory
    api_url = "http://backend:8001"
    try:
        response = httpx.get(f"{api_url}/api/tracks/", timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to get tracks: {response.status_code}")
            return

        tracks = response.json()
        db_paths = {track['path'] for track in tracks if track.get('path')}

        # Get all files in directory
        scanned_paths = set()
        for path in Path(directory).rglob('*'):
            if path.is_file() and path.suffix.lower() in ['.mp3', '.flac', '.m4a', '.ogg', '.wav']:
                scanned_paths.add(str(path))

        # Find deleted tracks
        deleted_paths = db_paths - scanned_paths
        if deleted_paths:
            logger.info(f"Suppression de {len(deleted_paths)} pistes supprimées")
            for path in deleted_paths:
                # Find track by path and delete
                delete_response = httpx.delete(f"{api_url}/api/tracks/search?path={path}", timeout=10)
                if delete_response.status_code == 200:
                    logger.info(f"Supprimé: {path}")
                else:
                    logger.warning(f"Échec suppression: {path}")
        else:
            logger.info("Aucune piste supprimée trouvée")

    except Exception as e:
        logger.error(f"Erreur nettoyage: {str(e)}")

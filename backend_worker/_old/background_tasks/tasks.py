import asyncio
import httpx
import os
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.audio_features_service import analyze_audio_with_librosa, retry_failed_updates
from backend_worker.services.enrichment_service import enrich_artist, enrich_album
from backend_worker.services.vectorization_service import OptimizedVectorizationService, vectorize_single_track_optimized
from backend_worker.services.audio_features_service import analyze_audio_batch
from backend_worker.utils.pubsub import publish_event


@celery.task(name="scan_music_task", bind=True)
def scan_music_tasks(self, directory: str, cleanup_deleted: bool = False, progress_callback=None):
    """Tâche d'indexation synchrone - évitant la récursion."""
    try:
        # Removed problematic logger.info to avoid recursion error

        def progress_callback(progress):
            payload = {"task_id": self.request.id, **progress}
            publish_event("progress", payload, channel="progress")
            self.update_state(state='PROGRESS', meta=progress)

        # Scanner directement - éviter l'appel à une autre tâche Celery
        from pathlib import Path
        import time
        
        start_time = time.time()
        
        # Extensions musicales supportées
        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
        
        # Découverte des fichiers
        discovered_files = []
        base_path = Path(directory)
        
        def scan_recursive(current_path: Path):
            """Scan récursif simple pour discovery."""
            try:
                for file_path in current_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in music_extensions:
                        discovered_files.append(str(file_path))
            except (OSError, PermissionError):
                pass  # Éviter les logs pour éviter récursion
        
        scan_recursive(base_path)
        
        total_files = len(discovered_files)
        
        # Publier la progression
        if progress_callback:
            progress_callback({
                "current": total_files,
                "total": total_files,
                "percent": 100,
                "step": "Discovery terminée",
                "files_discovered": total_files
            })
        
        # Résultat
        result = {
            "directory": directory,
            "files_discovered": total_files,
            "file_paths": discovered_files,
            "discovery_time": time.time() - start_time,
            "success": True
        }

        # Envoyer vers l'extraction
        file_paths = result.get('file_paths', [])
        if file_paths:
            batch_size = 25
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                celery.send_task(
                    'extract_metadata_batch',
                    args=[batch],
                    queue='extract',
                    priority=5
                )

        return result

    except Exception:
        # Removed logger.error to avoid recursion error
        raise

@celery.task(name='analyze_audio_with_librosa_task')
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
    service = OptimizedVectorizationService()
    return asyncio.run(service.vectorize_and_store_batch(track_ids))

@celery.task(name='vectorize_single_track_task')
def vectorize_single_track_task(track_id: int):
    """Tâche de calcul du vecteur pour un track unique."""
    logger.info(f"Lancement de la tâche de vectorisation pour le track ID: {track_id}")
    return asyncio.run(vectorize_single_track_optimized(track_id))

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

    api_url = os.getenv("LIBRARY_API_URL", "http://library-api:8001")
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
                delete_response = httpx.delete(f"{api_url}/api/tracks/search?path={path}", timeout=10)
                if delete_response.status_code == 200:
                    logger.info(f"Supprimé: {path}")
                else:
                    logger.warning(f"Échec suppression: {path}")
        else:
            logger.info("Aucune piste supprimée trouvée")

    except Exception as e:
        logger.error(f"Erreur nettoyage: {str(e)}")

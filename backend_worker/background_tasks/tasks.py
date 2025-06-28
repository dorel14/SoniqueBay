import asyncio
from backend_worker.celery_app import celery
from backend_worker.services.scanner import scan_music_task
from backend_worker.services.audio_features_service import analyze_audio_with_librosa, retry_failed_updates



@celery.task(name="scan_music_task")
def scan_music_tasks(directory: str):
    """Tâche d'indexation synchrone, exécute une coroutine dans un event loop."""
    return asyncio.run(scan_music_task(directory))

@celery.task(name='analyze_audio_with_librosa')
def analyze_audio_with_librosa_task(track_id: int, file_path: str):
    """Tâche d'analyse audio avec Librosa."""
    return asyncio.run(analyze_audio_with_librosa(track_id, file_path))

@celery.task(name='retry_failed_updates')
def retry_failed_updates_task():
    """Tâche de reprise des mises à jour en échec."""
    return asyncio.run(retry_failed_updates())

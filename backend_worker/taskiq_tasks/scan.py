"""Tâches TaskIQ pour le scan.
Migration de celery_tasks.py vers TaskIQ.
"""
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger
# Note: We avoid importing from backend_worker.utils.pubsub to keep the TaskIQ worker independent
# Instead, we will mimic the progress callback by calling it if provided (it's a function from Celery context)
# In the TaskIQ version, we will just call the progress_callback if it's provided (same as Celery)


@broker.task
async def discovery_task(directory: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Découverte de fichiers musicaux et lancement de la pipeline complète.
    Converti en async pour TaskIQ.

    Pipeline : discovery → extract_metadata → batch_entities → insert_batch

    Args:
        directory: Répertoire à scanner
        progress_callback: Fonction de callback pour la progression

    Returns:
        Résultat de la découverte et lancement de la pipeline
    """
    logger.info(f"[TASKIQ|SCAN] Démarrage discovery: {directory}")
    
    start_time = time.time()
    task_id = None  # TaskIQ doesn't provide task_id in the same way, but we can generate one or leave None

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
        except (OSError, PermissionError) as e:
            logger.warning(f"[TASKIQ|SCAN] Erreur accès {current_path}: {e}")

    scan_recursive(base_path)

    total_files = len(discovered_files)
    logger.info(f"[TASKIQ|SCAN] Discovery terminée: {total_files} fichiers trouvés")

    # Publier la progression
    if progress_callback:
        progress_callback({
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "step": "Discovery terminée",
            "files_discovered": total_files
        })

    # Si des fichiers ont été trouvés, lancer la pipeline complète
    if discovered_files:
        logger.info(f"[TASKIQ|SCAN] Lancement de la pipeline d'extraction pour {total_files} fichiers")
        
        # Diviser en batches pour l'extraction (50 fichiers par batch)
        batch_size = 50
        batches = [discovered_files[i:i + batch_size] for i in range(0, len(discovered_files), batch_size)]
        
        logger.info(f"[TASKIQ|SCAN] Création de {len(batches)} batches d'extraction")
        
        # Envoyer chaque batch vers l'extraction (via TaskIQ)
        for i, batch_files in enumerate(batches):
            batch_id = f"batch_{i+1}_{len(batches)}"
            logger.info(f"[TASKIQ|SCAN] Envoi batch {i+1}/{len(batches)}: {len(batch_files)} fichiers")
            
            # Instead of using celery.send_task, we use the TaskIQ broker to send a task
            # We are in an async context, so we can use kiq to send the task
            from backend_worker.taskiq_tasks.metadata import extract_metadata_batch_task
            await extract_metadata_batch_task.kiq(file_paths=batch_files, batch_id=batch_id)

    result = {
        "directory": directory,
        "files_discovered": total_files,
        "file_paths": discovered_files,
        "discovery_time": time.time() - start_time,
        "batches_created": len(batches) if discovered_files else 0,
        "success": True
    }
    
    logger.info(f"[TASKIQ|SCAN] Discovery et pipeline lancée: {result}")
    return result
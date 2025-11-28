"""
Worker Scan - Discovery et extraction de métadonnées optimisée pour Raspberry Pi

Responsabilités :
- Discovery des fichiers musicaux (scan récursif optimisé)
- Extraction des métadonnées (avec ThreadPoolExecutor limité à 2 workers)
- Envoi vers batching et insertion

Optimisations Raspberry Pi :
- max_workers = 2 pour éviter surcharge CPU/mémoire
- Timeouts réduits (120s par fichier)
- Batches plus petits (50-100 fichiers)
- Pas de limitation longueur chemins (utilise Path.resolve())
- Barre de progression fonctionnelle via pubsub

Architecture :
1. Discovery : scan_music_task -> retourne file_paths
2. Extraction : extract_metadata_batch -> envoie vers batch
3. Batching : batch_entities -> envoie vers insert
4. Insertion : insert_batch_direct -> insertion en base

Conventions :
- Logs via backend_worker.utils.logging
- Docstrings pour toutes fonctions
- Annotations de type
- Imports absolus
- Pas de print, pas de code obsolète
"""

import time
from pathlib import Path

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


@celery.task(name='scan_music_task', queue='scan', bind=True)
def scan_music_task(self, directory: str, progress_callback=None):
    """
    Tâche de discovery uniquement - retourne les chemins de fichiers musicaux.

    Optimisée pour Raspberry Pi : scan récursif simple, pas d'extraction.

    Args:
        directory: Répertoire à scanner
        progress_callback: Fonction de callback pour la progression

    Returns:
        Liste des chemins de fichiers découverts
    """
    start_time = time.time()

    try:
        logger.info(f"[SCAN] Démarrage discovery: {directory}")

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
                logger.warning(f"[SCAN] Erreur accès {current_path}: {e}")

        scan_recursive(base_path)

        total_files = len(discovered_files)
        logger.info(f"[SCAN] Discovery terminée: {total_files} fichiers trouvés")

        # Publier la progression
        if progress_callback:
            progress_callback({
                "current": total_files,
                "total": total_files,
                "percent": 100,
                "step": "Discovery terminée",
                "files_discovered": total_files
            })

        # Retourner les chemins pour traitement par metadata worker
        result = {
            "directory": directory,
            "files_discovered": total_files,
            "file_paths": discovered_files,
            "discovery_time": time.time() - start_time,
            "success": True
        }

        logger.info(f"[SCAN] Discovery terminée: {result}")
        return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[SCAN] Erreur discovery après {error_time:.2f}s: {str(e)}")

        error_result = {
            "error": str(e),
            "directory": directory,
            "duration": error_time,
            "success": False
        }
        return error_result


"""
TÂCHES DE SCAN OPTIMISÉES POUR HAUTE PERFORMANCE

Ces tâches remplacent l'architecture monolithique par un pipeline distribué
capable de traiter des milliers de fichiers en parallèle.
"""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any
import logging

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event



@celery.task(name='scan_directory_parallel', queue='scan', bind=True)
def scan_directory_parallel(self, directory: str, batch_size: int = 10000):
    """
    Tâche de découverte parallélisée ultra-rapide.

    Parcourt un répertoire de manière massive et distribue les fichiers
    trouvés vers l'extraction en batches optimisés.

    Args:
        directory: Répertoire à scanner
        batch_size: Taille des batches à envoyer vers l'extraction

    Returns:
        Statistiques du scan de découverte
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[SCAN] Démarrage découverte parallélisée: {directory}")
        logger.info(f"[SCAN] Task ID: {task_id}")
        logger.info(f"[SCAN] Batch size: {batch_size}")

        # Validation du répertoire
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory does not exist: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"Path is not a directory: {directory}")

        # Extensions musicales supportées
        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}

        # Découverte massive avec ThreadPoolExecutor
        discovered_files = []
        base_path = Path(directory)

        def scan_subdirectories(root_path: Path):
            """Scan récursif d'un sous-répertoire."""
            try:
                for file_path in root_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in music_extensions:
                        discovered_files.append(str(file_path))
            except (OSError, PermissionError) as e:
                logger.warning(f"[SCAN] Erreur accès {root_path}: {e}")

        # Parallélisation du scan avec plusieurs threads
        subdirectories = [base_path]
        for subdir in base_path.rglob('*'):
            if subdir.is_dir() and subdir != base_path:
                subdirectories.append(subdir)

        # Limiter le nombre de threads pour éviter la surcharge
        max_threads = min(32, len(subdirectories) + 1)

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Scanner le répertoire de base + sous-répertoires en parallèle
            futures = []
            for subdir in subdirectories[:max_threads]:  # Limiter aux threads disponibles
                future = executor.submit(scan_subdirectories, subdir)
                futures.append(future)

            # Attendre la fin de tous les scans
            for future in futures:
                try:
                    future.result(timeout=300)  # 5 minutes timeout par sous-répertoire
                except Exception as e:
                    logger.error(f"[SCAN] Erreur scan sous-répertoire: {e}")

        total_files = len(discovered_files)
        logger.info(f"[SCAN] Découverte terminée: {total_files} fichiers trouvés en {time.time() - start_time:.2f}s")

        # Publier les métriques
        publish_event("scan_progress", {
            "task_id": task_id,
            "step": "discovery_completed",
            "files_discovered": total_files,
            "discovery_time": time.time() - start_time
        })

        # Distribuer les fichiers vers l'extraction par batches
        files_sent = 0
        for i in range(0, total_files, batch_size):
            batch = discovered_files[i:i + batch_size]

            # Envoyer le batch vers l'extraction
            celery.send_task(
                'extract_metadata_batch',
                args=[batch],
                queue='extract',
                priority=5  # Priorité normale
            )

            files_sent += len(batch)

            # Update progression
            progress = min(90, (i / total_files) * 90) if total_files > 0 else 0
            self.update_state(state='PROGRESS', meta={
                'current': i,
                'total': total_files,
                'percent': progress,
                'step': f'Distributing batch {i//batch_size + 1}/{(total_files//batch_size) + 1}'
            })

        # Métriques finales
        total_time = time.time() - start_time

        result = {
            'task_id': task_id,
            'directory': directory,
            'files_discovered': total_files,
            'files_sent_to_extraction': files_sent,
            'batches_created': (total_files // batch_size) + 1,
            'discovery_time': total_time,
            'files_per_second': total_files / total_time if total_time > 0 else 0,
            'success': True
        }

        logger.info(f"[SCAN] Distribution terminée: {result}")
        return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[SCAN] Erreur découverte après {error_time:.2f}s: {str(e)}")

        # Publier l'erreur
        publish_event("scan_error", {
            "task_id": task_id,
            "error": str(e),
            "directory": directory,
            "duration": error_time
        })

        raise


@celery.task(name='scan_single_file', queue='scan')
def scan_single_file(file_path: str):
    """
    Tâche de scan d'un fichier unique (pour tests ou ajouts individuels).

    Args:
        file_path: Chemin du fichier à scanner

    Returns:
        Métadonnées du fichier ou None si erreur
    """
    try:
        logger.debug(f"[SCAN] Traitement fichier unique: {file_path}")

        if not os.path.exists(file_path):
            logger.warning(f"[SCAN] Fichier inexistant: {file_path}")
            return None

        if not os.path.isfile(file_path):
            logger.warning(f"[SCAN] Chemin n'est pas un fichier: {file_path}")
            return None

        # Extensions musicales
        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
        if Path(file_path).suffix.lower() not in music_extensions:
            logger.debug(f"[SCAN] Extension non musicale: {file_path}")
            return None

        # Retourner le chemin pour traitement par l'extraction
        return file_path

    except Exception as e:
        logger.error(f"[SCAN] Erreur fichier unique {file_path}: {e}")
        return None


@celery.task(name='scan_directory_chunk', queue='scan')
def scan_directory_chunk(directory: str, chunk_id: int, total_chunks: int):
    """
    Tâche de scan d'un chunk de répertoire (pour distribution sur plusieurs workers).

    Args:
        directory: Répertoire à scanner
        chunk_id: ID du chunk (0-based)
        total_chunks: Nombre total de chunks

    Returns:
        Liste des fichiers du chunk
    """
    try:
        logger.info(f"[SCAN] Traitement chunk {chunk_id}/{total_chunks} pour: {directory}")

        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory does not exist: {directory}")

        # Récupérer tous les fichiers du répertoire
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if Path(file_path).suffix.lower() in {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}:
                    all_files.append(file_path)

        # Diviser en chunks
        chunk_size = len(all_files) // total_chunks
        start_idx = chunk_id * chunk_size
        end_idx = start_idx + chunk_size if chunk_id < total_chunks - 1 else len(all_files)

        chunk_files = all_files[start_idx:end_idx]

        logger.info(f"[SCAN] Chunk {chunk_id} terminé: {len(chunk_files)} fichiers")
        return chunk_files

    except Exception as e:
        logger.error(f"[SCAN] Erreur chunk {chunk_id}: {e}")
        return []
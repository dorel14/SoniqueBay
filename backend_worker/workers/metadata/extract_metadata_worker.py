"""Worker d'extraction de métadonnées - Pipeline optimisée pour Raspberry Pi

Responsabilités :
- Extraction des métadonnées de fichiers audio
- Traitement par lots avec ThreadPoolExecutor (max_workers=2)
- Envoi vers la phase de batching
- Publication de la progression

Architecture :
1. discovery → 2. extract_metadata → 3. batch_entities → 4. insert_batch
"""

import time
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event
from backend_worker.celery_app import celery
from backend_worker.workers.metadata.enrichment_worker import extract_single_file_metadata


@celery.task(name="metadata.extract_batch", queue="extract", bind=True)
def extract_metadata_batch(self, file_paths: List[str], batch_id: str = None):
    """Extraction des métadonnées de fichiers en parallèle.
    
    Optimisée pour Raspberry Pi : max_workers=2, timeout=60s, batches=25.
    
    Args:
        file_paths: Liste des chemins de fichiers à traiter
        batch_id: ID optionnel du batch pour tracking
        
    Returns:
        Liste des métadonnées extraites
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[EXTRACT] Démarrage extraction: {len(file_paths)} fichiers")
        logger.info(f"[EXTRACT] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[EXTRACT] Batch ID: {batch_id}")

        # Validation des chemins
        valid_paths = []
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_paths.append(file_path)
            else:
                logger.warning(f"[EXTRACT] Fichier invalide ignoré: {file_path}")

        if not valid_paths:
            logger.warning("[EXTRACT] Aucun fichier valide dans le batch")
            return {
                'task_id': task_id,
                'batch_id': batch_id,
                'files_processed': 0,
                'files_total': 0,
                'extraction_time': time.time() - start_time,
                'success': True
            }

        logger.info(f"[EXTRACT] Fichiers valides: {len(valid_paths)}/{len(file_paths)}")

        # Configuration ThreadPoolExecutor optimisée pour Raspberry Pi
        max_workers = 2  # Fixé à 2 pour Raspberry Pi (4 cœurs max)

        # Extraction massive avec ThreadPoolExecutor
        extracted_metadata = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les fichiers en parallèle
            future_to_path = {
                executor.submit(extract_single_file_metadata, file_path): file_path
                for file_path in valid_paths
            }

            # Collecter les résultats au fur et à mesure
            completed = 0
            for future in future_to_path:
                try:
                    metadata = future.result(timeout=60)  # 1 minute timeout par fichier
                    if metadata:
                        extracted_metadata.append(metadata)

                    completed += 1

                    # Update progression toutes les 50 fichiers
                    if completed % 50 == 0:
                        progress = min(90, (completed / len(valid_paths)) * 90)
                        self.update_state(state='PROGRESS', meta={
                            'current': completed,
                            'total': len(valid_paths),
                            'percent': progress,
                            'step': f'Extraction {completed}/{len(valid_paths)} fichiers'
                        })

                        # Publier la progression vers le frontend
                        publish_event("progress", {
                            "type": "progress",
                            "task_id": task_id,
                            "step": f'Extraction {completed}/{len(valid_paths)} fichiers',
                            "current": completed,
                            "total": len(valid_paths),
                            "percent": progress,
                            "batch_id": batch_id
                        }, channel="progress")

                except Exception as e:
                    logger.error(f"[EXTRACT] Erreur traitement fichier: {e}")
                    completed += 1

        # Métriques de performance
        total_time = time.time() - start_time
        files_per_second = len(extracted_metadata) / total_time if total_time > 0 else 0

        logger.info(f"[EXTRACT] Extraction terminée: {len(extracted_metadata)}/{len(valid_paths)} fichiers en {total_time:.2f}s")
        logger.info(f"[EXTRACT] Performance: {files_per_second:.2f} fichiers/seconde")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Extraction terminée",
            "current": len(extracted_metadata),
            "total": len(valid_paths),
            "percent": 100,
            "batch_id": batch_id,
            "files_processed": len(extracted_metadata),
            "files_total": len(valid_paths),
            "extraction_time": total_time,
            "files_per_second": files_per_second
        }, channel="progress")

        # Envoyer vers le batching si on a des résultats
        if extracted_metadata:
            celery.send_task(
                'batch.process_entities',
                args=[extracted_metadata],
                queue='batch',
                priority=5
            )

        return {
            'task_id': task_id,
            'batch_id': batch_id,
            'files_processed': len(extracted_metadata),
            'files_total': len(valid_paths),
            'extraction_time': total_time,
            'files_per_second': files_per_second,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[EXTRACT] Erreur batch après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur d'extraction: {str(e)}",
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise
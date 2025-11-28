"""
Worker Covers - Traitement des covers et images d'artistes

Responsabilités :
- Extraction des covers intégrées (embedded) dans les fichiers audio
- Extraction des images d'artistes depuis les dossiers
- Traitement et insertion des covers en base de données

Optimisations Raspberry Pi :
- max_workers = 2 pour extraction
- Timeouts réduits (300s par fichier)
- Batches plus petits (50 fichiers)
- Traitement différé pour éviter surcharge

Architecture :
1. Extraction : extract_embedded_covers_batch, extract_artist_images_batch
2. Traitement : process_track_covers_batch, process_artist_images_batch
3. Insertion : via API

Conventions :
- Logs via backend_worker.utils.logging
- Docstrings pour toutes fonctions
- Annotations de type
- Imports absolus
"""

import asyncio
import time
import os
from pathlib import Path
from typing import List, Dict, Any

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event


@celery.task(name='extract_embedded_covers_batch', queue='deferred', bind=True)
def extract_embedded_covers_batch(self, file_paths: List[str]):
    """
    Extrait les covers intégrées (embedded) pour un lot de fichiers.

    Optimisée pour Raspberry Pi : max_workers=2, timeout=300s.

    Args:
        file_paths: Liste des chemins de fichiers

    Returns:
        Résultats de l'extraction des covers embedded
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[COVERS] Démarrage extraction embedded: {len(file_paths)} fichiers")
        logger.info(f"[COVERS] Task ID: {task_id}")

        # Configuration pour extraction covers
        from backend_worker.services.music_scan import extract_embedded_covers, secure_open_file
        from mutagen import File
        from io import BytesIO

        covers_data = []

        # Traitement séquentiel pour Raspberry Pi (pas de parallélisation lourde)
        for file_path in file_paths:
            try:
                # Charger l'audio
                file_content = asyncio.run(secure_open_file(Path(file_path), 'rb', allowed_base_paths=[Path(file_path).parent]))
                if file_content is None:
                    continue

                file_buffer = BytesIO(file_content)
                audio = File(file_buffer, easy=False)

                if audio is None:
                    continue

                # Extraire covers embedded
                cover_info = asyncio.run(extract_embedded_covers(audio, file_path, allowed_base_paths=[Path(file_path).parent]))
                if cover_info and "error" not in cover_info:
                    covers_data.append(cover_info)

            except Exception as e:
                logger.error(f"[COVERS] Erreur pour {file_path}: {e}")

        # Envoyer vers traitement final des covers
        if covers_data:
            celery.send_task(
                'process_track_covers_batch',
                args=[covers_data],
                queue='deferred',
                priority=1
            )

        total_time = time.time() - start_time
        logger.info(f"[COVERS] Extraction embedded terminée: {len(covers_data)}/{len(file_paths)} en {total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Extraction covers terminée",
            "current": len(covers_data),
            "total": len(file_paths),
            "percent": 100,
            "covers_extracted": len(covers_data),
            "extraction_time": total_time
        }, channel="progress")

        return {
            'task_id': task_id,
            'files_processed': len(covers_data),
            'files_total': len(file_paths),
            'extraction_time': total_time,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[COVERS] Erreur batch embedded: {e}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur extraction covers: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        return {'error': str(e), 'files_total': len(file_paths)}


@celery.task(name='extract_artist_images_batch', queue='deferred', bind=True)
def extract_artist_images_batch(self, file_paths: List[str]):
    """
    Extrait les images d'artistes (dossiers) pour un lot de fichiers.

    Optimisée pour Raspberry Pi : traitement séquentiel.

    Args:
        file_paths: Liste des chemins de fichiers

    Returns:
        Résultats de l'extraction des artist images
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[ARTIST_IMAGES] Démarrage extraction: {len(file_paths)} fichiers")
        logger.info(f"[ARTIST_IMAGES] Task ID: {task_id}")

        # Configuration pour extraction artist images
        from backend_worker.services.music_scan import extract_artist_images

        artist_data = []

        # Traitement séquentiel pour Raspberry Pi
        for file_path in file_paths:
            try:
                # Extraire artist images (pas besoin d'audio)
                artist_info = asyncio.run(extract_artist_images(file_path, allowed_base_paths=[Path(file_path).parent]))
                if artist_info and "error" not in artist_info:
                    artist_data.append(artist_info)

            except Exception as e:
                logger.error(f"[ARTIST_IMAGES] Erreur pour {file_path}: {e}")

        # Envoyer vers traitement final des artist images
        if artist_data:
            celery.send_task(
                'process_artist_images_batch',
                args=[artist_data],
                queue='deferred',
                priority=2  # Priorité plus basse
            )

        total_time = time.time() - start_time
        logger.info(f"[ARTIST_IMAGES] Extraction terminée: {len(artist_data)}/{len(file_paths)} en {total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Extraction artist images terminée",
            "current": len(artist_data),
            "total": len(file_paths),
            "percent": 100,
            "images_extracted": len(artist_data),
            "extraction_time": total_time
        }, channel="progress")

        return {
            'task_id': task_id,
            'files_processed': len(artist_data),
            'files_total': len(file_paths),
            'extraction_time': total_time,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[ARTIST_IMAGES] Erreur batch: {e}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur extraction artist images: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        return {'error': str(e), 'files_total': len(file_paths)}


@celery.task(name='process_track_covers_batch', queue='deferred', bind=True)
def process_track_covers_batch(self, covers_data: List[Dict[str, Any]]):
    """
    Traite et insère un lot de covers de pistes.

    Args:
        covers_data: Liste des données de covers

    Returns:
        Résultats du traitement
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[PROCESS_COVERS] Traitement de {len(covers_data)} covers")
        logger.info(f"[PROCESS_COVERS] Task ID: {task_id}")

        # Utiliser httpx pour insertion via API
        import httpx

        with httpx.Client(
            base_url=os.getenv("API_URL", "http://api:8001"),
            timeout=httpx.Timeout(120.0),  # 2 minutes
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        ) as client:

            processed_covers = 0

            # Traiter chaque cover
            for cover_info in covers_data:
                try:
                    # Insérer la cover via API
                    response = client.post(
                        "/api/covers/",
                        json=cover_info,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code in (200, 201):
                        processed_covers += 1
                        logger.debug(f"[PROCESS_COVERS] Cover insérée: {cover_info.get('path', 'unknown')}")
                    else:
                        logger.error(f"[PROCESS_COVERS] Erreur insertion cover: {response.status_code} - {response.text}")

                except Exception as e:
                    logger.error(f"[PROCESS_COVERS] Exception cover: {e}")

        total_time = time.time() - start_time
        logger.info(f"[PROCESS_COVERS] Traitement terminé: {processed_covers}/{len(covers_data)} en {total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Traitement covers terminé",
            "current": processed_covers,
            "total": len(covers_data),
            "percent": 100,
            "covers_processed": processed_covers,
            "processing_time": total_time
        }, channel="progress")

        return {
            'task_id': task_id,
            'covers_processed': processed_covers,
            'covers_total': len(covers_data),
            'processing_time': total_time,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[PROCESS_COVERS] Erreur traitement: {e}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur traitement covers: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        return {'error': str(e), 'covers_total': len(covers_data)}


@celery.task(name='process_artist_images_batch', queue='deferred', bind=True)
def process_artist_images_batch(self, artist_data: List[Dict[str, Any]]):
    """
    Traite et insère un lot d'images d'artistes.

    Args:
        artist_data: Liste des données d'images d'artistes

    Returns:
        Résultats du traitement
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[PROCESS_ARTIST_IMAGES] Traitement de {len(artist_data)} images d'artistes")
        logger.info(f"[PROCESS_ARTIST_IMAGES] Task ID: {task_id}")

        # Utiliser httpx pour insertion via API
        import httpx

        with httpx.Client(
            base_url=os.getenv("API_URL", "http://api:8001"),
            timeout=httpx.Timeout(120.0),  # 2 minutes
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        ) as client:

            processed_images = 0

            # Traiter chaque image d'artiste
            for artist_info in artist_data:
                try:
                    # Insérer l'image d'artiste via API
                    response = client.post(
                        "/api/artists/images/",
                        json=artist_info,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code in (200, 201):
                        processed_images += 1
                        logger.debug(f"[PROCESS_ARTIST_IMAGES] Image insérée: {artist_info.get('artist_path', 'unknown')}")
                    else:
                        logger.error(f"[PROCESS_ARTIST_IMAGES] Erreur insertion image: {response.status_code} - {response.text}")

                except Exception as e:
                    logger.error(f"[PROCESS_ARTIST_IMAGES] Exception image: {e}")

        total_time = time.time() - start_time
        logger.info(f"[PROCESS_ARTIST_IMAGES] Traitement terminé: {processed_images}/{len(artist_data)} en {total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Traitement artist images terminé",
            "current": processed_images,
            "total": len(artist_data),
            "percent": 100,
            "images_processed": processed_images,
            "processing_time": total_time
        }, channel="progress")

        return {
            'task_id': task_id,
            'images_processed': processed_images,
            'images_total': len(artist_data),
            'processing_time': total_time,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[PROCESS_ARTIST_IMAGES] Erreur traitement: {e}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur traitement artist images: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        return {'error': str(e), 'images_total': len(artist_data)}
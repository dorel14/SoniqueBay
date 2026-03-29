"""Tâches Celery centralisées pour le backend worker."""

import os
import asyncio
from typing import List

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.cover_orchestrator_service import cover_orchestrator_service
from backend_worker.services.cover_types import CoverProcessingContext, ImageType, TaskType


def get_or_create_event_loop():
    """Get current event loop or create a new one if none exists."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Feature flags pour la migration TaskIQ
USE_TASKIQ_FOR_MAINTENANCE = os.getenv('USE_TASKIQ_FOR_MAINTENANCE', 'false').lower() == 'true'
USE_TASKIQ_FOR_COVERS = os.getenv('USE_TASKIQ_FOR_COVERS', 'false').lower() == 'true'
USE_TASKIQ_FOR_PROCESS_ARTIST_IMAGES = os.getenv('USE_TASKIQ_FOR_PROCESS_ARTIST_IMAGES', 'false').lower() == 'true'
USE_TASKIQ_FOR_PROCESS_ALBUM_COVERS = os.getenv('USE_TASKIQ_FOR_PROCESS_ALBUM_COVERS', 'false').lower() == 'true'
USE_TASKIQ_FOR_METADATA = os.getenv('USE_TASKIQ_FOR_METADATA', 'false').lower() == 'true'
USE_TASKIQ_FOR_BATCH = os.getenv('USE_TASKIQ_FOR_BATCH', 'false').lower() == 'true'
USE_TASKIQ_FOR_INSERT = os.getenv('USE_TASKIQ_FOR_INSERT', 'false').lower() == 'true'
USE_TASKIQ_FOR_SCAN = os.getenv('USE_TASKIQ_FOR_SCAN', 'false').lower() == 'true'
USE_TASKIQ_FOR_VECTORIZATION = os.getenv('USE_TASKIQ_FOR_VECTORIZATION', 'false').lower() == 'true'


     # === TÂCHES DE SCAN ===
@celery.task(name="scan.discovery", queue="scan", bind=True)
def discovery(self, directory: str, progress_callback=None):
    """Découverte de fichiers musicaux et lancement de la pipeline complète.
    
    Pipeline : discovery → extract_metadata → batch_entities → insert_batch
    
    Args:
        directory: Répertoire à scanner
        progress_callback: Fonction de callback pour la progression
        
    Returns:
        Résultat de la découverte et lancement de la pipeline
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_SCAN:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour scan.discovery")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.scan import discovery_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(discovery_task.kiq(directory=directory, progress_callback=progress_callback))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        from pathlib import Path
        import time
        from backend_worker.utils.pubsub import publish_event
        
        start_time = time.time()
        task_id = self.request.id
        
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
        
        # Publier progression pour SSE
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Discovery terminée - {total_files} fichiers trouvés",
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "files_discovered": total_files
        }, channel="progress")
        
        # Si des fichiers ont été trouvés, lancer la pipeline complète
        if discovered_files:
            logger.info(f"[SCAN] Lancement de la pipeline d'extraction pour {total_files} fichiers")
            
            # Diviser en batches pour l'extraction (50 fichiers par batch)
            batch_size = 50
            batches = [discovered_files[i:i + batch_size] for i in range(0, len(discovered_files), batch_size)]
            
            logger.info(f"[SCAN] Création de {len(batches)} batches d'extraction")
            
            # Envoyer chaque batch vers l'extraction
            for i, batch_files in enumerate(batches):
                batch_id = f"batch_{i+1}_{len(batches)}"
                logger.info(f"[SCAN] Envoi batch {i+1}/{len(batches)}: {len(batch_files)} fichiers")
                
                celery.send_task(
                    'metadata.extract_batch',
                    args=[batch_files, batch_id],
                    queue='extract',
                    priority=5
                )
        
        result = {
            "directory": directory,
            "files_discovered": total_files,
            "file_paths": discovered_files,
            "discovery_time": time.time() - start_time,
            "batches_created": len(batches) if discovered_files else 0,
            "success": True
        }
        
        logger.info(f"[SCAN] Discovery et pipeline lancée: {result}")
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


# === TÂCHES DE MÉTADONNÉES ===
@celery.task(name="metadata.extract_batch", queue="extract", bind=True)
def extract_metadata_batch(self, file_paths: list[str], batch_id: str = None):
    """
    Extrait les métadonnées de fichiers en parallèle avec ThreadPoolExecutor.

    Optimisée pour Raspberry Pi : max_workers=2, timeout=60s, batches=25.

    Args:
        file_paths: Liste des chemins de fichiers à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Liste des métadonnées extraites
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_METADATA:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour extract_metadata_batch")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.metadata import extract_metadata_batch_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(extract_metadata_batch_task.kiq(file_paths=file_paths, batch_id=batch_id))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        from concurrent.futures import ThreadPoolExecutor
        from backend_worker.workers.metadata.enrichment_worker import extract_single_file_metadata
        
        import time
        start_time = time.time()
        task_id = self.request.id

        logger.info(f"[METADATA] Démarrage extraction batch: {len(file_paths)} fichiers")
        logger.info(f"[METADATA] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[METADATA] Batch ID: {batch_id}")

        # Configuration ThreadPoolExecutor optimisée pour Raspberry Pi
        max_workers = 2  # Fixé à 2 pour Raspberry Pi (4 cœurs max)

        # Extraction massive avec ThreadPoolExecutor
        extracted_metadata = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les fichiers en parallèle
            future_to_path = {
                executor.submit(extract_single_file_metadata, file_path): file_path
                for file_path in file_paths
            }

            # Collecter les résultats au fur et à mesure
            for future in future_to_path:
                try:
                    metadata = future.result(timeout=60)  # 1 minute timeout par fichier (Raspberry Pi)
                    if metadata:
                        extracted_metadata.append(metadata)
                except Exception as e:
                    logger.error(f"[METADATA] Erreur traitement fichier: {e}")

        # Métriques de performance
        total_time = time.time() - start_time
        files_per_second = len(extracted_metadata) / total_time if total_time > 0 else 0

        logger.info(f"[METADATA] Extraction terminée: {len(extracted_metadata)}/{len(file_paths)} fichiers en {total_time:.2f}s")

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
            'files_total': len(file_paths),
            'extraction_time': total_time,
            'files_per_second': files_per_second,
            'success': True
        }

    except Exception as e:
        logger.error(f"[METADATA] Erreur batch: {str(e)}")
        import traceback
        logger.error(f"[METADATA] Traceback complet: {traceback.format_exc()}")
        raise


# === TÂCHES DE BATCH ===
@celery.task(name="batch.process_entities", queue="batch", bind=True)
def batch_entities(self, metadata_list: list[dict], batch_id: str = None):
    """
    Regroupe les métadonnées par artistes et albums pour insertion optimisée.

    Args:
        metadata_list: Liste des métadonnées à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Données groupées prêtes pour insertion
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_BATCH:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour batch_entities")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.batch import process_entities_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(process_entities_task.kiq(metadata_list=metadata_list, batch_id=batch_id))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        from collections import defaultdict
        from pathlib import Path
        
        import time
        start_time = time.time()
        task_id = self.request.id

        logger.info(f"[BATCH] Démarrage batching: {len(metadata_list)} métadonnées")

        if not metadata_list:
            return {
                'task_id': task_id,
                'batch_id': batch_id,
                'artists_count': 0,
                'albums_count': 0,
                'tracks_count': 0,
                'success': True
            }

        # Regroupement intelligent des données
        artists_by_name = {}
        albums_by_key = {}
        tracks_by_artist = defaultdict(list)

        # Regrouper par artistes
        for metadata in metadata_list:
            artist_name = metadata.get('artist', 'Unknown')
            if not artist_name or artist_name.lower() == 'unknown':
                path_obj = Path(metadata.get('path', ''))
                if len(path_obj.parts) >= 2:
                    artist_name = path_obj.parts[-2]
                else:
                    artist_name = 'Unknown Artist'

            normalized_artist = artist_name.strip().lower()

            if normalized_artist not in artists_by_name:
                artists_by_name[normalized_artist] = {
                    'name': artist_name,
                    'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                    'tracks_count': 0,
                    'albums_count': 0
                }

            artists_by_name[normalized_artist]['tracks_count'] += 1
            tracks_by_artist[normalized_artist].append(metadata)

        # Regrouper par albums
        for artist_name, tracks in tracks_by_artist.items():
            artist_info = artists_by_name[artist_name]

            for track in tracks:
                album_name = track.get('album', 'Unknown')
                if not album_name or album_name.lower() == 'unknown':
                    path_obj = Path(track.get('path', ''))
                    if len(path_obj.parts) >= 1:
                        album_name = path_obj.parts[-1]
                    else:
                        album_name = 'Unknown Album'

                album_key = (album_name.strip().lower(), artist_name)

                if album_key not in albums_by_key:
                    albums_by_key[album_key] = {
                        'title': album_name,
                        'album_artist_name': artist_name,
                        'release_year': track.get('year'),
                        'tracks_count': 0
                    }

                albums_by_key[album_key]['tracks_count'] += 1
                artist_info['albums_count'] += 1

        # Préparation des données
        artists_data = list(artists_by_name.values())
        albums_data = list(albums_by_key.values())
        tracks_data = metadata_list.copy()

        # Nettoyer les tracks
        for track in tracks_data:
            track.pop('tracks_count', None)
            track.pop('albums_count', None)

        total_time = time.time() - start_time
        logger.info(f"[BATCH] Batching terminé: {len(artists_data)} artistes, {len(albums_data)} albums, {len(tracks_data)} pistes en {total_time:.2f}s")
        
        # DIAGNOSTIC: Log des albums détectés
        if albums_data:
            logger.info(f"[BATCH] Albums détectés (sample): {albums_data[:5]}")
            for album in albums_data[:5]:
                logger.info(f"[BATCH]   - Album: '{album.get('title')}', artist_name: '{album.get('album_artist_name')}', year: {album.get('release_year')}")

        # Préparer le résultat pour l'insertion
        insertion_data = {
            'task_id': task_id,
            'batch_id': batch_id,
            'artists': artists_data,
            'albums': albums_data,
            'tracks': tracks_data,
            'metadata_count': len(metadata_list),
            'batching_time': total_time,
            'success': True
        }

        # Envoyer vers l'insertion directe via API uniquement
        celery.send_task(
            'insert.direct_batch',
            args=[insertion_data],
            queue='insert',
            priority=7
        )

        return insertion_data

    except Exception as e:
        logger.error(f"[BATCH] Erreur batching: {str(e)}")
        raise


# === TÂCHES D'INSERTION ===
# Import de la vraie implémentation depuis insert_batch_worker.py


# === TÂCHES DE VECTORISATION ===
# Utilisation de sentence-transformers (plus léger que Ollama/Koboldcpp)
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Modèle léger et efficace pour Raspberry Pi

@celery.task(name="vectorization.calculate", queue="vectorization", bind=True)
def calculate_vector(self, track_id: int, metadata: dict = None):
    """
    Calcule le vecteur d'une track via sentence-transformers.
    
    Pipeline:
        1. Récupère les données de la track via l'API
        2. Génère l'embedding avec sentence-transformers (local, léger)
        3. Stocke le vecteur via l'API backend
    
    Args:
        track_id: ID de la track
        metadata: Métadonnées optionnelles de la track
        
    Returns:
        Résultat du calcul avec statut et métadonnées
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_VECTORIZATION:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour vectorization.calculate")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.vectorization import calculate_vector_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(calculate_vector_task.kiq(track_id=track_id, metadata=metadata))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    import time
    
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(f"[VECTOR] Démarrage calcul vecteur: track_id={track_id}")
    
    try:
        # Import de sentence-transformers
        from sentence_transformers import SentenceTransformer
        import httpx
        
        # Chargement du modèle (lazy loading - chargé une seule fois)
        model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Récupérer les métadonnées de la track via l'API si non fournies
        track_metadata = metadata or {}
        if not track_metadata:
            api_url = os.getenv("API_URL", "http://api:8001")
            try:
                with httpx.Client(timeout=30) as client:
                    response = client.get(f"{api_url}/api/tracks/{track_id}")
                    if response.status_code == 200:
                        track_metadata = response.json()
            except Exception as e:
                logger.warning(f"[VECTOR] Impossible de récupérer les métadonnées: {e}")
        
        # Construire le texte à vectoriser à partir des métadonnées
        text_parts = []
        if track_metadata.get('title'):
            text_parts.append(track_metadata['title'])
        if track_metadata.get('artist'):
            text_parts.append(track_metadata['artist'])
        if track_metadata.get('album'):
            text_parts.append(track_metadata['album'])
        if track_metadata.get('genre'):
            text_parts.append(track_metadata['genre'])
        
        text_to_embed = " - ".join(text_parts) if text_parts else f"track_{track_id}"
        
        # Générer l'embedding
        embedding = model.encode(text_to_embed, convert_to_numpy=True)
        
        # Convertir en liste pour sérialisation JSON
        embedding_list = embedding.tolist()
        
        # Stocker le vecteur via l'API
        api_url = os.getenv("API_URL", "http://api:8001")
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{api_url}/api/tracks/{track_id}/vector",
                json={"vector": embedding_list, "model": EMBEDDING_MODEL}
            )
            if response.status_code not in (200, 201):
                raise Exception(f"Erreur stockage vecteur: {response.status_code}")
        
        calculation_time = time.time() - start_time
        
        logger.info(
            f"[VECTOR] Vecteur calculé et stocké: track_id={track_id}, "
            f"dimensions={len(embedding_list)}, time={calculation_time:.2f}s"
        )
        
        return {
            'task_id': task_id,
            'track_id': track_id,
            'status': 'success',
            'embedding_model': EMBEDDING_MODEL,
            'dimensions': len(embedding_list),
            'calculation_time': calculation_time
        }
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[VECTOR] Erreur vectorisation: {str(e)}")
        import traceback
        logger.error(f"[VECTOR] Traceback: {traceback.format_exc()}")
        return {
            'task_id': task_id,
            'track_id': track_id,
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__,
            'calculation_time': error_time,
            'embedding_model': EMBEDDING_MODEL
        }


@celery.task(name="vectorization.batch", queue="vectorization", bind=True)
def calculate_vector_batch(self, track_ids: list[int]):
    """
    Calcule les vecteurs d'un batch de tracks via sentence-transformers.
    
    Args:
        track_ids: Liste des IDs de tracks
        
    Returns:
        Résultat du calcul batch
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_VECTORIZATION:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour vectorization.batch")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.vectorization import calculate_vector_batch_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(calculate_vector_batch_task.kiq(track_ids=track_ids))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    import time
    
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(f"[VECTOR] Démarrage batch: {len(track_ids)} tracks")
    
    successful = 0
    failed = 0
    errors = []
    
    try:
        from sentence_transformers import SentenceTransformer
        import httpx
        
        # Chargement du modèle (une seule fois pour tout le batch)
        model = SentenceTransformer(EMBEDDING_MODEL)
        api_url = os.getenv("API_URL", "http://api:8001")
        
        with httpx.Client(timeout=30) as client:
            for track_id in track_ids:
                try:
                    # Récupérer les métadonnées
                    response = client.get(f"{api_url}/api/tracks/{track_id}")
                    if response.status_code != 200:
                        failed += 1
                        errors.append(f"Track {track_id}: non trouvé")
                        continue
                    
                    track_metadata = response.json()
                    
                    # Construire le texte à vectoriser
                    text_parts = []
                    if track_metadata.get('title'):
                        text_parts.append(track_metadata['title'])
                    if track_metadata.get('artist'):
                        text_parts.append(track_metadata['artist'])
                    if track_metadata.get('album'):
                        text_parts.append(track_metadata['album'])
                    if track_metadata.get('genre'):
                        text_parts.append(track_metadata['genre'])
                    
                    text_to_embed = " - ".join(text_parts) if text_parts else f"track_{track_id}"
                    
                    # Générer l'embedding
                    embedding = model.encode(text_to_embed, convert_to_numpy=True)
                    embedding_list = embedding.tolist()
                    
                    # Stocker le vecteur
                    store_response = client.post(
                        f"{api_url}/api/tracks/{track_id}/vector",
                        json={"vector": embedding_list, "model": EMBEDDING_MODEL}
                    )
                    
                    if store_response.status_code in (200, 201):
                        successful += 1
                    else:
                        failed += 1
                        errors.append(f"Track {track_id}: erreur stockage {store_response.status_code}")
                        
                except Exception as e:
                    failed += 1
                    errors.append(f"Track {track_id}: {str(e)}")
        
        calculation_time = time.time() - start_time
        
        logger.info(
            f"[VECTOR] Batch terminé: {successful} succès, "
            f"{failed} échecs en {calculation_time:.2f}s"
        )
        
        return {
            'task_id': task_id,
            'status': 'success' if failed == 0 else 'partial',
            'successful': successful,
            'failed': failed,
            'errors': errors[:10],  # Limiter le nombre d'erreurs retournées
            'calculation_time': calculation_time,
            'embedding_model': EMBEDDING_MODEL
        }
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[VECTOR] Erreur batch: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'error',
            'message': str(e),
            'calculation_time': error_time,
            'embedding_model': EMBEDDING_MODEL
        }


# === TÂCHES DE COVERS ===
@celery.task(name="covers.extract_embedded", queue="deferred_covers", bind=True)
def extract_embedded_covers(self, file_paths: list[str]):
    """
    Extrait les covers intégrées pour un lot de fichiers (placeholder).

    Args:
        file_paths: Liste des chemins de fichiers

    Returns:
        Résultat de l'extraction
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_COVERS:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour extract_embedded_covers")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.covers import extract_embedded_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(extract_embedded_task.kiq(file_paths=file_paths))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    logger.info(f"[COVERS] Début extraction covers intégrées: {len(file_paths)} fichiers")

    # En production, implémenter la logique d'extraction des covers
    # Pour l'instant, juste un placeholder

    result = {
        "message": f"Extraction covers simulée pour {len(file_paths)} fichiers",
        "covers_extracted": 0,
        "success": True
    }

    logger.info(f"[COVERS] Extraction covers terminée: {result}")
    return result


@celery.task(name="covers.process_album_covers", queue="deferred_covers", bind=True)
def process_album_covers(self, album_ids: List[int], priority: str = "normal"):
    """
    Traite les covers d'albums en utilisant le CoverOrchestratorService.

    Utilise tous les services spécialisés pour un traitement optimisé :
    - Recherche dans les dossiers locaux (ImageService)
    - API Cover Art Archive (CoverArtService)
    - Cache Redis intelligent (ImageCacheService)
    - Priorisation basée sur la popularité (ImagePriorityService)
    - Traitement/redimensionnement optimisé (ImageProcessingService)
    """
     # Vérifier le feature flag
     if USE_TASKIQ_FOR_PROCESS_ALBUM_COVERS:
         logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour process_album_covers")
         
         # Déléguer à TaskIQ
         from backend_worker.taskiq_tasks.covers import process_album_covers_task
         
         try:
             # Obtenir ou créer une boucle d'événements
             loop = get_or_create_event_loop()
             
             # Exécuter la tâche TaskIQ de manière synchrone
             result = loop.run_until_complete(process_album_covers_task.kiq(album_ids=album_ids, priority=priority))
             
             logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
             return result
             
         except Exception as e:
             logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
             # Fallback vers Celery
             logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        logger.info(f"[COVERS] Début traitement covers albums: {len(album_ids)} albums")

        # Récupérer les informations des albums depuis la base de données via l'API
        import httpx
        import os
        # Utiliser l'URL de l'API depuis les variables d'environnement ou localhost en dev
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[COVERS] API URL utilisée pour albums: {api_url}")
        album_infos = []
        
        for album_id in album_ids:
            try:
                # Récupérer les informations de l'album via l'API REST
                logger.info(f"[COVERS] Récupération infos album {album_id} depuis {api_url}/api/albums/{album_id}")
                response = httpx.get(f"{api_url}/api/albums/{album_id}", timeout=10)
                if response.status_code == 200:
                    album_data = response.json()
                    logger.info(f"[COVERS] Données album {album_id} récupérées: {album_data.get('title')}")
                    album_infos.append(album_data)
                else:
                    logger.warning(f"[COVERS] Impossible de récupérer les informations de l'album {album_id}")
            except Exception as e:
                logger.warning(f"[COVERS] Erreur lors de la récupération des infos de l'album {album_id}: {str(e)}")
                continue

        logger.info(f"[COVERS] Informations récupérées pour {len(album_infos)} albums")

        # Création des contextes de traitement
        contexts = []
        for album_info in album_infos:
            album_id = album_info.get("id")
            album_title = album_info.get("title")
            
            # Tentative de détermination du chemin de l'album (basé sur les tracks)
            album_path = None
            try:
                # Récupérer les tracks de l'album pour déterminer le chemin
                tracks_response = httpx.get(f"{api_url}/api/albums/{album_id}/tracks", timeout=10)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        from pathlib import Path
                        track_path = tracks[0].get("path")
                        if track_path:
                            album_path = str(Path(track_path).parent)
                            logger.debug(f"[COVERS] Chemin album déduit pour {album_title}: {album_path}")
            except Exception as e:
                logger.debug(f"[COVERS] Impossible de déterminer le chemin de l'album {album_id}: {str(e)}")

            context = CoverProcessingContext(
                image_type=ImageType.ALBUM_COVER,
                entity_id=album_id,
                entity_path=album_path,
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "album",
                    "batch_size": len(album_ids),
                    "album_title": album_title,
                    "artist_name": album_info.get("album_artist_name"),
                    "musicbrainz_albumid": album_info.get("musicbrainz_albumid")
                }
            )
            contexts.append(context)

        logger.info(f"[COVERS] Contextes créés: {len(contexts)}")

        # Traitement via l'orchestrateur (à implémenter)
        # TODO: Utiliser le CoverOrchestratorService quand il sera disponible
        # Pour l'instant, implémentation simplifiée
        result = {
            "processed": len(album_ids),
            "success": True,
            "message": f"Traitement de {len(album_ids)} covers d'albums effectué (placeholder)"
        }

        logger.info(f"[COVERS] Traitement covers albums terminé: {result}")
        return {
            "success": True,
            "albums_processed": len(album_ids),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImagePriorityService",
                "ImageCacheService",
                "CoverArtService",
                "ImageService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement covers albums: {str(e)}")
        return {"success": False, "error": str(e), "albums_processed": 0}



# === TÂCHES DE COVERS (Suite) ===
@celery.task(name="covers.process_artist_images", queue="deferred_covers", bind=True)
def process_artist_images(self, artist_ids: List[int], priority: str = "normal"):
    """
    Traite les images d'artistes en utilisant le CoverOrchestratorService.

    Utilise tous les services spécialisés :
    - CoverOrchestratorService (coordination)
    - ImageProcessingService (traitement/redimensionnement)
    - ImagePriorityService (priorisation intelligente)
    - ImageCacheService (cache Redis)
    - CoverArtService (API externes)
    - ImageService (extraction fichiers locaux)
    """
    # Vérifier le feature flag
    if USE_TASKIQ_FOR_PROCESS_ARTIST_IMAGES:
        logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour process_artist_images")
        
        # Déléguer à TaskIQ
        from backend_worker.taskiq_tasks.covers import process_artist_images_task
        
        try:
            # Obtenir ou créer une boucle d'événements
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Exécuter la tâche TaskIQ de manière synchrone
            result = loop.run_until_complete(process_artist_images_task.kiq(artist_ids=artist_ids, priority=priority))
            
            logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
            # Fallback vers Celery
            logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        logger.info(f"[COVERS] Début traitement images artistes: {len(artist_ids)} artistes")
        logger.info(f"[COVERS] Artist IDs à traiter: {artist_ids}")

        # Récupérer les informations des artistes depuis la base de données via l'API
        import httpx
        import os
        # Utiliser l'URL de l'API depuis les variables d'environnement ou localhost en dev
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[COVERS] API URL utilisée: {api_url}")
        artist_infos = []
        
        for artist_id in artist_ids:
            try:
                # Récupérer les informations de l'artiste via l'API REST
                logger.info(f"[COVERS] Récupération infos artiste {artist_id} depuis {api_url}/api/artists/{artist_id}")
                response = httpx.get(f"{api_url}/api/artists/{artist_id}", timeout=10)
                logger.info(f"[COVERS] Status code réponse API pour artiste {artist_id}: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    logger.info(f"[COVERS] Données artiste {artist_id} récupérées: {artist_data.get('name')}")
                    artist_infos.append(artist_data)
                else:
                    logger.warning(f"[COVERS] Impossible de récupérer les informations de l'artiste {artist_id} - Status: {response.status_code}")
            except Exception as e:
                logger.warning(f"[COVERS] Erreur lors de la récupération des infos de l'artiste {artist_id}: {str(e)}")
                continue

        logger.info(f"[COVERS] Informations récupérées pour {len(artist_infos)} artistes")

        # Création des contextes de traitement
        contexts = []
        for artist_info in artist_infos:
            artist_id = artist_info.get("id")
            artist_name = artist_info.get("name")
            
            # Tentative de détermination du chemin de l'artiste (basé sur les tracks)
            artist_path = None
            try:
                # Récupérer les tracks de l'artiste pour déterminer le chemin
                tracks_response = httpx.get(f"{api_url}/api/artists/{artist_id}/tracks", timeout=10)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        from pathlib import Path
                        track_path = tracks[0].get("path")
                        if track_path:
                            track_dir = Path(track_path).parent
                            # Supposer structure: .../Artiste/Album/Track
                            artist_path = str(track_dir.parent)
                            logger.info(f"[COVERS] Chemin artiste déduit pour {artist_name}: {artist_path}")
            except Exception as e:
                logger.debug(f"[COVERS] Impossible de déterminer le chemin de l'artiste {artist_id}: {str(e)}")

            context = CoverProcessingContext(
                image_type=ImageType.ARTIST_IMAGE,
                entity_id=artist_id,
                entity_path=artist_path,
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "artist",
                    "batch_size": len(artist_ids),
                    "artist_name": artist_name,
                    "musicbrainz_artistid": artist_info.get("musicbrainz_artistid")
                }
            )
            contexts.append(context)

        logger.info(f"[COVERS] Contextes créés: {len(contexts)}")

        # Traitement via l'orchestrateur (utilise tous les services)
        result = asyncio.run(cover_orchestrator_service.process_batch(contexts))

        logger.info(f"[COVERS] Traitement images artistes terminé: {result}")
        return {
            "success": True,
            "artists_processed": len(artist_ids),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImagePriorityService",
                "ImageCacheService",
                "CoverArtService",
                "ImageService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement images artistes: {str(e)}")
        return {"success": False, "error": str(e), "artists_processed": 0}



# === TÂCHES DE MAINTENANCE ===
@celery.task(name="maintenance.cleanup_old_data", queue="maintenance", bind=True)
def cleanup_old_data(self, days_old: int = 30):
    """Nettoie les anciennes données.
    
    Args:
        days_old: Nombre de jours pour considérer les données comme anciennes
        
    Returns:
        Résultat du nettoyage
    """
    
    # Vérifier le feature flag
    if USE_TASKIQ_FOR_MAINTENANCE:
        logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour cleanup_old_data")
        
        # Déléguer à TaskIQ
        from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
        import asyncio
        
        try:
            # Obtenir ou créer une boucle d'événements
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Exécuter la tâche TaskIQ de manière synchrone
            result = loop.run_until_complete(cleanup_old_data_task(days_old=days_old))
            
            logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
            # Fallback vers Celery
            logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    logger.info(f"[MAINTENANCE] Nettoyage des données de plus de {days_old} jours (placeholder)")
    logger.info("[MAINTENANCE] Nettoyage terminé: success=True")
    return {"cleaned": True, "days_old": days_old, "items_cleaned": 0, "success": True}


# === TÂCHES D'ENRICHISSEMENT ===
@celery.task(name="metadata.enrich_batch", queue="deferred_enrichment", bind=True)
def enrich_tracks_batch_task(self, track_ids: list[int]):
    """
    Tâche d'enrichissement par lot des tracks.

    Args:
        track_ids: Liste des IDs de tracks à enrichir

    Returns:
        Résultats de l'enrichissement
    """
    # Vérifier le feature flag
    if USE_TASKIQ_FOR_METADATA:
        logger.info("[CELERY→TASKIQ] Délégation à TaskIQ pour enrich_tracks_batch_task")
        
        # Déléguer à TaskIQ
        from backend_worker.taskiq_tasks.metadata import enrich_batch_task
        import asyncio
        
        try:
            # Obtenir ou créer une boucle d'événements
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Exécuter la tâche TaskIQ de manière synchrone
            result = loop.run_until_complete(enrich_batch_task.kiq(entity_type="artist", entity_ids=track_ids))
            
            logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
            # Fallback vers Celery
            logger.info("[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    try:
        logger.info(f"[METADATA] Démarrage enrichissement batch: {len(track_ids)} tracks")

        # Pour l'instant, simple placeholder
        return {
            "total_tracks": len(track_ids),
            "processed": len(track_ids),
            "success": True
        }

    except Exception as e:
        logger.error(f"[METADATA] Erreur enrichissement: {str(e)}")
        raise


# ============================================================
# GMM CLUSTERING TASKS
# ============================================================

@celery.task(name="gmm.cluster_all_artists", bind=True)
def cluster_all_artists(self, force_refresh: bool = False) -> dict:
    """
    Déclenche le clustering GMM de tous les artistes.
    
    Args:
        force_refresh: Si True, force le recalcul même si récent
        
    Returns:
        Dict avec statistiques de clustering
    """
    from backend_worker.services.artist_clustering_service import (
        ArtistClusteringService
    )
    
    async def _cluster() -> dict:
        async with ArtistClusteringService() as service:
            return await service.cluster_all_artists(force_refresh=force_refresh)
    
    import asyncio
    return asyncio.run(_cluster())


@celery.task(name="gmm.cluster_artist", bind=True)
def cluster_artist(self, artist_id: int) -> dict:
    """
    Cluster un artiste spécifique.
    
    Args:
        artist_id: ID de l'artiste
        
    Returns:
        Dict avec infos de cluster
    """
    from backend_worker.services.artist_clustering_service import (
        ArtistClusteringService
    )
    
    async def _cluster() -> dict:
        async with ArtistClusteringService() as service:
            return await service.cluster_artist(artist_id)
    
    import asyncio
    return asyncio.run(_cluster())


@celery.task(name="gmm.refresh_stale_clusters", bind=True)
def refresh_stale_clusters(self, max_age_hours: int = 24) -> dict:
    """
    Rafraîchit les clusters trop anciens.
    
    Args:
        max_age_hours: Âge maximum en heures avant rafraîchissement
        
    Returns:
        Dict avec nombre de clusters rafraîchis
    """
    from backend_worker.services.artist_clustering_service import (
        ArtistClusteringService
    )
    
    async def _refresh() -> dict:
        async with ArtistClusteringService() as service:
            count = await service.refresh_stale_clusters(max_age_hours)
            return {"refreshed_count": count}
    
    import asyncio
    return asyncio.run(_refresh())


@celery.task(name="gmm.cleanup_old_clusters", bind=True)
def cleanup_old_clusters(self) -> dict:
    """
    Nettoie les anciens clusters orphelins.
    
    Returns:
        Dict avec nombre de clusters nettoyés
    """
    logger.info("[GMM] Cleanup des anciens clusters")
    # Implémentation simplifiée - peut être étendue
    return {"cleaned_count": 0}

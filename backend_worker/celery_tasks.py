"""Tâches Celery centralisées pour le backend worker."""

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery


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
@celery.task(name="vectorization.calculate", queue="vectorization", bind=True)
def calculate_vector(self, track_id: int, metadata: dict = None):
    """
    Calcule le vecteur d'une track via le service d'embeddings local.
    
    Pipeline:
        1. Récupère les données de la track via l'API
        2. Génère l'embedding avec OllamaEmbeddingService (local)
        3. Stocke le vecteur via l'API backend
    
    Args:
        track_id: ID de la track
        metadata: Métadonnées optionnelles de la track
        
    Returns:
        Résultat du calcul avec statut et métadonnées
    """
    import asyncio
    import time
    
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(f"[VECTOR] Démarrage calcul vecteur: track_id={track_id}")
    
    try:
        # Import du service de vectorisation Ollama
        from backend_worker.services.vectorization_service import (
            OptimizedVectorizationService,
            VectorizationError
        )
        
        # Instanciation du service
        service = OptimizedVectorizationService()
        
        # Fonction async pour vectoriser et stocker
        async def run_vectorization():
            nonlocal service
            
            # Vectoriser et stocker
            result = await service.vectorize_and_store(track_id, metadata)
            return result
        
        # Exécution de la fonction async
        result = asyncio.run(run_vectorization())
        
        # Ajouter les métadonnées de la tâche
        result['task_id'] = task_id
        result['calculation_time'] = time.time() - start_time
        result['embedding_model'] = 'nomic-embed-text'
        
        logger.info(
            f"[VECTOR] Résultat: status={result['status']}, "
            f"track_id={track_id}, time={result['calculation_time']:.2f}s"
        )
        return result
        
    except VectorizationError as ve:
        error_time = time.time() - start_time
        logger.error(f"[VECTOR] Erreur vectorisation: {str(ve)}")
        return {
            'task_id': task_id,
            'track_id': track_id,
            'status': 'error',
            'message': str(ve),
            'error_type': 'VectorizationError',
            'calculation_time': error_time,
            'embedding_model': OllamaEmbeddingService.MODEL_NAME
        }
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[VECTOR] Erreur inattendue: {str(e)}")
        import traceback
        logger.error(f"[VECTOR] Traceback: {traceback.format_exc()}")
        return {
            'task_id': task_id,
            'track_id': track_id,
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__,
            'calculation_time': error_time,
            'embedding_model': OllamaEmbeddingService.MODEL_NAME
        }


@celery.task(name="vectorization.batch", queue="vectorization", bind=True)
def calculate_vector_batch(self, track_ids: list[int]):
    """
    Calcule les vecteurs d'un batch de tracks via le service local.
    
    Args:
        track_ids: Liste des IDs de tracks
        
    Returns:
        Résultat du calcul batch
    """
    import asyncio
    import time
    
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(f"[VECTOR] Démarrage batch: {len(track_ids)} tracks")
    
    try:
        from backend_worker.services.vectorization_service import (
            OptimizedVectorizationService
        )
        
        service = OptimizedVectorizationService()
        
        async def run_batch():
            return await service.vectorize_and_store_batch(track_ids)
        
        result = asyncio.run(run_batch())
        
        result['task_id'] = task_id
        result['calculation_time'] = time.time() - start_time
        result['embedding_model'] = 'nomic-embed-text'
        
        logger.info(
            f"[VECTOR] Batch terminé: {result['successful']} succès, "
            f"{result['failed']} échecs en {result['calculation_time']:.2f}s"
        )
        return result
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[VECTOR] Erreur batch: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'error',
            'message': str(e),
            'calculation_time': error_time,
            'embedding_model': OllamaEmbeddingService.MODEL_NAME
        }


# === TÂCHES DE COVERS ===
# Import des vraies tâches de covers depuis covers_tasks.py

@celery.task(name="covers.extract_embedded", queue="deferred", bind=True)
def extract_embedded_covers(self, file_paths: list[str]):
    """
    Extrait les covers intégrées pour un lot de fichiers.

    Args:
        file_paths: Liste des chemins de fichiers

    Returns:
        Résultats de l'extraction des covers embedded
    """
    try:
        import time
        start_time = time.time()
        task_id = self.request.id

        logger.info(f"[COVERS] Démarrage extraction embedded: {len(file_paths)} fichiers")

        # Pour l'instant, simple placeholder
        return {
            'task_id': task_id,
            'files_processed': 0,
            'files_total': len(file_paths),
            'extraction_time': time.time() - start_time,
            'success': True
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur extraction: {str(e)}")
        raise


# === TÂCHES D'ENRICHISSEMENT ===
@celery.task(name="metadata.enrich_batch", queue="deferred", bind=True)
def enrich_tracks_batch_task(self, track_ids: list[int]):
    """
    Tâche d'enrichissement par lot des tracks.

    Args:
        track_ids: Liste des IDs de tracks à enrichir

    Returns:
        Résultats de l'enrichissement
    """
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
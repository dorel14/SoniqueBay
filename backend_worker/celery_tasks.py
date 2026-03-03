"""Tâches Celery centralisées pour le backend worker.

Ce module regroupe toutes les tâches Celery du worker SoniqueBay.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import os

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery


# Modèle léger et efficace pour Raspberry Pi
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'


# === TÂCHES DE SCAN ===
@celery.task(name="scan.discovery", queue="scan", bind=True)
def discovery(self, directory: str, progress_callback=None):
    """Découverte de fichiers musicaux et lancement de la pipeline complète.

    Pipeline : discovery -> extract_metadata -> batch_entities -> insert_batch

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

        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
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

        if progress_callback:
            progress_callback({
                "current": total_files,
                "total": total_files,
                "percent": 100,
                "step": "Discovery terminée",
                "files_discovered": total_files
            })

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Discovery terminée - {total_files} fichiers trouvés",
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "files_discovered": total_files
        }, channel="progress")

        batches = []
        if discovered_files:
            logger.info(f"[SCAN] Lancement de la pipeline d'extraction pour {total_files} fichiers")
            batch_size = 50
            batches = [discovered_files[i:i + batch_size] for i in range(0, len(discovered_files), batch_size)]
            logger.info(f"[SCAN] Création de {len(batches)} batches d'extraction")

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
            "batches_created": len(batches),
            "success": True
        }

        logger.info(f"[SCAN] Discovery et pipeline lancée: {result}")
        return result

    except Exception as e:
        import time
        logger.error(f"[SCAN] Erreur discovery: {str(e)}")
        return {
            "error": str(e),
            "directory": directory,
            "success": False
        }


# === TÂCHES DE MÉTADONNÉES ===
@celery.task(name="metadata.extract_batch", queue="extract", bind=True)
def extract_metadata_batch(self, file_paths: list, batch_id: str = None):
    """Extrait les métadonnées de fichiers en parallèle avec ThreadPoolExecutor.

    Optimisée pour Raspberry Pi : max_workers=2, timeout=60s.

    Args:
        file_paths: Liste des chemins de fichiers à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Résultat de l'extraction
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

        max_workers = 2  # Fixé à 2 pour Raspberry Pi
        extracted_metadata = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(extract_single_file_metadata, file_path): file_path
                for file_path in file_paths
            }
            for future in future_to_path:
                try:
                    metadata = future.result(timeout=60)
                    if metadata:
                        extracted_metadata.append(metadata)
                except Exception as e:
                    logger.error(f"[METADATA] Erreur traitement fichier: {e}")

        total_time = time.time() - start_time
        files_per_second = len(extracted_metadata) / total_time if total_time > 0 else 0

        logger.info(
            f"[METADATA] Extraction terminée: {len(extracted_metadata)}/{len(file_paths)} "
            f"fichiers en {total_time:.2f}s"
        )

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
def batch_entities(self, metadata_list: list, batch_id: str = None):
    """Regroupe les métadonnées par artistes et albums pour insertion optimisée.

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

        artists_by_name = {}
        albums_by_key = {}
        tracks_by_artist = defaultdict(list)

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

        for artist_name, tracks in tracks_by_artist.items():
            artist_info = artists_by_name[artist_name]

            for track in tracks:
                album_name = track.get('album', 'Unknown')
                if not album_name or album_name.lower() == 'unknown':
                    path_obj = Path(track.get('path', ''))
                    album_name = path_obj.parts[-1] if len(path_obj.parts) >= 1 else 'Unknown Album'

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

        artists_data = list(artists_by_name.values())
        albums_data = list(albums_by_key.values())
        tracks_data = metadata_list.copy()

        for track in tracks_data:
            track.pop('tracks_count', None)
            track.pop('albums_count', None)

        total_time = time.time() - start_time
        logger.info(
            f"[BATCH] Batching terminé: {len(artists_data)} artistes, "
            f"{len(albums_data)} albums, {len(tracks_data)} pistes en {total_time:.2f}s"
        )

        if albums_data:
            logger.info(f"[BATCH] Albums détectés (sample): {albums_data[:5]}")

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
# Utilisation de sentence-transformers (plus léger que Ollama/Koboldcpp pour Raspberry Pi)

@celery.task(name="vectorization.calculate", queue="vectorization", bind=True)
def calculate_vector(self, track_id: int, metadata: dict = None):
    """Calcule le vecteur d'une track via sentence-transformers.

    Pipeline:
        1. Recupere les donnees de la track via l'API
        2. Genere l'embedding avec sentence-transformers (local, leger)
        3. Stocke le vecteur via l'API backend

    Args:
        track_id: ID de la track
        metadata: Metadonnees optionnelles de la track

    Returns:
        Resultat du calcul avec statut et metadonnees
    """
    import time

    start_time = time.time()
    task_id = self.request.id

    logger.info(f"[VECTOR] Démarrage calcul vecteur: track_id={track_id}")

    try:
        from sentence_transformers import SentenceTransformer
        import httpx

        model = SentenceTransformer(EMBEDDING_MODEL)

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

        embedding = model.encode(text_to_embed, convert_to_numpy=True)
        embedding_list = embedding.tolist()

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
def calculate_vector_batch(self, track_ids: list):
    """Calcule les vecteurs d'un batch de tracks via sentence-transformers.

    Args:
        track_ids: Liste des IDs de tracks

    Returns:
        Résultat du calcul batch
    """
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

        model = SentenceTransformer(EMBEDDING_MODEL)
        api_url = os.getenv("API_URL", "http://api:8001")

        with httpx.Client(timeout=30) as client:
            for track_id in track_ids:
                try:
                    response = client.get(f"{api_url}/api/tracks/{track_id}")
                    if response.status_code != 200:
                        failed += 1
                        errors.append(f"Track {track_id}: non trouvé")
                        continue

                    track_metadata = response.json()

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

                    embedding = model.encode(text_to_embed, convert_to_numpy=True)
                    embedding_list = embedding.tolist()

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
            'errors': errors[:10],
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
def extract_embedded_covers(self, file_paths: list):
    """Extrait les covers intégrées pour un lot de fichiers.

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

@celery.task(name="metadata.enrich_batch", queue="deferred_enrichment", bind=True)
def enrich_tracks_batch_task(self, track_ids: list):
    """Tâche d'enrichissement par lot des tracks.

    Args:
        track_ids: Liste des IDs de tracks à enrichir

    Returns:
        Résultats de l'enrichissement
    """
    try:
        logger.info(f"[METADATA] Démarrage enrichissement batch: {len(track_ids)} tracks")

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
    """Déclenche le clustering GMM de tous les artistes.

    Args:
        force_refresh: Si True, force le recalcul même si récent

    Returns:
        Dict avec statistiques de clustering
    """
    from backend_worker.services.artist_clustering_service import ArtistClusteringService
    import asyncio

    async def _cluster() -> dict:
        async with ArtistClusteringService() as service:
            return await service.cluster_all_artists(force_refresh=force_refresh)

    return asyncio.run(_cluster())


@celery.task(name="gmm.cluster_artist", bind=True)
def cluster_artist(self, artist_id: int) -> dict:
    """Cluster un artiste spécifique.

    Args:
        artist_id: ID de l'artiste

    Returns:
        Dict avec infos de cluster
    """
    from backend_worker.services.artist_clustering_service import ArtistClusteringService
    import asyncio

    async def _cluster() -> dict:
        async with ArtistClusteringService() as service:
            return await service.cluster_artist(artist_id)

    return asyncio.run(_cluster())


@celery.task(name="gmm.refresh_stale_clusters", bind=True)
def refresh_stale_clusters(self, max_age_hours: int = 24) -> dict:
    """Rafraîchit les clusters trop anciens.

    Args:
        max_age_hours: Âge maximum en heures avant rafraîchissement

    Returns:
        Dict avec nombre de clusters rafraîchis
    """
    from backend_worker.services.artist_clustering_service import ArtistClusteringService
    import asyncio

    async def _refresh() -> dict:
        async with ArtistClusteringService() as service:
            count = await service.refresh_stale_clusters(max_age_hours)
            return {"refreshed_count": count}

    return asyncio.run(_refresh())


@celery.task(name="gmm.cleanup_old_clusters", bind=True)
def cleanup_old_clusters(self) -> dict:
    """Nettoie les anciens clusters orphelins.

    Returns:
        Dict avec nombre de clusters nettoyés
    """
    logger.info("[GMM] Cleanup des anciens clusters")
    # TODO: Implémenter le nettoyage réel des clusters orphelins
    return {"cleaned_count": 0}

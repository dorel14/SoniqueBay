from backend_worker.services.indexer import MusicIndexer
from backend_worker.services.music_scan import scan_music_files
from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_update_cover
)
from backend_worker.services.scan_optimizer import ScanOptimizer
import httpx
import asyncio
from backend_worker.utils.logging import logger
from pathlib import Path
from backend_worker.celery_app import celery
from backend_worker.services.music_scan import async_walk
from backend_worker.services.settings_service import SettingsService, MUSIC_PATH_TEMPLATE, ARTIST_IMAGE_FILES, ALBUM_COVER_FILES
from backend_worker.utils.pubsub import publish_event
import json
import time

async def process_metadata_chunk(client: httpx.AsyncClient, chunk: list, stats: dict):
    """Traite un lot de métadonnées de fichiers."""
    # Étape 1: Traitement par lots des artistes
    unique_artists_data = {
        (fd.get("artist").lower()): { "name": fd.get("artist"), "musicbrainz_artistid": fd.get("musicbrainz_artistid") or fd.get("musicbrainz_albumartistid") }
        for fd in chunk if fd.get("artist")
    }
    artists_data_list = list(unique_artists_data.values())
    logger.debug(f"Artists data being sent to batch create: {artists_data_list}")
    artist_map = await create_or_get_artists_batch(client, artists_data_list)
    stats['artists_processed'] += len(artist_map)

    # Lancer les tâches d'enrichissement pour les artistes
    for artist in artist_map.values():
        celery.send_task('enrich_artist_task', args=[artist['id']])

    # Étape 2: Traitement par lots des albums
    unique_albums_data = {}
    for fd in chunk:
        artist = artist_map.get(fd.get("artist", "").lower())
        if artist and fd.get("album"):
            album_key = (fd.get("album").lower(), artist["id"])
            if album_key not in unique_albums_data:
                unique_albums_data[album_key] = { "title": fd.get("album"), "album_artist_id": artist["id"], "release_year": fd.get("year"), "musicbrainz_albumid": fd.get("musicbrainz_albumid") }
    
    album_map = await create_or_get_albums_batch(client, list(unique_albums_data.values()))
    stats['albums_processed'] += len(album_map)

    # Lancer les tâches d'enrichissement pour les albums
    for album in album_map.values():
        celery.send_task('enrich_album_task', args=[album['id']])

    # Étape 3: Préparation et traitement par lots des pistes
    tracks_to_process = []
    for fd in chunk:
        artist = artist_map.get(fd.get("artist", "").lower())
        if not artist:
            continue
        album = album_map.get((fd.get("album", "").lower(), artist["id"]))
        if not album:
            continue
        fd["track_artist_id"] = artist["id"]
        fd["album_id"] = album["id"]
        tracks_to_process.append(fd)
    
    processed_tracks = await create_or_update_tracks_batch(client, tracks_to_process)
    stats['tracks_processed'] += len(processed_tracks)

    # Étape 4: Traitement asynchrone des covers
    from backend_worker.services.entity_manager import process_artist_covers

    cover_tasks = []

    # Grouper les images d'artistes par artiste
    artist_images_map = {}
    for fd in chunk:
        artist_name = fd.get("artist", "").lower()
        if artist_name and fd.get("artist_images"):
            artist = artist_map.get(artist_name)
            if artist:
                artist_id = artist["id"]
                if artist_id not in artist_images_map:
                    artist_images_map[artist_id] = {
                        "images": [],
                        "path": fd.get("artist_path")
                    }
                artist_images_map[artist_id]["images"].extend(fd["artist_images"])

    # Traiter les covers d'artistes groupées
    for artist_id, data in artist_images_map.items():
        cover_tasks.append(process_artist_covers(client, artist_id, data["path"], data["images"]))

    # Traiter les covers d'albums
    for fd in chunk:
        artist_name = fd.get("artist", "").lower()
        artist = artist_map.get(artist_name)
        if artist and fd.get("album"):
            album = album_map.get((fd.get("album", "").lower(), artist["id"]))
            if album and fd.get("cover_data"):
                cover_tasks.append(create_or_update_cover(
                    client,
                    "album",
                    album["id"],
                    fd["cover_data"],
                    fd.get("cover_mime_type"),
                    str(Path(fd["path"]).parent)
                ))

    if cover_tasks:
        await asyncio.gather(*cover_tasks)
        stats['covers_processed'] += len(cover_tasks)



async def count_music_files(directory: str, music_extensions: set) -> int:
    """Compte rapidement le nombre de fichiers musicaux dans un répertoire."""
    count = 0
    async for file_path_bytes in async_walk(Path(directory)):
        if Path(file_path_bytes.decode('utf-8', 'surrogateescape')).suffix.lower().encode('utf-8') in music_extensions:
            count += 1
    return count

async def scan_music_task(directory: str, progress_callback=None, chunk_size=500):
    """
    Tâche d'indexation ultra-optimisée avec parallélisation intelligente.

    Args:
        directory: Répertoire à scanner
        progress_callback: Fonction de callback pour la progression
        chunk_size: Taille des lots de traitement

    Returns:
        Statistiques du scan avec métriques de performance
    """
    start_time = time.time()

    try:
        logger.info(f"Démarrage de l'indexation ultra-optimisée de: {directory}")

        # Initialisation de l'optimiseur
        optimizer = ScanOptimizer(
            max_concurrent_files=100,  # Augmenté pour plus de parallélisation
            max_concurrent_audio=20,   # Analyses audio parallèles
            chunk_size=chunk_size,
            enable_threading=True
        )

        # Étape 1: Récupérer la configuration
        settings_service = SettingsService()
        template = await settings_service.get_setting(MUSIC_PATH_TEMPLATE)
        artist_files_json = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        cover_files_json = await settings_service.get_setting(ALBUM_COVER_FILES)

        scan_config = {
            "template": template,
            "artist_files": artist_files_json if isinstance(artist_files_json, list) else json.loads(artist_files_json or '[]'),
            "cover_files": cover_files_json if isinstance(cover_files_json, list) else json.loads(cover_files_json or '[]'),
            "music_extensions": {b'.mp3', b'.flac', b'.m4a', b'.ogg', b'.wav'}
        }
        template_parts = template.split('/')
        scan_config["artist_depth"] = template_parts.index("{album_artist}") if "{album_artist}" in template_parts else -1

        # Étape 2: Comptage des fichiers
        total_files = await count_music_files(directory, scan_config["music_extensions"])
        optimizer.metrics.files_total = total_files
        logger.info(f"Nombre total de fichiers musicaux: {total_files}")

        # Statistiques globales
        stats = {
            "files_processed": 0, "artists_processed": 0,
            "albums_processed": 0, "tracks_processed": 0, "covers_processed": 0
        }

        # Étape 3: Collecte et traitement par gros chunks avec parallélisation
        async with httpx.AsyncClient(timeout=300.0) as client:
            file_batch = []
            batch_size = 200  # Taille des batches pour l'extraction parallèle

            async for file_metadata in scan_music_files(directory, scan_config):
                file_batch.append(file_metadata)
                stats['files_processed'] += 1

                # Traiter par batches pour paralléliser l'extraction
                if len(file_batch) >= batch_size:
                    logger.info(f"Traitement parallèle d'un batch de {len(file_batch)} fichiers...")

                    # Extraction parallélisée des métadonnées
                    extracted_metadata = await optimizer.extract_metadata_batch(
                        [fm['path'].encode('utf-8', 'surrogateescape') for fm in file_batch],
                        scan_config
                    )

                    # Regrouper en chunks pour l'insertion DB
                    for i in range(0, len(extracted_metadata), optimizer.chunk_size):
                        chunk = extracted_metadata[i:i + optimizer.chunk_size]
                        if chunk:
                            await optimizer.process_chunk_with_optimization(
                                client, chunk, stats, progress_callback
                            )

                    file_batch = []

            # Traiter le dernier batch
            if file_batch:
                logger.info(f"Traitement du dernier batch de {len(file_batch)} fichiers...")
                extracted_metadata = await optimizer.extract_metadata_batch(
                    [fm['path'].encode('utf-8', 'surrogateescape') for fm in file_batch],
                    scan_config
                )

                for i in range(0, len(extracted_metadata), optimizer.chunk_size):
                    chunk = extracted_metadata[i:i + optimizer.chunk_size]
                    if chunk:
                        await optimizer.process_chunk_with_optimization(
                            client, chunk, stats, progress_callback
                        )

        # Étape 4: Indexation Whoosh
        if progress_callback:
            progress_callback({"current": 90, "total": 100, "percent": 90, "step": "Indexing search data..."})

        logger.info(f"Indexation Whoosh de {total_files} fichiers.")
        indexer = MusicIndexer()
        await indexer.async_init()
        await indexer.index_directory(directory, scan_config)

        # Étape 5: Lancement de la vectorisation (optimisée)
        if progress_callback:
            progress_callback({"current": 95, "total": 100, "percent": 95, "step": "Starting vectorization..."})

        # TODO: Implémenter la vectorisation automatique avec récupération optimisée des track_ids
        logger.info("Vectorisation différée - à optimiser avec récupération des track_ids")

        if progress_callback:
            progress_callback({"current": 100, "total": 100, "percent": 100, "step": "Scan complete!"})

        # Métriques finales avec rapport détaillé
        total_time = time.time() - start_time
        performance_report = optimizer.get_performance_report()
        logger.debug(f"Performance report: {performance_report}")

        final_metrics = {
            **performance_report,
            "total_scan_time": total_time,
            "scan_efficiency_score": performance_report.get("efficiency_score", 0)
        }

        # Publier les métriques détaillées
        publish_event("scan_metrics", {
            "directory": directory,
            "stats": stats,
            "metrics": final_metrics,
            "optimizer_config": {
                "max_concurrent_files": optimizer.max_concurrent_files,
                "max_concurrent_audio": optimizer.max_concurrent_audio,
                "chunk_size": optimizer.chunk_size
            }
        })

        # Notification de mise à jour
        publish_event("library_updated", {"source": "scanner"})
        logger.info("Événement 'library_updated' publié.")

        logger.info(f"Scan ultra-optimisé terminé. Stats: {stats}")
        logger.info(f"Performance: {final_metrics}")

        # Nettoyer l'optimiseur
        await optimizer.cleanup()

        result = {
            "directory": directory,
            **stats,
            "performance_metrics": final_metrics
        }
        logger.debug(f"Scan result: {result}")
        return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Erreur scan optimisé après {error_time:.2f}s: {str(e)}", exc_info=True)

        # Publier les métriques d'erreur
        publish_event("scan_error", {
            "directory": directory,
            "error": str(e),
            "duration": error_time,
            "performance_report": optimizer.get_performance_report() if 'optimizer' in locals() else {}
        })

        error_result = {
            "error": str(e),
            "directory": directory,
            "duration": error_time,
            "partial_metrics": stats if 'stats' in locals() else {}
        }
        logger.debug(f"Error result: {error_result}")
        return error_result
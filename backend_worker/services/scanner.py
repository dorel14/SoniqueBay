from backend_worker.services.indexer import MusicIndexer
from backend_worker.services.music_scan import scan_music_files
from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_update_cover
)
import httpx
import asyncio
from typing import Dict
from backend_worker.utils.logging import logger
from pathlib import Path
from backend_worker.celery_app import celery
from backend_worker.services.music_scan import async_walk
from backend_worker.services.settings_service import SettingsService, MUSIC_PATH_TEMPLATE, ARTIST_IMAGE_FILES, ALBUM_COVER_FILES
from backend_worker.utils.pubsub import publish_event
import json

async def process_metadata_chunk(client: httpx.AsyncClient, chunk: list, stats: dict):
    """Traite un lot de métadonnées de fichiers."""
    # Étape 1: Traitement par lots des artistes
    unique_artists_data = {
        (fd.get("artist").lower()): { "name": fd.get("artist"), "musicbrainz_artistid": fd.get("musicbrainz_artistid") or fd.get("musicbrainz_albumartistid") }
        for fd in chunk if fd.get("artist")
    }
    artist_map = await create_or_get_artists_batch(client, list(unique_artists_data.values()))
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
        if not artist: continue
        album = album_map.get((fd.get("album", "").lower(), artist["id"]))
        if not album: continue
        fd["track_artist_id"] = artist["id"]
        fd["album_id"] = album["id"]
        tracks_to_process.append(fd)
    
    processed_tracks = await create_or_update_tracks_batch(client, tracks_to_process)
    stats['tracks_processed'] += len(processed_tracks)

    # Étape 4: Traitement asynchrone des covers
    cover_tasks = []
    for fd in chunk:
        artist = artist_map.get(fd.get("artist", "").lower())
        album = album_map.get((fd.get("album", "").lower(), artist["id"])) if artist else None
        if artist and fd.get("artist_images"):
            for image_data, mime_type in fd["artist_images"]:
                cover_tasks.append(create_or_update_cover(client, "artist", artist["id"], image_data, mime_type, fd.get("artist_path")))
        if album and fd.get("cover_data"):
            cover_tasks.append(create_or_update_cover(client, "album", album["id"], fd["cover_data"], fd.get("cover_mime_type"), str(Path(fd["path"]).parent)))
    
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

async def scan_music_task(directory: str, progress_callback=None, chunk_size=200):
    """Tâche d'indexation en streaming avec traitement par lots et progression précise."""
    try:
        logger.info(f"Démarrage de l'indexation en streaming de: {directory}")
        
        # Étape 1: Récupérer tous les paramètres en une seule fois
        settings_service = SettingsService()
        template = await settings_service.get_setting(MUSIC_PATH_TEMPLATE)
        artist_files_json = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        cover_files_json = await settings_service.get_setting(ALBUM_COVER_FILES)
        
        scan_config = {
            "template": template,
            "artist_files": json.loads(artist_files_json or '[]'),
            "cover_files": json.loads(cover_files_json or '[]'),
            "music_extensions": {b'.mp3', b'.flac', b'.m4a', b'.ogg', b'.wav'}
        }
        template_parts = template.split('/')
        scan_config["artist_depth"] = template_parts.index("{album_artist}") if "{album_artist}" in template_parts else -1

        # Étape 2: Lancer le comptage des fichiers en arrière-plan
        stats = {
            "files_processed": 0, "artists_processed": 0,
            "albums_processed": 0, "tracks_processed": 0, "covers_processed": 0
        }
        chunk = []
        total_files = 0
        count_task = asyncio.create_task(count_music_files(directory, scan_config["music_extensions"]))

        # Étape 3: Traitement en streaming
        async with httpx.AsyncClient(timeout=300.0) as client:
            async for file_metadata in scan_music_files(directory, scan_config):
                if not total_files and count_task.done():
                    total_files = count_task.result()
                    logger.info(f"Nombre total de fichiers musicaux: {total_files}")

                chunk.append(file_metadata)
                stats['files_processed'] += 1
                
                if len(chunk) >= chunk_size:
                    logger.info(f"Traitement d'un lot de {len(chunk)} fichiers...")
                    await process_metadata_chunk(client, chunk, stats)
                    if progress_callback:
                        progress = {
                            "current": stats['files_processed'],
                            "total": total_files,
                            "percent": int((stats['files_processed'] / total_files) * 90) if total_files > 0 else 0, # 90% pour le scan
                            "step": f"Processing files... ({stats['files_processed']}/{total_files or '?'})"
                        }
                        progress_callback(progress)
                    chunk = []

            if chunk:
                logger.info(f"Traitement du dernier lot de {len(chunk)} fichiers...")
                await process_metadata_chunk(client, chunk, stats)

        if not count_task.done():
            total_files = await count_task
        
        stats['files_processed'] = total_files

        # Étape 4: Indexation Whoosh
        if progress_callback:
            progress_callback({"current": 95, "total": 100, "percent": 95, "step": "Indexing search data..."})
        
        logger.info(f"Indexation Whoosh de {total_files} fichiers.")
        indexer = MusicIndexer()
        await indexer.async_init()
        await indexer.index_directory(directory)
        
        if progress_callback:
            progress_callback({"current": 100, "total": 100, "percent": 100, "step": "Scan complete!"})

        # Envoyer une notification de mise à jour de la bibliothèque
        publish_event("library_updated", {"source": "scanner"})
        logger.info("Événement 'library_updated' publié.")

        logger.info(f"Scan terminé. Statistiques finales: {stats}")
        return { "directory": directory, **stats }

    except Exception as e:
        logger.error(f"Erreur d'indexation: {str(e)}", exc_info=True)
        return {"error": str(e)}
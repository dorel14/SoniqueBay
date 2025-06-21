
from celery_app import celery
from backend_worker.indexing.indexer import MusicIndexer
from backend_worker.indexing.music_scan import scan_music_files
from backend_worker.indexing.entity_manager import (
    create_or_get_artist, 
    create_or_get_album, 
    create_or_get_track,
    create_or_update_cover
)
from backend.api.schemas.covers_schema import CoverType
import httpx
from typing import Dict
from helpers.logging import logger




@celery.task("scan_music_task")
async def index_music_task(directory: str):
    """Tâche d'indexation avec monitoring de la progression."""
    try:
        logger.info(f"Démarrage de l'indexation de: {directory}")

        files = await scan_music_files(directory)


        async with httpx.AsyncClient() as client:
            for i, file_data in enumerate(files, 1):

                await process_file_entities(client, file_data)

        # 3. Indexer dans Whoosh
        indexer = MusicIndexer()
        await indexer.index_directory(
            directory, # Seconde moitié pour Whoosh
        )



    except Exception as e:
        logger.error(f"Erreur d'indexation: {str(e)}", exc_info=True)
        raise

async def process_file_entities(client: httpx.AsyncClient, file_data: Dict):
    """Traite les entités en base de données."""
    try:
        # Préparer les données artiste avec l'ID MusicBrainz
        artist_data = {
            "name": file_data.get("artist"),
            "musicbrainz_artistid": (
                file_data.get("musicbrainz_artistid") or 
                file_data.get("musicbrainz_albumartistid")
            ),
            "artist_path": file_data.get("artist_path"),
        }

        logger.info(f"Traitement artiste avec MusicBrainz ID: {artist_data['musicbrainz_artistid']}")
        artist = await create_or_get_artist(client, artist_data)
        if not artist:
            return

        # Traiter les images d'artiste immédiatement après la création/récupération
        if file_data.get("artist_images"):
            logger.info(f"Traitement de {len(file_data['artist_images'])} images pour artiste {artist['name']}")
            for image_data, mime_type in file_data["artist_images"]:
                logger.info(f"Création cover artiste pour {artist['name']}")
                await create_or_update_cover(
                    client=client,
                    entity_type=CoverType.ARTIST,
                    entity_id=artist["id"],
                    cover_data=image_data,
                    mime_type=mime_type,
                    url=file_data.get("artist_path")
                )

        # Traiter l'album
        album = await create_or_get_album(client, file_data, artist["id"])
        if not album:
            return
            
        # Traiter la piste
        await create_or_get_track(client, {**file_data, "track_artist_id": artist["id"], "album_id": album["id"]})
        
    except Exception as e:
        logger.error(f"Erreur traitement entités: {str(e)}")
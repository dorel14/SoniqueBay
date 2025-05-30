from backend.task_system import AsyncTask
from backend.indexing.indexer import MusicIndexer
from backend.indexing.music_scan import scan_music_files
from backend.indexing.entity_manager import (
    create_or_get_artist, 
    create_or_get_album, 
    create_or_get_track,
    create_or_update_cover
)
from backend.api.schemas.covers_schema import CoverType
import httpx
from typing import Dict
from helpers.logging import logger


# Création de l'instance AsyncTask avant le décorateur
index_music = AsyncTask(name="index_music", description="Indexation des fichiers musicaux")

@index_music
async def index_music_task(update_progress, directory: str):
    """Tâche d'indexation avec monitoring de la progression."""
    try:
        logger.info(f"Démarrage de l'indexation de: {directory}")
        
        # 1. Scanner et traiter les fichiers en BDD
        update_progress(0, "Scan des fichiers...")
        files = await scan_music_files(directory)
        
        # 2. Traiter les entités en BDD avec entity_manager
        total = len(files)
        async with httpx.AsyncClient() as client:
            for i, file_data in enumerate(files, 1):
                progress = (i / total) * 50  # Première moitié pour BDD
                update_progress(progress, "Traitement en base de données...")
                await process_file_entities(client, file_data)
        
        # 3. Indexer dans Whoosh
        indexer = MusicIndexer()
        await indexer.index_directory(
            directory,
            lambda p: update_progress(50 + p/2, "Indexation recherche...")  # Seconde moitié pour Whoosh
        )
        
        update_progress(100, "Indexation terminée")
        
    except Exception as e:
        logger.error(f"Erreur d'indexation: {str(e)}", exc_info=True)
        raise

async def process_file_entities(client: httpx.AsyncClient, file_data: Dict):
    """Traite les entités en base de données."""
    try:
        # Préparer les données artiste
        artist_data = {
            "name": file_data.get("artist"),
            "musicbrainz_artistid": file_data.get("musicbrainz_artistid"),
            "artist_path": file_data.get("artist_path"),
        }

        logger.info(f"Traitement artiste {artist_data['name']}")
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
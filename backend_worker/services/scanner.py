from backend_worker.services.indexer import MusicIndexer
from backend_worker.services.music_scan import scan_music_files
from backend_worker.services.entity_manager import (
    create_or_get_artist,
    create_or_get_album,
    create_or_get_track,
    create_or_update_cover
)
import httpx
from typing import Dict
from helpers.logging import logger

async def scan_music_task(directory: str):
    """Tâche d'indexation avec monitoring de la progression."""
    try:
        logger.info(f"Démarrage de l'indexation de: {directory}")

        files = await scan_music_files(directory)
        logger.info(f"Fichiers trouvés: {len(files)} dans {directory}")
        logger.debug(f"files type: {type(files)}")
        for i, f in enumerate(files):
            logger.debug(f"files[{i}] type: {type(f)}")
        results = []

        async with httpx.AsyncClient() as client:
            for i, file_data in enumerate(files, 1):
                res = await process_file_entities(client, file_data)
                results.append(res)

        # 3. Indexer dans Whoosh
        indexer = MusicIndexer()
        await indexer.async_init()  # Assurez-vous que l'index est initialisé
        logger.info(f"Indexation Whoosh de {len(files)} fichiers dans {directory}")
        await indexer.index_directory(
            directory, # Seconde moitié pour Whoosh
        )

        # Retourne un résumé JSON-serializable
        return {
            "directory": directory,
            "files_processed": len(files),
            "entities_results": results
        }

    except Exception as e:
        logger.error(f"Erreur d'indexation: {str(e)}", exc_info=True)
        # Retourne l'erreur sous forme de string pour éviter une exception non sérialisable
        return {"error": str(e)}

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

        logger.info(f"Traitement artiste avec MusicBrainz ID: {artist_data}")
        artist = await create_or_get_artist(client, artist_data)
        if not artist:
            return {"artist": None, "status": "artist_not_created"}

        # Traiter les images d'artiste immédiatement après la création/récupération
        if file_data.get("artist_images"):
            logger.info(f"Traitement de {len(file_data['artist_images'])} images pour artiste {artist['name']}")
            for image_data, mime_type in file_data["artist_images"]:
                logger.info(f"Création cover artiste pour {artist['name']}")
                await create_or_update_cover(
                    client=client,
                    entity_type="artist",
                    entity_id=artist["id"],
                    cover_data=image_data,
                    mime_type=mime_type,
                    url=file_data.get("artist_path")
                )

        # Traiter l'album
        album = await create_or_get_album(client, file_data, artist["id"])
        if not album:
            return {"album": None, "status": "album_not_created"}

        # Traiter la piste
        track = await create_or_get_track(client, {**file_data, "track_artist_id": artist["id"], "album_id": album["id"]})
        results={
            "artist_id": artist["id"],
            "album_id": album["id"] if album else None,
            "track_id": track["id"] if track else None,
            "status": "ok"
        }
        logger.debug(f"process_file_entities returns: {type(results)}")
        return results

    except Exception as e:
        logger.error(f"Erreur traitement entités: {str(e)}")
        return {"error": str(e)}
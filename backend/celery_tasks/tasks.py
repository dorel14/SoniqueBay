# -*- coding: utf-8 -*-
from backend.indexing.music_scan import scan_music_files
from backend.indexing.search import create_search_index, add_to_index
from backend.celery_app import celery as celery_app
from backend.celery_tasks.entity_manager import (
    create_or_get_genre,
    create_or_get_artist,
    create_or_get_album
)
from helpers.logging import logger
import httpx
import asyncio

@celery_app.task(bind=True, max_retries=3)
def scan_and_index_music(self, directory: str):
    logger.info(f"Début du scan du répertoire: {directory}")
    index = create_search_index("./data/whoosh_index")

    # Convertir le générateur en liste pour pouvoir utiliser len()
    try:
        files = list(scan_music_files(directory))
        logger.info(f"Nombre de fichiers trouvés : {len(files)}")
    except Exception as e:
        logger.error(f"Erreur lors du scan des fichiers : {str(e)}")
        return

    if not files:
        logger.warning("Aucun fichier trouvé à indexer")
        return

    async def process_file(client, file):
        try:
            if not file.get("title") or not file.get("artist"):
                logger.warning("Données manquantes pour le fichier: %s", file.get('path'))
                return

            # Créer/récupérer l'artiste d'abord
            artist_data = {
                "name": file.get("artist"),
                "musicbrain_id": file.get("musicbrain_artistid")
            }
            artist = await create_or_get_artist(client, artist_data)
            if not artist:
                logger.error("Impossible de créer/récupérer l'artiste pour: %s", file.get('path'))
                return
            
            artist_id = artist.get('id')
            if not artist_id:
                logger.error("ID artiste manquant pour: %s", file.get('path'))
                return

            # Créer/récupérer l'album avec l'ID de l'artiste validé
            album_data = {
                "title": file.get("album"),
                "release_year": file.get("year"),
                "musicbrainz_albumid": file.get("musicbrain_albumid"),
                "album_artist_id": artist_id  # ID artiste validé
            }
            album = await create_or_get_album(client, album_data)
            
            # Préparer les données de la piste avec l'ID artiste validé
            track_data = {
                "title": file.get("title"),
                "path": file.get("path"),
                "duration": file.get("duration", 0),
                "track_number": file.get("track_number"),
                "disc_number": file.get("disc_number"),
                "musicbrainz_id": file.get("musicbrain_id"),
                "acoustid_fingerprint": file.get("acoustid_fingerprint", ""),
                "artist_id": artist_id,  # ID artiste validé
                "album_id": album.get('id') if album else None
            }

            # Validation finale avant envoi
            if not track_data["artist_id"]:
                logger.error("ID artiste manquant pour la piste: %s", file.get('path'))
                return

            # Envoi des données validées avec gestion des codes HTTP
            response = await client.post("http://localhost:8001/api/tracks/", json=track_data)
            
            if response.status_code == 409:
                logger.info(f"La piste existe déjà: {file.get('title')} - ignorée")
                return
            elif response.status_code not in (200, 201):
                logger.error(f"Erreur API pour {file.get('title')}: {response.text}")
                return
                
            logger.info(f"Piste créée/mise à jour avec succès: {file.get('title')}")

            # Index Whoosh avec tous les champs requis
            whoosh_doc = {
                "title": file.get("title", ""),
                "artist": file.get("artist", ""),
                "album": file.get("album", ""),
                "path": file.get("path", ""),
                "genre": file.get("genre", ""),
                "year": file.get("year", ""),
                "decade": str(int(file.get("year", "0")) // 10 * 10) if file.get("year", "").isdigit() else "",
                "disc_number": file.get("disc_number", ""),
                "track_number": file.get("track_number", ""),
                "acoustid_fingerprint": file.get("acoustid_fingerprint", ""),
                "duration": str(file.get("duration", "")),
                "musicbrain_id": file.get("musicbrain_id", ""),
                "musicbrain_albumid": file.get("musicbrain_albumid", ""),
                "musicbrain_artistid": file.get("musicbrain_artistid", ""),
                "musicbrain_albumartistid": file.get("musicbrain_albumartistid", ""),
                "musicbrain_genre": file.get("musicbrain_genre", ""),
                "cover": ""  # À compléter si vous avez des métadonnées de couverture
            }
            add_to_index(index, whoosh_doc)
            logger.info(f"Indexé avec succès: {file.get('title')}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {file.get('path')}: {str(e)}")
            raise
    
    async def process_files():
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Traitement par lots de 10 fichiers
            chunks = [files[i:i + 10] for i in range(0, len(files), 10)]
            for i, chunk in enumerate(chunks, 1):
                try:
                    tasks = [process_file(client, file) for file in chunk]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(f"Traitement du lot {i}/{len(chunks)} terminé")
                    
                    # Gestion des erreurs par fichier
                    for result, file in zip(results, chunk):
                        if isinstance(result, Exception):
                            logger.error(f"Erreur pour {file.get('path')}: {str(result)}")
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du lot {i}: {str(e)}")
                    continue

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(process_files())
        logger.info("Scan et indexation terminés avec succès")
    except Exception as e:
        logger.error(f"Erreur globale: {str(e)}")
        self.retry(countdown=60)  # Retry after 1 minute






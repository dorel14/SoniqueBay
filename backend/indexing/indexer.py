# music/indexer.py

import httpx

from typing import Callable, Optional

from backend.indexing.music_scan import scan_music_files
from backend.indexing.search import get_or_create_index, add_to_index
from backend.indexing.entity_manager import create_or_get_artist, create_or_get_album, create_or_get_genre, create_or_get_track
from helpers.logging import logger

class MusicIndexer:
    def __init__(self, index_dir="./data/whoosh_index"):
        self.index = get_or_create_index(index_dir)

    async def index_directory(self, directory: str, progress_callback: Optional[Callable] = None):
        """Scan, appelle l’API, et indexe dans Whoosh."""
        files = list(scan_music_files(directory))
        total = len(files)

        if progress_callback:
            progress_callback(0, f"Trouvé {total} fichiers")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, file in enumerate(files, 1):
                try:
                    artist = await create_or_get_artist(client, {
                        "name": file.get("artist"),
                        "musicbrain_artistid": file.get("musicbrain_artistid"),
                    })
                    if not artist:
                        continue

                    # Traitement des genres avant la création de l'album
                    genres = []
                    if file.get("genre"):
                        for genre_name in file.get("genre").split(","):
                            genre = await create_or_get_genre(client, genre_name.strip())
                            if genre:
                                genres.append(genre["id"])

                    album_data = {
                        "title": file.get("album"),
                        "release_year": file.get("year"),
                        "musicbrainz_albumid": file.get("musicbrain_albumid"),
                        "cover_url": None,
                        "genres": genres  # Ajout des IDs de genres
                    }

                    album = await create_or_get_album(client, album_data, artist_id=artist.get("id"))

                    # Préparer les données pour l’API piste
                    track_data = {
                        "title": file.get("title"),
                        "path": file.get("path"),
                        "duration": file.get("duration", 0),
                        "track_number": file.get("track_number"),
                        "disc_number": file.get("disc_number"),
                        "musicbrainz_id": file.get("musicbrain_id"),
                        "acoustid_fingerprint": file.get("acoustid_fingerprint", ""),
                        "track_artist_id": artist.get("id"),  # Changement ici
                        "album_id": album.get("id") if album else None,
                    }

                    # Utilisation de create_or_get_track au lieu du POST direct
                    track = await create_or_get_track(client, track_data)
                    if track:
                        logger.info("Track OK: %s", file.get("title"))
                        # Indexation dans Whoosh
                        add_to_index(self.index, file)
                    else:
                        logger.warning("Erreur traitement piste: %s", file.get("title"))

                except Exception as e:
                    logger.error(f"Erreur fichier {file.get('path')}: {str(e)}")
                    continue

                if progress_callback:
                    progress = (i / total) * 100
                    progress_callback(progress, f"Traitement de {file.get('title')}")

        logger.info("Indexation terminée.")

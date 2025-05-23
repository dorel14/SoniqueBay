# music/indexer.py

import httpx
import os
import shutil

from typing import Callable, Optional, Dict
from backend.indexing.music_scan import scan_music_files
from backend.indexing.search import get_or_create_index, add_to_index
from backend.indexing.entity_manager import create_or_get_artist, create_or_get_album, create_or_get_genre, create_or_get_track
from helpers.logging import logger

class MusicIndexer:
    def __init__(self, index_dir="./data/whoosh_index"):
        self.index_dir = index_dir
        self.index = get_or_create_index(index_dir)

    def clean_track_data(self, file: Dict) -> Dict:
        """Nettoie et valide les données de piste avant l'envoi."""
        track_data = {
            "title": file.get("title"),
            "path": file.get("path"),
            "duration": file.get("duration", 0),
            "track_number": file.get("track_number"),
            "disc_number": file.get("disc_number"),
            "musicbrainz_id": file.get("musicbrain_id"),
            "acoustid_fingerprint": file.get("acoustid_fingerprint", ""),
            "year": file.get("year"),
            "genre": file.get("genre"),
            "musicbrainz_albumid": file.get("musicbrainz_albumid"),
            "musicbrainz_artistid": file.get("musicbrainz_artistid"),
            "musicbrainz_albumartistid": file.get("musicbrainz_albumartistid"),
            "musicbrainz_genre": file.get("musicbrainz_genre"),
            "file_type": file.get("file_type"),
            "bitrate": file.get("bitrate"),
            "featured_artists": file.get("featured_artists", ""),
            "bpm": file.get("bpm"),
            "key": file.get("key"),
            "scale": file.get("scale"),
            "danceability": file.get("danceability"),
            "mood_happy": file.get("mood_happy"),
            "mood_aggressive": file.get("mood_aggressive"),
            "mood_party": file.get("mood_party"),
            "mood_relaxed": file.get("mood_relaxed"),
            "instrumental": file.get("instrumental"),
            "acoustic": file.get("acoustic"),
            "tonal": file.get("tonal"),
            "genre_main": file.get("genre_main"),
            "genre_tags": [{"name": tag} for tag in file.get("genre_tags", [])],
            "mood_tags": [{"name": tag} for tag in file.get("mood_tags", [])],
        }

        # Gestion spéciale des covers
        cover_data = file.get("cover_data")
        cover_mime_type = file.get("cover_mime_type")
        
        if cover_data and cover_mime_type:
            if isinstance(cover_data, str) and cover_data.startswith('data:image/'):
                track_data["cover_data"] = cover_data
                track_data["cover_mime_type"] = cover_mime_type
            else:
                logger.warning(f"Données de cover invalides pour {file.get('path')}")
                track_data["cover_data"] = None
                track_data["cover_mime_type"] = None
        else:
            track_data["cover_data"] = None
            track_data["cover_mime_type"] = None

        return {k: v for k, v in track_data.items() if v is not None}

    def prepare_whoosh_data(self, file: Dict, track: Dict) -> Dict:
        """Prépare les données pour l'indexation Whoosh."""
        whoosh_data = {
            "id": track.get("id"),
            "title": file.get("title"),
            "path": file.get("path"),
            "artist": file.get("artist"),
            "album": file.get("album"),
            "genre": file.get("genre"),
            "year": file.get("year"),
            "duration": file.get("duration", 0),
            "track_number": file.get("track_number"),
            "disc_number": file.get("disc_number"),
            "musicbrainz_id": file.get("musicbrainz_id"),
            "musicbrainz_albumid": file.get("musicbrainz_albumid"),
            "musicbrainz_artistid": file.get("musicbrainz_artistid"),
            "musicbrainz_genre": file.get("musicbrainz_genre")
        }
        return {k: v for k, v in whoosh_data.items() if v is not None}

    async def index_directory(self, directory: str, progress_callback: Optional[Callable] = None):
        """Scan, appelle l’API, et indexe dans Whoosh."""
        files = list(scan_music_files(directory))
        total = len(files)

        if progress_callback:
            progress_callback(0, f"Trouvé {total} fichiers")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, file in enumerate(files, 1):
                try:
                    # Création/récupération de l'artiste
                    artist = await create_or_get_artist(client, {
                        "name": file.get("artist"),
                        "musicbrain_artistid": file.get("musicbrain_artistid"),
                    })
                    if not artist:
                        logger.warning(f"Artiste non créé pour: {file.get('path')}")
                        continue

                    # Traitement des genres
                    genres = []
                    if file.get("genre"):
                        for genre_name in file.get("genre").split(","):
                            genre = await create_or_get_genre(client, genre_name.strip())
                            if genre:
                                genres.append(genre["id"])

                    # Création/récupération de l'album
                    album = await create_or_get_album(client, {
                        "title": file.get("album"),
                        "release_year": file.get("year"),
                        "musicbrainz_albumid": file.get("musicbrain_albumid"),
                        "cover_url": None,
                        "genres": genres
                    }, artist_id=artist.get("id"))

                    # Préparation et nettoyage des données de piste
                    track_data = self.clean_track_data(file)
                    track_data["track_artist_id"] = artist.get("id")
                    track_data["album_id"] = album.get("id") if album else None

                    # Création/mise à jour de la piste
                    track = await create_or_get_track(client, track_data)
                    if track:
                        logger.info(f"Track OK: {file.get('title')}")
                        # Préparation et indexation dans Whoosh
                        whoosh_data = self.prepare_whoosh_data(file, track)
                        add_to_index(self.index, whoosh_data)
                    else:
                        logger.warning(f"Erreur traitement piste: {file.get('title')}")

                except Exception as e:
                    logger.error(f"Erreur fichier {file.get('path')}: {str(e)}", exc_info=True)
                    continue

                if progress_callback:
                    progress = (i / total) * 100
                    progress_callback(progress, f"Traitement de {file.get('title')}")

        logger.info("Indexation terminée.")

    async def reindex_all(self, directory: str, progress_callback: Optional[Callable] = None):
        """Force la réindexation complète."""
        logger.info("Début de la réindexation complète...")
        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        self.index = get_or_create_index(self.index_dir)
        await self.index_directory(directory, progress_callback)

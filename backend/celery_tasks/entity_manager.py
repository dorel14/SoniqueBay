from typing import Dict, Optional
from cachetools import TTLCache
import httpx
from helpers.logging import logger

# Cache pour stocker les IDs (durée de vie 1 heure)
artist_cache = TTLCache(maxsize=100, ttl=3600)
album_cache = TTLCache(maxsize=100, ttl=3600)
genre_cache = TTLCache(maxsize=50, ttl=3600)

async def create_or_get_genre(client: httpx.AsyncClient, genre_name: str) -> Optional[int]:
    if not genre_name:
        return None
    # ...existing code from tasks.py for create_or_get_genre...

async def create_or_get_artist(client: httpx.AsyncClient, artist_data) -> Optional[Dict]:
    try:
        name = artist_data.get("name")
        musicbrainz_id = artist_data.get("musicbrain_id")

        if not name:
            logger.error("Nom d'artiste manquant")
            return None

        # Vérifier le cache
        cache_key = f"{name.lower()}:{musicbrainz_id}" if musicbrainz_id else name.lower()
        if cache_key in artist_cache:
            logger.debug("Artiste trouvé dans le cache: %s", name)
            return artist_cache[cache_key]

        # Recherche par nom exact (insensible à la casse)
        response = await client.get(
            "http://localhost:8001/api/artists/search",
            params={"name": name}
        )

        if response.status_code == 200:
            artists = response.json()
            if artists:
                artist = artists[0]
                artist_cache[cache_key] = artist
                logger.info("Artiste existant trouvé: %s", name)
                return artist

        # Création uniquement si l'artiste n'existe pas
        logger.info("Création d'un nouvel artiste: %s", name)
        create_data = {
            "name": name,
            "musicbrain_id": musicbrainz_id
        }
        
        response = await client.post(
            "http://localhost:8001/api/artists/",
            json=create_data
        )

        if response.status_code in (200, 201):
            artist = response.json()
            artist_cache[cache_key] = artist
            logger.info("Nouvel artiste créé: %s", name)
            return artist
        else:
            logger.error("Erreur création artiste %s: %s", name, response.text)
            return None

    except Exception as e:
        logger.error("Erreur pour artiste %s: %s", name, str(e))
        return None

async def create_or_get_album(client: httpx.AsyncClient, album_data: Dict, artist_id: Optional[int] = None) -> Optional[Dict]:
    """Créer ou récupérer un album."""
    try:
        if not artist_id:
            logger.error("ID artiste manquant pour l'album: %s", album_data.get('title'))
            return None

        # Vérifier si l'album existe déjà pour cet artiste
        response = await client.get(
            "http://localhost:8001/api/albums/",
            params={"skip": 0, "limit": 100}
        )

        if response.status_code == 200:
            albums = response.json()
            # Recherche exacte par titre et artiste
            for album in albums:
                if (album.get("title", "").lower() == album_data.get("title", "").lower() and
                    album.get("album_artist_id") == artist_id):
                    logger.info("Album existant trouvé: %s", album_data.get("title"))
                    return album

        # Préparation des données pour la création
        create_data = {
            "title": album_data.get("title"),
            "album_artist_id": artist_id,
            "release_year": album_data.get("release_year"),
            "musicbrainz_albumid": album_data.get("musicbrainz_albumid"),
            "cover_url": album_data.get("cover_url")
        }

        # Création de l'album
        logger.info("Création d'un nouvel album: %s", create_data["title"])
        response = await client.post(
            "http://localhost:8001/api/albums/",
            json=create_data
        )

        if response.status_code in (200, 201):
            album = response.json()
            logger.info("Nouvel album créé: %s", create_data["title"])
            return album
        else:
            logger.error("Erreur création album: %s - %s", create_data["title"], response.text)
            return None

    except Exception as e:
        logger.error("Erreur dans create_or_get_album: %s", str(e))
        return None

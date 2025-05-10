from typing import Dict, Optional
from cachetools import TTLCache
import httpx
from helpers.logging import logger
from datetime import datetime

# Cache pour stocker les IDs (durée de vie 1 heure)
artist_cache = TTLCache(maxsize=100, ttl=3600)
album_cache = TTLCache(maxsize=100, ttl=3600)
genre_cache = TTLCache(maxsize=50, ttl=3600)

async def create_or_get_genre(client: httpx.AsyncClient, genre_name: str) -> Optional[int]:
    if not genre_name:
        return None
    # ...existing code from tasks.py for create_or_get_genre...

async def create_or_get_artist(client: httpx.AsyncClient, artist_data) -> Optional[int]:
    """Créer ou récupérer un artiste."""
    try:
        # Vérification des données requises
        if not artist_data.get("name"):
            logger.error("Nom d'artiste manquant")
            return None

        # Rechercher d'abord par MusicBrainz ID si disponible
        if artist_data.get("musicbrain_id"):
            response = await client.get(
                "http://localhost:8001/api/artists/search",
                params={"musicbrain_id": artist_data["musicbrain_id"]}
            )
            if response.status_code == 200:
                artists = response.json()
                if artists:
                    logger.info("Artiste trouvé par MusicBrainz ID: %s", artist_data["name"])
                    return artists[0]

        # Rechercher par nom
        response = await client.get(
            "http://localhost:8001/api/artists/search",
            params={"name": artist_data["name"]}
        )
        if response.status_code == 200:
            artists = response.json()
            if artists:
                logger.info("Artiste trouvé par nom: %s", artist_data["name"])
                return artists[0]

        # Si l'artiste n'existe pas, le créer
        logger.info("Création d'un nouvel artiste: %s", artist_data["name"])
        response = await client.post(
            "http://localhost:8001/api/artists/",
            json=artist_data
        )

        if response.status_code in (200, 201):
            logger.info("Nouvel artiste créé avec succès: %s", artist_data["name"])
            return response.json()
        else:
            logger.error("Erreur création artiste %s: %s", artist_data["name"], response.text)
            return None

    except Exception as e:
        logger.error("Erreur dans create_or_get_artist pour %s: %s", 
                    artist_data.get("name", "Unknown"), str(e))
        return None

async def create_or_get_album(client: httpx.AsyncClient, album_data: Dict, artist_id: Optional[int] = None) -> Optional[int]:
    """Créer ou récupérer un album."""
    try:
        # Ajouter les champs de date
        album_data.update({
            "album_artist_id": artist_id,
            "date_added": datetime.utcnow().isoformat(),
            "date_modified": datetime.utcnow().isoformat()
        })

        # Essayer de trouver l'album par son ID MusicBrainz
        if album_data.get("musicbrainz_albumid"):
            response = await client.get(
                f"http://localhost:8001/api/albums/search",
                params={"musicbrainz_albumid": album_data["musicbrainz_albumid"]}
            )
            if response.status_code == 200:
                albums = response.json()
                if albums:
                    return albums[0]

        # Si l'album n'existe pas, le créer
        response = await client.post(
            "http://localhost:8001/api/albums/",
            json=album_data
        )
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error(f"Erreur création album: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Erreur dans create_or_get_album: {str(e)}")
        return None

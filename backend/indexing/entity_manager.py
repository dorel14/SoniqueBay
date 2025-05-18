from typing import Dict, Optional, Callable
from cachetools import TTLCache
import httpx
from helpers.logging import logger

# Cache pour stocker les IDs (durée de vie 1 heure)
artist_cache = TTLCache(maxsize=100, ttl=3600)
album_cache = TTLCache(maxsize=100, ttl=3600)
genre_cache = TTLCache(maxsize=50, ttl=3600)
track_cache = TTLCache(maxsize=1000, ttl=3600)

async def create_or_get_genre(client: httpx.AsyncClient, genre_name: str) -> Optional[Dict]:
    """Créer ou récupérer un genre."""
    try:
        if not genre_name:
            return None

        # Vérifier le cache
        if genre_name.lower() in genre_cache:
            return genre_cache[genre_name.lower()]

        # Rechercher le genre par nom
        response = await client.get(
            "http://localhost:8001/api/genres/search",
            params={"name": genre_name}
        )

        if response.status_code == 200:
            genres = response.json()
            if genres:
                genre = genres[0]
                genre_cache[genre_name.lower()] = genre
                logger.debug(f"Genre trouvé: {genre_name}")
                return genre

        # Créer le genre s'il n'existe pas
        create_data = {"name": genre_name}
        response = await client.post(
            "http://localhost:8001/api/genres/",
            json=create_data
        )

        if response.status_code in (200, 201):
            genre = response.json()
            genre_cache[genre_name.lower()] = genre
            logger.info(f"Nouveau genre créé: {genre_name}")
            return genre
        else:
            logger.error(f"Erreur création genre {genre_name}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Erreur pour genre {genre_name}: {str(e)}")
        return None

def update_missing_info(entity: Dict, new_data: Dict) -> bool:
    """Compare et met à jour les informations manquantes (version synchrone)"""
    updated = False
    for key, new_value in new_data.items():
        if new_value and (key not in entity or not entity.get(key)):
            entity[key] = new_value
            updated = True
    return updated

async def create_or_get_artist(client: httpx.AsyncClient, artist_data) -> Optional[Dict]:
    try:
        name = artist_data.get("name")
        musicbrainz_artistid = artist_data.get("musicbrain_artistid") 

        # Recherche par MusicBrainz ID en priorité
        if musicbrainz_artistid:
            response = await client.get(
                "http://localhost:8001/api/artists/search",
                params={"musicbrainz_artistid": musicbrainz_artistid}
            )
            if response.status_code == 200:
                artists = response.json()
                if artists:
                    return artists[0]

        if not name:
            logger.error("Nom d'artiste manquant")
            return None

        # Vérifier le cache
        cache_key = f"{name.lower()}:{musicbrainz_artistid}" if musicbrainz_artistid else name.lower()
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
                # Vérifier et mettre à jour les infos manquantes
                if update_missing_info(artist, {
                    "musicbrainz_artistid": artist_data.get("musicbrainz_artistid"),
                    "cover_url": artist_data.get("cover_url"),
                    "genre": artist_data.get("genre")
                }):
                    response = await client.put(
                        f"http://localhost:8001/api/artists/{artist['id']}", 
                        json=artist_data
                    )
                    if response.status_code == 200:
                        artist = response.json()
                return artist

        # Création uniquement si l'artiste n'existe pas
        logger.info("Création d'un nouvel artiste: %s", name)
        artist_create = {
            "name": name,
            "musicbrainz_artistid": musicbrainz_artistid
        }

        response = await client.post(
            "http://localhost:8001/api/artists/",
            json=artist_create
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
        if not artist_id or not album_data.get("title"):
            logger.error("ID artiste ou titre album manquant")
            return None

        # Rechercher l'album par titre et artist_id
        response = await client.get(
            "http://localhost:8001/api/albums/search",
            params={
                "title": album_data["title"],
                "artist_id": artist_id
            }
        )

        if response.status_code == 200:
            albums = response.json()
            if albums:
                album = albums[0]
                # Vérifier et mettre à jour les infos manquantes (version synchrone)
                if update_missing_info(album, {
                    "release_year": album_data.get("release_year"),
                    "musicbrainz_albumid": album_data.get("musicbrainz_albumid"),
                    "cover_url": album_data.get("cover_url")
                }):
                    # Mise à jour si nécessaire
                    update_data = {**album}
                    response = await client.put(
                        f"http://localhost:8001/api/albums/{album['id']}", 
                        json=update_data
                    )
                    if response.status_code == 200:
                        album = response.json()
                        logger.info(f"Album mis à jour: {album['title']}")
                return album

        # Traiter les genres avant la création/mise à jour
        genres = []
        if album_data.get("genre"):
            for genre_name in album_data["genre"].split(","):
                genre = await create_or_get_genre(client, genre_name.strip())
                if genre:
                    genres.append(genre["id"])

        # Créer l'album avec les données nettoyées
        create_data = {
            "title": album_data["title"],
            "album_artist_id": artist_id,
            "release_year": album_data.get("release_year"),
            "musicbrainz_albumid": album_data.get("musicbrainz_albumid"),
            "cover_url": album_data.get("cover_url"),
            "genres": genres
        }

        logger.info(f"Création d'un nouvel album: {create_data['title']} (artist_id: {artist_id})")
        response = await client.post(
            "http://localhost:8001/api/albums/",
            json=create_data
        )

        if response.status_code in (200, 201):
            album = response.json()
            logger.info(f"Album créé avec succès: {album.get('id')} - {album.get('title')}")
            return album
        else:
            logger.error(f"Erreur création album: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Erreur create_or_get_album: {str(e)}")
        return None

async def create_or_get_track(client: httpx.AsyncClient, track_data: Dict) -> Optional[Dict]:
    """Créer ou récupérer une piste avec mise à jour."""
    try:
        path = track_data.get("path")
        if not path:
            return None

        # Rechercher par chemin unique
        response = await client.get(
            "http://localhost:8001/api/tracks/search",
            params={"path": path}
        )

        if response.status_code == 200:
            tracks = response.json()
            if tracks:
                track = tracks[0]
                # Vérifier et mettre à jour les infos manquantes
                if update_missing_info(track, track_data):
                    response = await client.put(
                        f"http://localhost:8001/api/tracks/{track['id']}", 
                        json=track_data
                    )
                    if response.status_code == 200:
                        return response.json()
                return track

        # Créer nouvelle piste si non trouvée
        response = await client.post(
            "http://localhost:8001/api/tracks/",
            json=track_data
        )

        if response.status_code in (200, 201):
            track = response.json()
            track_cache[path] = track
            return track

        logger.error(f"Erreur création/mise à jour piste: {response.text}")
        return None

    except Exception as e:
        logger.error(f"Erreur pour piste {track_data.get('path')}: {str(e)}")
        return None



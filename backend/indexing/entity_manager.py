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
        musicbrainz_artistid = artist_data.get("musicbrainz_artistid") 

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

def clean_track_data(file: Dict) -> Dict:
    """Nettoie et valide les données de piste avant l'envoi."""
    track_data = {
        "title": file.get("title"),
        "path": file.get("path"),
        "duration": file.get("duration", 0),
        "track_number": file.get("track_number"),
        "disc_number": file.get("disc_number"),
        "year": file.get("year"),
        "genre": file.get("genre"),
        "file_type": file.get("file_type"),
        "bitrate": file.get("bitrate"),
        "featured_artists": file.get("featured_artists", ""),

        # Correction du mapping MusicBrainz
        "musicbrainz_id": file.get("musicbrain_id"),
        "musicbrainz_albumid": file.get("musicbrain_albumid"),
        "musicbrainz_artistid": file.get("musicbrain_artistid"),
        "musicbrainz_albumartistid": file.get("musicbrain_albumartistid"),
        "musicbrainz_genre": file.get("musicbrain_genre"),
        
        # Correction du mapping des caractéristiques audio
        "bpm": float(file.get("bpm")) if file.get("bpm") is not None else None,
        "key": file.get("key") if file.get("key") is not None else None,  # Déjà extrait par extract_audio_features
        "scale": file.get("scale") if file.get("scale") is not None else None,  # Déjà extrait par extract_audio_features
        "danceability": float(file.get("danceability")) if file.get("danceability") is not None else None,
        "mood_happy": float(file.get("mood_happy")) if file.get("mood_happy") is not None else None,
        "mood_aggressive": float(file.get("mood_aggressive")) if file.get("mood_aggressive") is not None else None,
        "mood_party": float(file.get("mood_party")) if file.get("mood_party") is not None else None,
        "mood_relaxed": float(file.get("mood_relaxed")) if file.get("mood_relaxed") is not None else None,
        "instrumental": bool(float(file.get("instrumental", 0)) > 0.5) if file.get("instrumental") is not None else None,
        "acoustic": bool(float(file.get("acoustic", 0)) > 0.5) if file.get("acoustic") is not None else None,
        "tonal": bool(float(file.get("tonal", 0)) > 0.5) if file.get("tonal") is not None else None,
        "genre_main": file.get("genre"),  # Utiliser le genre principal comme genre_main
        "genre_tags": file.get("genre_tags", []),
        "mood_tags": file.get("mood_tags", []),
        "acoustid_fingerprint": file.get("acoustid_fingerprint"),
        
        # Gestion des covers
        "cover_data": file.get("cover_data"),
        "cover_mime_type": file.get("cover_mime_type")
    }

    # Nettoyage supprimé car déjà fait lors de l'extraction

    return {k: v for k, v in track_data.items() if v is not None}

async def create_or_get_track(client: httpx.AsyncClient, track_data: Dict) -> Optional[Dict]:
    """Créer ou récupérer une piste avec mise à jour."""
    try:
        path = track_data.get("path")
        
        # Extraire et gérer séparément les tags
        genre_tags = track_data.pop("genre_tags", [])
        mood_tags = track_data.pop("mood_tags", [])
        
        # Nettoyer les données de base
        cleaned_data = clean_track_data(track_data)
        
        # Rajouter les tags sous forme de listes de noms
        if genre_tags:
            cleaned_data["genre_tags"] = [tag["name"] for tag in genre_tags]
        if mood_tags:
            cleaned_data["mood_tags"] = [tag["name"] for tag in mood_tags]
        
        if not path or not track_data.get("track_artist_id"):
            logger.error("Chemin ou ID d'artiste manquant")
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
                # Fusionner les données existantes avec les nouvelles données nettoyées
                merged_data = {**track}
                for key, value in cleaned_data.items():
                    if value is not None:  # Ne mettre à jour que si la nouvelle valeur n'est pas None
                        merged_data[key] = value

                # Vérifier si des mises à jour sont nécessaires
                if any(merged_data[k] != track[k] for k in merged_data if k in track):
                    logger.info(f"Mise à jour de la piste: {track['id']} - {track['title']}")
                    response = await client.put(
                        f"http://localhost:8001/api/tracks/{track['id']}", 
                        json=merged_data
                    )
                    if response.status_code == 200:
                        updated_track = response.json()
                        logger.info(f"Piste mise à jour avec succès: {updated_track['id']}")
                        return updated_track
                return track

        # Créer nouvelle piste avec les données nettoyées
        response = await client.post(
            "http://localhost:8001/api/tracks/",
            json=cleaned_data
        )

        if response.status_code in (200, 201):
            track = response.json()
            track_cache[path] = track
            logger.info(f"Nouvelle piste créée: {track['id']} - {track['title']}")
            return track

        logger.error(f"Erreur création/mise à jour piste: {response.text}")
        return None

    except Exception as e:
        logger.error(f"Erreur pour piste {track_data.get('path')}: {str(e)}")
        return None



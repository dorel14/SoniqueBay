from typing import Dict, Optional, List, Tuple
from cachetools import TTLCache
import httpx 
from pathlib import Path

from helpers.logging import logger
from backend.services.image_service import process_image_data, read_image_file, process_artist_image
from backend.services.path_service import get_artist_path, find_local_images, find_cover_in_directory
from backend.services.settings_service import SettingsService, ARTIST_IMAGE_FILES
from backend.api.schemas.covers_schema import CoverCreate, CoverType
from backend.services.lastfm_service import get_lastfm_artist_image
from backend.services.coverart_service import get_coverart_image


settings_service = SettingsService()

# Cache pour stocker les IDs (durée de vie 1 heure)
artist_cache = TTLCache(maxsize=100, ttl=3600)
album_cache = TTLCache(maxsize=100, ttl=3600)
genre_cache = TTLCache(maxsize=50, ttl=3600)
track_cache = TTLCache(maxsize=1000, ttl=3600)

async def create_or_update_cover(client: httpx.AsyncClient, entity_type: CoverType, entity_id: int, 
                            cover_data: str = None, mime_type: str = None, url: str = None) -> Optional[Dict]:
    """Crée ou met à jour une cover pour une entité."""
    try:
        if not cover_data:
            logger.debug(f"Pas de données cover pour {entity_type} {entity_id}")
            return None

        logger.info(f"Traitement cover pour {entity_type} {entity_id}")
        cover_create = CoverCreate(
            entity_type=entity_type.value,  # Utiliser la valeur str du enum
            entity_id=entity_id,
            cover_data=cover_data,
            mime_type=mime_type,
            url=url
        ).model_dump()

        try:
            # Essayer directement le PUT
            response = await client.put(
                f"http://localhost:8001/api/covers/{entity_type.value}/{entity_id}",
                json=cover_create
            )
            if response.status_code in (200, 201):
                logger.info(f"Cover mise à jour pour {entity_type} {entity_id}")
                return response.json()
        except Exception as e:
            logger.debug(f"PUT échoué, tentative de POST: {str(e)}")

        # Si le PUT échoue, essayer le POST
        try:
            response = await client.post(
                "http://localhost:8001/api/covers",
                json=cover_create,
                follow_redirects=True  # Important: suivre les redirections
            )
            if response.status_code in (200, 201):
                logger.info(f"Cover créée pour {entity_type} {entity_id}")
                return response.json()
        except Exception as e:
            logger.error(f"Erreur création cover: {str(e)}")

        return None

    except Exception as e:
        logger.error(f"Erreur gestion cover pour {entity_type} {entity_id}: {str(e)}")
        return None

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

async def create_or_get_artist(client: httpx.AsyncClient, artist_data: Dict) -> Optional[Dict]:
    """Créer ou récupérer un artiste."""
    try:
        logger.info(f"Données artiste reçues: {artist_data.get('name', 'Inconnu')}")
        name = artist_data.get("name")
        musicbrainz_artistid = artist_data.get("musicbrainz_artistid")
        
        if not name:
            logger.error(f"Nom d'artiste manquant dans les données")
            return None
            
        logger.info(f"Traitement artiste - Nom: {name}, MusicBrainz ID: {musicbrainz_artistid}")

        # Vérifier le cache d'abord
        cache_key = f"{name.lower()}:{musicbrainz_artistid}" if musicbrainz_artistid else name.lower()
        if cache_key in artist_cache:
            logger.debug("Artiste trouvé dans le cache: %s", name)
            return artist_cache[cache_key]

        # Recherche par MusicBrainz ID si disponible
        if musicbrainz_artistid:
            response = await client.get(
                "http://localhost:8001/api/artists/search",
                params={"musicbrainz_artistid": musicbrainz_artistid}
            )
            if response.status_code == 200:
                artists = response.json()
                if artists:
                    artist = artists[0]
                    artist_cache[cache_key] = artist
                    logger.info(f"Artiste trouvé par MusicBrainz ID: {artist['name']}")
                    return artist

        # Si pas trouvé par MusicBrainz ID, rechercher par nom
        response = await client.get(
            "http://localhost:8001/api/artists/search",
            params={"name": name}
        )

        # Si artiste trouvé par MusicBrainz ID ou nom
        if response.status_code == 200:
            artists = response.json()
            if artists:
                artist = artists[0]
                return artist

        # Pour la création d'un nouvel artiste
        logger.info(f"Création d'un nouvel artiste: {name}")
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
            logger.info(f"Nouvel artiste créé: {artist['name']}")

            # Essayer d'abord les images locales
            cover_added = False
            if artist_data.get("artist_path"):
                logger.info(f"Recherche d'images locales pour: {name}")
                cover_data = await process_artist_image(artist_data["artist_path"])
                if cover_data:
                    await create_or_update_cover(
                        client, CoverType.ARTIST, artist["id"],
                        cover_data=cover_data[0],
                        mime_type=cover_data[1],
                        url=artist_data["artist_path"]
                    )
                    cover_added = True

            # Si pas d'image locale, essayer Last.fm
            if not cover_added:
                logger.info(f"Tentative récupération image Last.fm pour: {name}")
                lastfm_cover = await get_lastfm_artist_image(client, name)
                if lastfm_cover:
                    await create_or_update_cover(
                        client, CoverType.ARTIST, artist["id"],
                        cover_data=lastfm_cover[0],
                        mime_type=lastfm_cover[1],
                        url=f"lastfm://{name}"
                    )

            return artist

        logger.error(f"Erreur création artiste {name}: {response.text}")
        return None

    except Exception as e:
        logger.error(f"Erreur pour artiste {name}: {str(e)}")
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
            
            # Gérer la cover album
            cover_added = False
            
            # 1. Essayer d'abord la cover locale
            if album_data.get("cover_data"):
                await create_or_update_cover(
                    client=client,
                    entity_type=CoverType.ALBUM,
                    entity_id=album["id"],
                    cover_data=album_data["cover_data"],
                    mime_type=album_data.get("cover_mime_type"),
                    url=str(Path(album_data["path"]).parent)
                )
                cover_added = True
            
            # 2. Si pas de cover locale, essayer Cover Art Archive
            if not cover_added and album_data.get("musicbrainz_albumid"):
                logger.info(f"Tentative récupération cover depuis Cover Art Archive")
                cover_data = await get_coverart_image(client, album_data["musicbrainz_albumid"])
                if cover_data:
                    await create_or_update_cover(
                        client=client,
                        entity_type=CoverType.ALBUM,
                        entity_id=album["id"],
                        cover_data=cover_data[0],
                        mime_type=cover_data[1],
                        url=f"coverart://{album_data['musicbrainz_albumid']}"
                    )
                    
            return album
        else:
            logger.error(f"Erreur création album: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Erreur create_or_get_album: {str(e)}")
        return None

def clean_track_data(file: Dict) -> Dict:
    """Nettoie et valide les données de piste avant l'envoi."""
    # Récupérer les IDs MusicBrainz pour la gestion de l'artiste album
    mb_artistid = file.get("musicbrain_artistid")
    mb_albumartistid = file.get("musicbrain_albumartistid")

    # Si l'artiste de l'album n'est pas spécifié, utiliser celui de la track
    if not mb_albumartistid and mb_artistid:
        mb_albumartistid = mb_artistid

    # Pour les tags, s'assurer qu'ils sont des strings
    genre_tags = file.get("genre_tags", [])
    mood_tags = file.get("mood_tags", [])

    if genre_tags and isinstance(genre_tags[0], (dict, object)):
        genre_tags = [str(tag.get('name', tag) if isinstance(tag, dict) else tag) for tag in genre_tags]

    if mood_tags and isinstance(mood_tags[0], (dict, object)):
        mood_tags = [str(tag.get('name', tag) if isinstance(tag, dict) else tag) for tag in mood_tags]

    track_data = {
        # Champs obligatoires pour la création de piste
        "title": file.get("title"),
        "path": file.get("path"),
        "track_artist_id": file.get("track_artist_id"),  # Champ requis
        "album_id": file.get("album_id"),  # Optionnel mais important
        
        # Autres champs
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
        "musicbrainz_artistid": mb_artistid,
        "musicbrainz_albumartistid": mb_albumartistid,
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
        "genre_tags": genre_tags,
        "mood_tags": mood_tags,
        "acoustid_fingerprint": file.get("acoustid_fingerprint"),

        # Gestion des covers
        "cover_data": file.get("cover_data"),
        "cover_mime_type": file.get("cover_mime_type")
    }

    # Nettoyage et filtrage des valeurs None
    cleaned_data = {k: v for k, v in track_data.items() if v is not None}
    
    # S'assurer que track_artist_id est présent
    if "track_artist_id" not in cleaned_data:
        logger.error("track_artist_id manquant dans les données de piste")
        return {}  # Retourner un dict vide si le champ requis est manquant

    return cleaned_data

async def create_or_get_track(client: httpx.AsyncClient, track_data: Dict) -> Optional[Dict]:
    """Créer ou récupérer une piste avec mise à jour."""
    try:
        path = track_data.get("path")
        
        # S'assurer que track_artist_id est présent avant le nettoyage
        if not track_data.get("track_artist_id"):
            logger.error("track_artist_id requis mais manquant")
            return None

        # Nettoyer les données de base
        cleaned_data = clean_track_data(track_data)
        if not cleaned_data:
            logger.error("Données de piste invalides après nettoyage")
            return None

        # La gestion des covers sera faite après la création/mise à jour de la track
        cover_data = cleaned_data.pop("cover_data", None)
        cover_mime_type = cleaned_data.pop("cover_mime_type", None)

        # Rechercher par chemin unique
        response = await client.get(
            "http://localhost:8001/api/tracks/search",
            params={"path": path}
        )

        # Mise à jour du track existant
        if response.status_code == 200:
            tracks = response.json()
            if tracks:
                track = tracks[0]
                merged_data = {**track}
                for key, value in cleaned_data.items():
                    if value is not None:
                        merged_data[key] = value
                
                # Log des données avant mise à jour
                logger.debug(f"Données à mettre à jour pour {track['id']}: {merged_data}")
                
                response = await client.put(
                    f"http://localhost:8001/api/tracks/{track['id']}", 
                    json=merged_data
                )
                
                if response.status_code != 200:
                    logger.error(f"Erreur mise à jour piste {track['id']}: {response.status_code}")
                    logger.error(f"Détails de l'erreur: {response.text}")
                    logger.error(f"Données envoyées: {merged_data}")

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

                # Gérer la cover après la mise à jour
                if cover_data:
                    await create_or_update_cover(
                        client=client,
                        entity_type=CoverType.TRACK,
                        entity_id=track["id"],
                        cover_data=cover_data,
                        mime_type=cover_mime_type,
                        url=str(Path(track_data["path"]).parent)  # Utiliser le dossier du fichier comme URL
                    )
                return track

        # Créer nouvelle piste
        response = await client.post(
            "http://localhost:8001/api/tracks/",
            json=cleaned_data
        )

        if response.status_code in (200, 201):
            track = response.json()
            track_cache[path] = track
            
            # Gérer la cover après la création
            if track_data.get("cover_data"):
                logger.info(f"Création/mise à jour cover pour track {track['id']}")
                cover_result = await create_or_update_cover(
                    client,
                    CoverType.TRACK,
                    track["id"],
                    cover_data=track_data["cover_data"],
                    mime_type=track_data.get("cover_mime_type")
                )
                if cover_result:
                    logger.info(f"Cover mise à jour pour track {track['id']}")

            logger.info(f"Nouvelle piste créée: {track['id']} - {track['title']}")
            return track

        logger.error(f"Erreur création/mise à jour piste: {response.text}")
        return None

    except Exception as e:
        logger.error(f"Erreur pour piste {track_data.get('path')}: {str(e)}")
        return None

async def process_artist_covers(client: httpx.AsyncClient, artist_id: int, 
                              artist_path: str, artist_images: List[Tuple[str, str]]) -> None:
    """Traite toutes les covers d'un artiste."""
    try:
        for cover_data, mime_type in artist_images:
            await create_or_update_cover(
                client=client,
                entity_type=CoverType.ARTIST,
                entity_id=artist_id,
                cover_data=cover_data,
                mime_type=mime_type,
                url=artist_path
            )
    except Exception as e:
        logger.error(f"Erreur traitement covers artiste {artist_id}: {str(e)}")



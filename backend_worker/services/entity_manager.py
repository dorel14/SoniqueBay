
from typing import Dict, Optional, List, Tuple
from cachetools import TTLCache
import httpx
import os
import redis
import json

from backend_worker.utils.logging import logger
from backend_worker.services.settings_service import SettingsService
from backend_worker.services.coverart_service import get_cover_schema, get_cover_types


def snake_to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def convert_dict_keys_to_camel(data):
    """Recursively convert dict keys from snake_case to camelCase."""
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_dict_keys_to_camel(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_dict_keys_to_camel(item) for item in data]
    else:
        return data


settings_service = SettingsService()

# Cache pour stocker les IDs (durée de vie 1 heure)
artist_cache = TTLCache(maxsize=100, ttl=3600)
album_cache = TTLCache(maxsize=100, ttl=3600)
genre_cache = TTLCache(maxsize=50, ttl=3600)
track_cache = TTLCache(maxsize=1000, ttl=3600)
api_url = os.getenv("API_URL", "http://backend:8001")

def publish_library_update():
    r = redis.Redis(host='redis', port=6379, db=0)
    r.publish("notifications", json.dumps({"type": "library_update"}))


async def execute_graphql_query(client: httpx.AsyncClient, query: str, variables: dict = None) -> dict:
    """
    Exécute une requête GraphQL de manière asynchrone.

    Args:
        client: Client HTTP asynchrone
        query: Requête GraphQL
        variables: Variables de la requête

    Returns:
        Résultat de la requête GraphQL

    Raises:
        Exception: En cas d'erreur GraphQL
    """
    graphql_url = f"{api_url}/api/graphql"

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = await client.post(
            graphql_url,
            json=payload,
            timeout=120  # Timeout plus long pour les opérations batch
        )

        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code} - {response.text}")

        result = await response.json()

        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get("data", {})

    except Exception as e:
        logger.error(f"Erreur GraphQL: {str(e)}")
        raise


async def create_or_update_cover(client: httpx.AsyncClient, entity_type: str, entity_id: int,
                             cover_data: str = None, mime_type: str = None, url: str = None,
                             cover_schema: dict = None) -> Optional[Dict]:
    """
    Crée ou met à jour une cover pour une entité avec gestion d'erreurs améliorée.

    Args:
        client: Client HTTP asynchrone
        entity_type: Type d'entité ('artist', 'album', 'track')
        entity_id: ID de l'entité
        cover_data: Données de l'image encodée
        mime_type: Type MIME de l'image
        url: URL source de l'image
        cover_schema: Schéma de validation (optionnel)

    Returns:
        Données de la cover créée/mise à jour ou None en cas d'erreur
    """
    try:
        # Validation des paramètres d'entrée
        if not entity_type or not isinstance(entity_id, int) or entity_id <= 0:
            logger.error(f"Paramètres invalides: entity_type={entity_type}, entity_id={entity_id}")
            return None

        if not cover_data:
            logger.debug(f"Pas de données cover pour {entity_type} {entity_id}")
            return None

        if not mime_type:
            logger.warning(f"Type MIME manquant pour {entity_type} {entity_id}")
            # Essayer de deviner le type MIME depuis les données
            if cover_data.startswith('data:image/'):
                mime_type = cover_data.split(';')[0].split(':')[1]
            else:
                mime_type = 'image/jpeg'  # Valeur par défaut

        # Récupération du schéma si non fourni
        if not cover_schema:
            try:
                cover_schema = await get_cover_schema()
            except Exception as e:
                logger.error(f"Erreur récupération schéma cover: {str(e)}")
                return None

        # Validation du type d'entité
        try:
            covertype = await get_cover_types()
            if entity_type not in covertype:
                logger.error(f"Type de cover non supporté: {entity_type} (supportés: {covertype})")
                return None
        except Exception as e:
            logger.error(f"Erreur récupération types de cover: {str(e)}")
            return None

        logger.info(f"Traitement cover pour {entity_type} {entity_id} ({mime_type})")

        # Préparation des données
        all_args = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "cover_data": cover_data,
            "mime_type": mime_type,
            "url": url,
        }

        # Filtrage selon le schéma
        properties = cover_schema.get("properties", {})
        cover_create = {
            field: all_args[field]
            for field in properties
            if field in all_args and all_args[field] is not None
        }

        # Nettoyer les données base64 si nécessaire
        if cover_data.startswith('data:image/'):
            cover_create["cover_data"] = cover_data.split(',')[1]

        # Tentative de mise à jour (PUT)
        try:
            response = await client.put(
                f"{api_url}/api/covers/{entity_type}/{entity_id}",
                json=cover_create,
                timeout=60,  # Timeout plus long pour les uploads
            )

            if response.status_code in (200, 201):
                result = await response.json()
                logger.info(f"Cover mise à jour pour {entity_type} {entity_id}")
                return result
            elif response.status_code == 404:
                logger.debug(f"Cover n'existe pas pour {entity_type} {entity_id}, tentative de création")
            else:
                logger.warning(f"PUT échoué pour {entity_type} {entity_id}: {response.status_code} - {response.text}")

        except httpx.TimeoutException:
            logger.warning(f"Timeout PUT pour {entity_type} {entity_id}")
        except Exception as e:
            logger.debug(f"PUT échoué pour {entity_type} {entity_id}, tentative POST: {str(e)}")

        # Tentative de création (POST) si PUT a échoué
        try:
            response = await client.post(
                f"{api_url}/api/covers",
                json=cover_create,
                timeout=60,
                follow_redirects=True
            )

            if response.status_code in (200, 201):
                result = await response.json()
                logger.info(f"Cover créée pour {entity_type} {entity_id}")
                return result
            else:
                logger.error(f"POST échoué pour {entity_type} {entity_id}: {response.status_code} - {response.text}")
                return None

        except httpx.TimeoutException:
            logger.error(f"Timeout POST pour {entity_type} {entity_id}")
            return None
        except Exception as e:
            logger.error(f"Erreur POST pour {entity_type} {entity_id}: {str(e)}")
            return None

    except Exception as e:
        logger.error(f"Erreur générale gestion cover pour {entity_type} {entity_id}: {str(e)}")
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
            f"{api_url}/api/genres/search",
            params={"name": genre_name},
            timeout=10
        )

        if response.status_code == 200:
            genres = await response.json()
            if genres:


                genre = genres[0]
                genre_cache[genre_name.lower()] = genre
                logger.debug(f"Genre trouvé: {genre_name}")
                return genre

        # Créer le genre s'il n'existe pas
        create_data = {"name": genre_name}
        response = await client.post(
            f"{api_url}/api/genres/",
            json=create_data,
            timeout=10
        )

        if response.status_code in (200, 201):
            genre = await response.json()
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

async def create_or_get_artists_batch(client: httpx.AsyncClient, artists_data: List[Dict]) -> Dict[str, Dict]:
    """
    Crée ou récupère une liste d'artistes en une seule requête GraphQL (batch).

    Args:
        client: Client HTTP asynchrone
        artists_data: Liste des données d'artistes

    Returns:
        Dictionnaire des artistes créés/récupérés
    """
    try:
        if not artists_data:
            logger.info("Traitement en batch de 0 artistes.")
            return {}

        logger.info(f"Traitement en batch de {len(artists_data)} artistes via GraphQL")

        # Construire la mutation GraphQL
        mutation = """
        mutation CreateArtists($artists: [ArtistCreateInput!]!) {
            createArtists(data: $artists) {
                id
                name
                musicbrainzArtistid
            }
        }
        """

        # Convertir les clés snake_case en camelCase pour GraphQL
        converted_artists_data = convert_dict_keys_to_camel(artists_data)
        variables = {"artists": converted_artists_data}
        logger.debug(f"GraphQL variables for CreateArtists: {variables}")

        # Exécuter la requête GraphQL
        result = await execute_graphql_query(client, mutation, variables)

        if "createArtists" in result:
            artists = result["createArtists"]
            # Créer un dictionnaire pour un accès facile par nom ou mbid
            artist_map = {
                (artist.get('musicbrainzArtistid') or artist['name'].lower()): artist
                for artist in artists
            }
            logger.info(f"{len(artists)} artistes traités avec succès en batch via GraphQL")
            publish_library_update()  # Publier la mise à jour de la bibliothèque
            return artist_map
        else:
            logger.error(f"Réponse GraphQL inattendue: {result}")
            return {}

    except Exception as e:
        logger.error(f"Erreur lors du traitement en batch des artistes: {str(e)}")
        return {}

async def create_or_get_albums_batch(client: httpx.AsyncClient, albums_data: List[Dict]) -> Dict[str, Dict]:
    """
    Crée ou récupère une liste d'albums en une seule requête GraphQL (batch).

    Args:
        client: Client HTTP asynchrone
        albums_data: Liste des données d'albums

    Returns:
        Dictionnaire des albums créés/récupérés
    """
    try:
        if not albums_data:
            return {}

        logger.info(f"Traitement en batch de {len(albums_data)} albums via GraphQL")

        # Construire la mutation GraphQL
        mutation = """
        mutation CreateAlbums($albums: [AlbumCreateInput!]!) {
            createAlbums(data: $albums) {
                id
                title
                albumArtistId
                releaseYear
                musicbrainzAlbumid
            }
        }
        """

        # Convertir les clés snake_case en camelCase pour GraphQL
        converted_albums_data = convert_dict_keys_to_camel(albums_data)
        variables = {"albums": converted_albums_data}

        # Exécuter la requête GraphQL
        result = await execute_graphql_query(client, mutation, variables)

        if "createAlbums" in result:
            albums = result["createAlbums"]
            # Clé: (titre, artist_id) ou mbid
            album_map = {
                (album.get('musicbrainzAlbumid') or (album['title'].lower(), album['albumArtistId'])): album
                for album in albums
            }
            logger.info(f"{len(albums)} albums traités avec succès en batch via GraphQL")
            publish_library_update()  # Publier la mise à jour de la bibliothèque
            return album_map
        else:
            logger.error(f"Réponse GraphQL inattendue: {result}")
            return {}

    except Exception as e:
        logger.error(f"Exception lors du traitement en batch des albums: {str(e)}")
        return {}

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

    # Gestion spécifique des tags
    if isinstance(file.get("genre_tags"), str):
        genre_tags = [tag.strip() for tag in file["genre_tags"].split(",")]
    else:
        genre_tags = file.get("genre_tags", [])

    if isinstance(file.get("mood_tags"), str):
        mood_tags = [tag.strip() for tag in file["mood_tags"].split(",")]
    else:
        mood_tags = file.get("mood_tags", [])

    def convert_to_bool(value) -> Optional[bool]:
        """Convertit une valeur en booléen selon un seuil."""
        try:
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                try:
                    float_val = float(value)
                    # Conversion explicite en bool
                    return bool(float_val > 0.5)
                except Exception:
                    return None
            return None
        except Exception:
            return None

    def safe_float(value) -> Optional[float]:
        """Convertit une valeur en float de manière sécurisée."""
        try:
            return float(value) if value is not None else None
        except Exception:
            return None

    # Correction du mapping MusicBrainz avec les bonnes clés
    mb_data = file.get("musicbrainz_data", {}) or {}  # Récupérer les données MusicBrainz

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

        # Correction du mapping MusicBrainz avec les bonnes clés
        "musicbrainz_id": mb_data.get("musicbrainz_id") or file.get("musicbrainz_id"),
        "musicbrainz_albumid": mb_data.get("musicbrainz_albumid") or file.get("musicbrainz_albumid"),
        "musicbrainz_artistid": mb_data.get("musicbrainz_artistid") or file.get("musicbrainz_artistid"),
        "musicbrainz_albumartistid": mb_data.get("musicbrainz_albumartistid") or file.get("musicbrainz_albumartistid"),
        "musicbrainz_genre": mb_data.get("musicbrainz_genre") or file.get("musicbrainz_genre"),
        "acoustid_fingerprint": mb_data.get("acoustid_fingerprint") or file.get("acoustid_fingerprint"),
        
        # Caractéristiques audio avec conversion appropriée
        "bpm": safe_float(file.get("bpm")),
        "key": file.get("key"),
        "scale": file.get("scale"),
        "danceability": safe_float(file.get("danceability")),
        "mood_happy": safe_float(file.get("mood_happy")),
        "mood_aggressive": safe_float(file.get("mood_aggressive")),
        "mood_party": safe_float(file.get("mood_party")),
        "mood_relaxed": safe_float(file.get("mood_relaxed")),
        
        # Garder les valeurs flottantes telles quelles
        "instrumental": safe_float(file.get("instrumental")),
        "acoustic": safe_float(file.get("acoustic")),
        "tonal": safe_float(file.get("tonal")),
        
        # S'assurer que les tags sont des listes
        "genre_tags": genre_tags,
        "mood_tags": mood_tags,
    }

    # Log pour debug
    logger.debug(f"Valeurs booléennes avant nettoyage: {file.get('instrumental')}, {file.get('acoustic')}, {file.get('tonal')}")
    logger.debug(f"Valeurs booléennes après conversion: {track_data['instrumental']}, {track_data['acoustic']}, {track_data['tonal']}")

    # Nettoyer les valeurs invalides
    cleaned_data = {
        k: v for k, v in track_data.items() 
        if v is not None and (
            isinstance(v, bool) or 
            isinstance(v, (int, float)) or 
            (isinstance(v, str) and v.strip()) or
            (isinstance(v, list) and v)
        )
    }

    # Ajouter un log pour les IDs MusicBrainz
    mb_ids = {k: v for k, v in cleaned_data.items() if k.startswith('musicbrainz_') and v}
    if mb_ids:
        logger.info(f"IDs MusicBrainz trouvés: {mb_ids}")

    return cleaned_data

async def create_or_update_tracks_batch(client: httpx.AsyncClient, tracks_data: List[Dict]) -> List[Dict]:
    """
    Crée ou met à jour une liste de pistes en une seule requête GraphQL (batch).

    Args:
        client: Client HTTP asynchrone
        tracks_data: Liste des données de pistes

    Returns:
        Liste des pistes traitées
    """
    try:
        if not tracks_data:
            return []

        logger.info(f"Traitement en batch de {len(tracks_data)} pistes via GraphQL")

        # Nettoyer les données avant de les envoyer
        cleaned_tracks_data = [clean_track_data(track) for track in tracks_data]

        # Construire la mutation GraphQL
        mutation = """
        mutation CreateTracks($tracks: [TrackCreateInput!]!) {
            createTracks(data: $tracks) {
                id
                title
                path
                trackArtistId
                albumId
                duration
                trackNumber
                discNumber
                year
                genre
                fileType
                bitrate
                featuredArtists
                bpm
                key
                scale
                danceability
                moodHappy
                moodAggressive
                moodParty
                moodRelaxed
                instrumental
                acoustic
                tonal
                camelotKey
                genreMain
                musicbrainzId
                musicbrainzAlbumid
                musicbrainzArtistid
                musicbrainzAlbumartistid
                acoustidFingerprint
            }
        }
        """

        # Convertir les clés snake_case en camelCase pour GraphQL
        converted_tracks_data = convert_dict_keys_to_camel(cleaned_tracks_data)
        variables = {"tracks": converted_tracks_data}

        # Exécuter la requête GraphQL
        result = await execute_graphql_query(client, mutation, variables)

        if "createTracks" in result:
            processed_tracks = result["createTracks"]
            logger.info(f"{len(processed_tracks)} pistes traitées avec succès en batch via GraphQL")
            return processed_tracks
        else:
            logger.error(f"Réponse GraphQL inattendue: {result}")
            return []

    except Exception as e:
        logger.error(f"Exception lors du traitement en batch des pistes: {str(e)}")
        return []

async def process_artist_covers(client: httpx.AsyncClient, artist_id: int,
                             artist_path: str, artist_images: List[Tuple[str, str]]) -> None:
    """
    Traite toutes les covers d'un artiste avec gestion d'erreurs améliorée.

    Args:
        client: Client HTTP asynchrone
        artist_id: ID de l'artiste
        artist_path: Chemin vers le dossier de l'artiste
        artist_images: Liste de tuples (données_cover, type_mime)
    """
    if not artist_images:
        logger.debug(f"Aucune image cover pour l'artiste {artist_id}")
        return

    logger.info(f"Traitement de {len(artist_images)} covers pour l'artiste {artist_id}")

    successful = 0
    failed = 0

    for i, (cover_data, mime_type) in enumerate(artist_images):
        try:
            if not cover_data or not mime_type:
                logger.warning(f"Données cover invalides pour artiste {artist_id}, image {i}")
                failed += 1
                continue

            # Validation basique du type MIME
            if not mime_type.startswith('image/'):
                logger.warning(f"Type MIME invalide pour artiste {artist_id}: {mime_type}")
                failed += 1
                continue

            result = await create_or_update_cover(
                client=client,
                entity_type="artist",
                entity_id=artist_id,
                cover_data=cover_data,
                mime_type=mime_type,
                url=artist_path
            )

            if result:
                successful += 1
                logger.debug(f"Cover {i+1}/{len(artist_images)} traitée pour artiste {artist_id}")
            else:
                failed += 1
                logger.warning(f"Échec traitement cover {i+1} pour artiste {artist_id}")

        except Exception as e:
            failed += 1
            logger.error(f"Exception traitement cover {i+1} pour artiste {artist_id}: {str(e)}")

    logger.info(f"Covers artiste {artist_id}: {successful} succès, {failed} échecs")

    # Publier une mise à jour si au moins une cover a été traitée
    if successful > 0:
        try:
            publish_library_update()
        except Exception as e:
            logger.error(f"Erreur publication mise à jour artiste {artist_id}: {str(e)}")
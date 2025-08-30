# -*- coding: utf-8 -*-

from pathlib import Path
from mutagen import File
import mimetypes
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import os
from backend_worker.utils.logging import logger
import base64
from backend_worker.services.settings_service import SettingsService, ALBUM_COVER_FILES, ARTIST_IMAGE_FILES, MUSIC_PATH_TEMPLATE
import json
import aiofiles
import asyncio
from backend_worker.services.audio_features_service import extract_audio_features



settings_service = SettingsService()

def get_file_type(file_path: str) -> str:
    """Détermine le type de fichier à partir de son extension."""
    try:
        mime_type, encoding = mimetypes.guess_type(file_path)
        logger.debug(f"get_file_type for {file_path}: mime_type={mime_type}, encoding={encoding}")
        if mime_type is None:
            logger.warning("Type de fichier inconnu pour %s", file_path)
            return "unknown"
        # Normalize common variants
        if mime_type == "audio/x-flac":
            mime_type = "audio/flac"
        return mime_type
    except Exception as e:
        logger.error("Erreur lors de la détermination du type de fichier %s: %s", file_path, str(e))
        return "unknown"


async def get_cover_art(file_path_str: str, audio):
    """Récupère la pochette d'album d'un objet audio Mutagen."""
    try:
        if audio is None:
            logger.warning(f"Objet audio non valide pour: {file_path_str}")
            return None, None

        cover_data = None
        mime_type = None

        # 1. Essayer d'abord d'extraire la cover intégrée
        # Pour MP3 (ID3)
        if 'APIC:' in audio:
            apic = audio['APIC:']
            mime_type = apic.mime
            cover_data = await convert_to_base64(apic.data, mime_type)
            logger.debug(f"Cover MP3 extraite de {file_path_str}")
        # Pour FLAC et autres
        elif hasattr(audio, 'pictures') and audio.pictures:
            try:
                if hasattr(audio, 'pictures') and audio.pictures:
                    picture = audio.pictures[0]
                    mime_type = picture.mime
                    cover_data = await convert_to_base64(picture.data, mime_type)
                    logger.debug(f"Cover FLAC extraite: {file_path_str}")
            except Exception as e:
                logger.error(f"Erreur lecture cover FLAC: {str(e)}")

        # 2. Si pas de cover intégrée, chercher dans le dossier
        if not cover_data:
            try:
                dir_path = Path(file_path_str).parent
                # Récupérer la liste des noms de fichiers de cover depuis les paramètres
                cover_files_json = await settings_service.get_setting(ALBUM_COVER_FILES)
                cover_files = json.loads(cover_files_json)

                for cover_file in cover_files:
                    cover_path = dir_path / cover_file
                    if cover_path.exists():
                        mime_type = mimetypes.guess_type(str(cover_path))[0] or 'image/jpeg'
                        async with aiofiles.open(cover_path, mode='rb') as f:
                            cover_bytes = await f.read()
                            cover_data = await convert_to_base64(cover_bytes, mime_type)
                            logger.debug(f"Cover fichier trouvée: {cover_path}")
                            break
            except Exception as e:
                logger.error(f"Erreur lecture fichier cover: {str(e)}")

        if cover_data:
            logger.info(f"Cover extraite avec succès - Type: {mime_type}")
        else:
            logger.warning(f"Aucune cover trouvée pour: {file_path_str}")
        logger.debug(f"get_cover_art returns: {type(cover_data)}")
        return cover_data, mime_type

    except Exception as e:
        logger.error(f"Erreur extraction cover: {str(e)}")
        return None, None

async def convert_to_base64(data: bytes, mime_type: str) -> str:
    """Convertit des données binaires en chaîne base64 avec le type MIME."""
    try:
        base64_data = base64.b64encode(data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        logger.error(f"Erreur conversion base64: {str(e)}")
        return None

def get_file_bitrate(file_path: str) -> int:
    """Récupère le bitrate d'un fichier audio."""
    try:
        filetype = get_file_type(file_path)

        if filetype == "audio/mpeg":
            audio = MP3(file_path)
            return int(audio.info.bitrate / 1000)  # Convertir en kbps

        elif filetype in ["audio/flac", "audio/x-flac"]:
            audio = FLAC(file_path)
            if hasattr(audio.info, 'bits_per_sample') and hasattr(audio.info, 'sample_rate'):
                # Pour FLAC, calculer le bitrate approximatif
                return int((audio.info.bits_per_sample * audio.info.sample_rate) / 1000)

        return 0

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du bitrate pour {file_path}: {str(e)}")
        return 0

def get_musicbrainz_tags(audio):
    """Extrait les IDs MusicBrainz."""
    mb_data = {
        "musicbrainz_id": None,
        "musicbrainz_albumid": None,
        "musicbrainz_artistid": None,
        "musicbrainz_albumartistid": None,
        "acoustid_fingerprint": None
    }
    
    try:
        if not audio or not audio.tags:
            return mb_data

        # Mapping des tags MusicBrainz
        mb_mapping = {
            "musicbrainz_id": ["UFID:http://musicbrainz.org", "MUSICBRAINZ_TRACKID"],
            "musicbrainz_albumid": ["MUSICBRAINZ_ALBUMID", "TXXX:MusicBrainz Album Id"],
            "musicbrainz_artistid": ["MUSICBRAINZ_ARTISTID", "TXXX:MusicBrainz Artist Id"],
            "musicbrainz_albumartistid": ["MUSICBRAINZ_ALBUMARTISTID", "TXXX:MusicBrainz Album Artist Id"],
            "acoustid_fingerprint": ["ACOUSTID_FINGERPRINT", "TXXX:Acoustid Fingerprint"]
        }

        for field, tags in mb_mapping.items():
            for tag in tags:
                value = None
                if hasattr(audio.tags, "getall"):  # ID3
                    frames = audio.tags.getall(tag)
                    if frames:
                        value = str(frames[0])
                elif hasattr(audio.tags, "get"):  # Autres formats
                    value = audio.tags.get(tag, [None])[0]

                if value:
                    mb_data[field] = str(value)
                    break

        return mb_data

    except Exception as e:
        logger.error(f"Erreur extraction MusicBrainz: {str(e)}")
        return mb_data


async def extract_metadata(audio, file_path_str: str):
    """Extrait les métadonnées d'un objet audio Mutagen."""
    try:
        # L'objet 'audio' est déjà chargé, on l'utilise directement
        cover_data, mime_type = await get_cover_art(file_path_str, audio=audio)
        
        # Extraire les métadonnées musicales de base
        metadata = {
            "path": file_path_str,
            "title": get_tag(audio, "title") or Path(file_path_str).stem,
            "artist": get_tag(audio, "artist") or get_tag(audio, "TPE1") or get_tag(audio, "TPE2"),
            "album": get_tag(audio, "album") or Path(file_path_str).parent.name,
            "genre": get_tag(audio, "genre"),
            "year": get_tag(audio, "date") or get_tag(audio, "TDRC"),
            "track_number": get_tag(audio, "tracknumber") or get_tag(audio, "TRCK"),
            "disc_number": get_tag(audio, "discnumber") or get_tag(audio, "TPOS"),
            "duration": int(audio.info.length) if hasattr(audio.info, 'length') else 0,
            "file_type": get_file_type(file_path_str),
            "bitrate": int(audio.info.bitrate / 1000) if hasattr(audio.info, 'bitrate') and audio.info.bitrate else 0,
            "cover_data": cover_data,
            "cover_mime_type": mime_type,
            "tags": serialize_tags(audio.tags) if audio and hasattr(audio, "tags") else {},
        }

        # La logique des tags est maintenant gérée par extract_audio_features
        results = await extract_audio_features(
            audio=audio,
            tags=serialize_tags(audio.tags) if audio and hasattr(audio, "tags") else {},
            file_path=file_path_str
        )
        logger.debug(f"Résultats de l'extraction des caractéristiques audio: {results}")
        logger.debug(f"extract_audio_features type: {type(results)}")  # Doit être <class 'dict'>
        metadata.update(results)

        if metadata.get("genre_tags"):
            logger.info(f"Genre tags trouvés: {metadata['genre_tags']}")
        if metadata.get("mood_tags"):
            logger.info(f"Mood tags trouvés: {metadata['mood_tags']}")

        # Extraire les données MusicBrainz
        mb_data = get_musicbrainz_tags(audio)

        metadata.update({
            # S'assurer que les IDs sont au bon endroit
            "musicbrainz_artistid": mb_data.get("musicbrainz_artistid"),
            "musicbrainz_albumartistid": mb_data.get("musicbrainz_albumartistid"),
            "musicbrainz_albumid": mb_data.get("musicbrainz_albumid"),
            "musicbrainz_id": mb_data.get("musicbrainz_id"),
            "acoustid_fingerprint": mb_data.get("acoustid_fingerprint")
        })

        # Log des IDs trouvés
        mb_ids = {k: v for k, v in mb_data.items() if v}
        if mb_ids:
            logger.info(f"IDs MusicBrainz trouvés pour {file_path_str}: {mb_ids}")

        # Ne pas filtrer les valeurs numériques à 0 ou booléennes False
        metadata = {k: v for k, v in metadata.items() if v is not None}

        logger.debug(f"Métadonnées complètes pour {file_path_str}")
        logger.debug(f"extract_metadata returns: {type(metadata)}")
        return metadata

    except Exception as e:
        logger.error(f"Erreur d'extraction des métadonnées pour {file_path_str}: {str(e)}")
        return {"path": file_path_str, "error": str(e)}

async def get_artist_images(artist_path: str) -> list[tuple[str, str]]:
    """Récupère les images d'artiste dans le dossier artiste."""
    try:
        artist_images = []
        dir_path = Path(artist_path)

        if not dir_path.exists():
            logger.debug(f"Dossier artiste non trouvé: {artist_path}")
            return []

        # Récupérer la liste des noms de fichiers d'artiste depuis les paramètres
        artist_files_json = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        artist_files = json.loads(artist_files_json)

        for image_file in artist_files:
            image_path = dir_path / image_file
            if image_path.exists():
                try:
                    mime_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'
                    async with aiofiles.open(image_path, mode='rb') as f:
                        image_bytes = await f.read()
                        image_data = await convert_to_base64(image_bytes, mime_type)
                        if image_data:
                            artist_images.append((image_data, mime_type))
                            logger.debug(f"Image artiste trouvée: {image_path}")
                except Exception as e:
                    logger.error(f"Erreur lecture image artiste {image_path}: {str(e)}")
                    continue
        logger.debug(f"get_artist_images returns: {type(artist_images)}")
        return artist_images

    except Exception as e:
        logger.error(f"Erreur recherche images artiste dans {artist_path}: {str(e)}")
        return []

async def process_file(file_path_bytes, scan_config: dict, artist_images_cache: dict, cover_cache: dict):
    """
    Traite un fichier musical à partir de son chemin en bytes.
    Retourne un dictionnaire de métadonnées ou None si erreur.
    """
    file_path_str = file_path_bytes.decode('utf-8', 'surrogateescape')
    file_path = Path(file_path_str)

    try:
        if file_path.suffix.lower().encode('utf-8') not in scan_config["music_extensions"]:
            return None

        loop = asyncio.get_running_loop()
        try:
            with open(file_path_bytes, 'rb') as f:
                audio = await loop.run_in_executor(None, lambda: File(f, easy=False))
        except FileNotFoundError:
            logger.error(f"Fichier non trouvé: {file_path_str}")
            return None
        except Exception as e:
            logger.error(f"Erreur de lecture Mutagen pour {file_path_str}: {e}")
            return None
        
        if audio is None:
            logger.warning(f"Impossible de lire les données audio du fichier: {file_path_str}")
            return None

        parts = file_path.parts
        artist_depth = scan_config["artist_depth"]
        artist_path = Path(*parts[:artist_depth+1]) if artist_depth > 0 and len(parts) > artist_depth else file_path.parent
        artist_path_str = str(artist_path)

        artist_images = []
        if artist_path_str in artist_images_cache:
            artist_images = artist_images_cache[artist_path_str]
        elif artist_path.exists():
            # Note: get_artist_images appelle toujours settings_service. On pourrait optimiser davantage.
            artist_images = await get_artist_images(artist_path_str)
            artist_images_cache[artist_path_str] = artist_images

        metadata = await extract_metadata(audio, file_path_str)
        metadata["artist_path"] = artist_path_str
        metadata["artist_images"] = artist_images

        logger.debug(f"Métadonnées extraites pour {file_path_str}")
        return metadata

    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier {file_path_str}: {str(e)}", exc_info=True)
        return None


async def async_walk(path: Path):
    """Générateur asynchrone pour parcourir les fichiers, basé sur os.walk."""
    loop = asyncio.get_running_loop()
    for dirpath, dirnames, filenames in await loop.run_in_executor(None, os.walk, path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            if not filename.startswith('.'):
                yield os.path.join(dirpath, filename).encode('utf-8', 'surrogateescape')

async def scan_music_files(directory: str, scan_config: dict):
    """Générateur asynchrone qui scanne les fichiers musicaux et yield leurs métadonnées."""
    path = Path(directory)
    artist_images_cache = {}
    cover_cache = {}
    
    semaphore = asyncio.Semaphore(20)

    async def process_and_yield(file_path_bytes):
        async with semaphore:
            return await process_file(
                file_path_bytes, scan_config, artist_images_cache, cover_cache
            )

    tasks = []
    async for file_path_bytes in async_walk(path):
        file_suffix = Path(file_path_bytes.decode('utf-8', 'surrogateescape')).suffix.lower().encode('utf-8')
        if file_suffix in scan_config["music_extensions"]:
            tasks.append(process_and_yield(file_path_bytes))
            if len(tasks) >= 100:
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        yield res
                tasks = []

    if tasks:
        results = await asyncio.gather(*tasks)
        for res in results:
            if res:
                yield res

def get_tag_list(audio, tag_name: str) -> list:
    """Récupère une liste de tags."""
    try:
        values = set()  # Utiliser un set pour éviter les doublons
        
        if not audio or not audio.tags:
            return []

        # 1. Essayer les tags ID3
        if hasattr(audio.tags, "getall"):
            frames = audio.tags.getall(tag_name)
            for frame in frames:
                if hasattr(frame, "text"):  # ID3v2
                    values.update(str(t).strip() for t in frame.text if t)
                else:  # Autres formats
                    values.add(str(frame).strip())

        # 2. Essayer les tags génériques
        elif hasattr(audio.tags, "get"):
            tag_values = audio.tags.get(tag_name, [])
            if isinstance(tag_values, list):
                for value in tag_values:
                    if isinstance(value, str):
                        values.update(v.strip() for v in value.split(","))
                    else:
                        values.add(str(value).strip())
            elif tag_values:
                values.update(str(tag_values).split(","))

        result = [v for v in values if v]
        if result:
            logger.debug(f"Tags {tag_name} trouvés: {result}")
        return result

    except Exception as e:
        logger.debug(f"Erreur lecture tag liste {tag_name}: {str(e)}")
        return []

def get_tag(audio, tag_name):
    """Récupère une tag de manière sécurisée."""
    try:
        if not hasattr(audio, 'tags') or not audio.tags:
            logger.debug(f"get_tag: no tags for {tag_name}")
            return None

        # ID3 tags
        if hasattr(audio.tags, 'getall'):
            logger.debug(f"get_tag: trying getall for {tag_name}")
            try:
                frames = audio.tags.getall(tag_name)
                if frames:
                    value = str(frames[0])
                    logger.debug(f"Tag ID3 trouvé {tag_name}: {value}")
                    return value
            except AttributeError as ae:
                logger.debug(f"get_tag: getall AttributeError for {tag_name}: {ae}")

        # Tags génériques
        if hasattr(audio.tags, 'get'):
            logger.debug(f"get_tag: trying get for {tag_name}")
            value = audio.tags.get(tag_name, [""])[0]
            if value:
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                logger.debug(f"Tag générique trouvé {tag_name}: {value}")
                return str(value)

        logger.debug(f"get_tag: no value found for {tag_name}")
        return None

    except Exception as e:
        logger.debug(f"Erreur lecture tag {tag_name}: {str(e)}")
        return None
def serialize_tags(tags):
    """Convertit un objet tags Mutagen en dict simple JSON-serializable."""
    if tags is None:
        logger.debug("serialize_tags: tags is None")
        return {}
    # Pour ID3 (MP3)
    if hasattr(tags, "keys"):
        logger.debug("serialize_tags: has keys, processing ID3")
        result = {}
        for key in tags.keys():
            value = tags.get(key)
            # value peut être une liste, un objet, etc.
            if isinstance(value, list):
                result[key] = [str(v) for v in value]
            else:
                result[key] = str(value)
        return result
    # Pour d'autres formats
    logger.debug("serialize_tags: trying dict(tags)")
    try:
        return dict(tags)
    except Exception as e:
        logger.debug(f"serialize_tags: dict failed {e}, trying str")
        try:
            return str(tags)
        except Exception as e2:
            logger.debug(f"serialize_tags: str also failed {e2}")
            return "unserializable tags object"
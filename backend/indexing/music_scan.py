# -*- coding: utf-8 -*-

from pathlib import Path
from mutagen import File
import mimetypes
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from helpers.logging import logger
import base64
from backend.api.services.settings_service import SettingsService, ALBUM_COVER_FILES, ARTIST_IMAGE_FILES, MUSIC_PATH_TEMPLATE
import json
import aiofiles
from backend.services.path_variables import PathVariables

settings_service = SettingsService()

def get_file_type(file_path: str) -> str:
    """Détermine le type de fichier à partir de son extension."""
    try:
        mime_type, encoding = mimetypes.guess_type(file_path)
        if mime_type is None:
            logger.warning("Type de fichier inconnu pour %s", file_path)
            return "unknown"
        return mime_type
    except Exception as e:
        logger.error("Erreur lors de la détermination du type de fichier %s: %s", file_path, str(e))
        return "unknown"


async def get_cover_art(file_path: str):
    """Récupère la pochette d'album d'un fichier audio."""
    try:
        logger.info(f"Extraction de la cover pour: {file_path}")
        audio = File(file_path, easy=True)
        if audio is None:
            logger.warning(f"Impossible de lire le fichier: {file_path}")
            return None, None

        filetype = get_file_type(file_path)
        cover_data = None
        mime_type = None

        # 1. Essayer d'abord d'extraire la cover intégrée
        if filetype == "audio/mpeg":
            try:
                tags = ID3(file_path)
                if tags and tags.get('APIC:'):
                    apic = tags.get('APIC:')
                    mime_type = apic.mime
                    cover_data = await convert_to_base64(apic.data, mime_type)
                    logger.debug(f"Cover MP3 extraite: {file_path}")
            except Exception as e:
                logger.error(f"Erreur lecture cover MP3: {str(e)}")

        elif filetype in ["audio/flac", "audio/x-flac"]:
            try:
                if hasattr(audio, 'pictures') and audio.pictures:
                    picture = audio.pictures[0]
                    mime_type = picture.mime
                    cover_data = await convert_to_base64(picture.data, mime_type)
                    logger.debug(f"Cover FLAC extraite: {file_path}")
            except Exception as e:
                logger.error(f"Erreur lecture cover FLAC: {str(e)}")

        # 2. Si pas de cover intégrée, chercher dans le dossier
        if not cover_data:
            try:
                dir_path = Path(file_path).parent
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
            logger.warning(f"Aucune cover trouvée pour: {file_path}")
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
def extract_audio_features(audio, tags):
    """Extrait les caractéristiques audio avancées."""
    features = {}

    # Mapping des clés AcoustID vers les noms de champs de la base de données
    tag_mapping = {
        'ab:hi:danceability:danceable': 'danceability',
        'ab:lo:rhythm:bpm': 'bpm',
        'ab:lo:tonal:key_key': 'key',
        'ab:lo:tonal:key_scale': 'scale',
        'ab:hi:mood_happy:happy': 'mood_happy',
        'ab:hi:mood_aggressive:aggressive': 'mood_aggressive',
        'ab:hi:mood_party:party': 'mood_party',
        'ab:hi:mood_relaxed:relaxed': 'mood_relaxed',
        'ab:hi:voice_instrumental:instrumental': 'instrumental',
        'ab:hi:mood_acoustic:acoustic': 'acoustic',
        'ab:hi:tonal_atonal:tonal': 'tonal'
    }

    # Conversion des valeurs
    for acoustid_key, field_name in tag_mapping.items():
        if acoustid_key in tags:
            try:
                value = float(tags.get(acoustid_key)[0])
                features[field_name] = value
            except (ValueError, TypeError, IndexError):
                features[field_name] = None

    # Extraction des tags
    features['genre_tags'] = tags.get('ab:genre', [])
    features['mood_tags'] = tags.get('ab:mood', [])

    return features

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

        return artist_images

    except Exception as e:
        logger.error(f"Erreur recherche images artiste dans {artist_path}: {str(e)}")
        return []

async def extract_metadata(audio, file_path):
    """Extrait les métadonnées d'un fichier audio."""
    try:
        # Extraire la cover de manière asynchrone
        cover_data, mime_type = await get_cover_art(str(file_path))
        bitrate = get_file_bitrate(str(file_path))
        
        # Get artist name
        artist_name = get_tag(audio, "artist") or get_tag(audio, "TPE1") or get_tag(audio, "TPE2")
        if not artist_name:
            artist_name = Path(file_path).parent.parent.name
            logger.info(f"Utilisation du nom d'artiste depuis le dossier: {artist_name}")

        metadata = {
            "path": str(file_path),
            "title": get_tag(audio, "title") or Path(file_path).stem,
            "artist": artist_name,
            "album": get_tag(audio, "album") or Path(file_path).parent.name,
            "genre": get_tag(audio, "genre"),
            "year": get_tag(audio, "date"),
            "track_number": get_tag(audio, "tracknumber"),
            "disc_number": get_tag(audio, "discnumber"),
            "duration": int(audio.info.length if hasattr(audio.info, 'length') else 0),
            "musicbrainz_id": get_tag(audio, "musicbrainz_trackid"),
            "musicbrainz_albumid": get_tag(audio, "musicbrainz_albumid"),
            "musicbrainz_artistid": get_tag(audio, "musicbrainz_artistid"),
            "musicbrainz_albumartistid": get_tag(audio, "musicbrainz_albumartistid"),
            "musicbrainz_genre": get_tag(audio, "musicbrainz_genre"),
            "acoustid_fingerprint": get_tag(audio, "acoustid_fingerprint"),
            "cover_data": cover_data,
            "cover_mime_type": mime_type,
            "file_type": get_file_type(str(file_path)),
            "bitrate": bitrate
        }

        # Ajouter les caractéristiques audio
        audio_features = extract_audio_features(audio, audio.tags if audio else {})
        metadata.update(audio_features)

        logger.debug(f"Métadonnées extraites pour {file_path}: artiste={artist_name}")
        return metadata

    except Exception as e:
        logger.error(f"Erreur d'extraction des métadonnées pour {file_path}: {str(e)}")
        return {"path": str(file_path), "error": str(e)}

async def scan_music_files(directory: str):
    """Scan les fichiers musicaux d'un répertoire."""
    try:
        logger.info(f"Début du scan dans le répertoire: {directory}")
        path = Path(directory)

        if not path.exists():
            logger.error("Le répertoire %s n'existe pas", directory)
            return []

        # Récupérer le template de chemin
        template = await settings_service.get_setting(MUSIC_PATH_TEMPLATE)
        template_parts = template.split('/')
        logger.info(f"Template chemin: {template}")
        artist_depth = template_parts.index("{album_artist}") if "{album_artist}" in template_parts else -1
        logger.info(f"Profondeur artiste: {artist_depth}")

        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
        files_data = []

        for file_path in path.rglob('*'):
            try:
                if file_path.suffix.lower() in music_extensions:
                    logger.info(f"Traitement du fichier: {str(file_path)}")
                    
                    # Extraction explicite du chemin artiste
                    artist_path = str(file_path.parent.parent)  # Remonter de deux niveaux
                    logger.info(f"Chemin artiste déterminé: {artist_path}")

                    # Vérification des images artiste
                    artist_images = []
                    if Path(artist_path).exists():
                        artist_images = await get_artist_images(artist_path)
                        logger.info(f"Images artiste trouvées dans {artist_path}: {len(artist_images)}")

                    # Extraction des métadonnées
                    metadata = await extract_metadata(File(str(file_path), easy=True), file_path)
                    if metadata:
                        metadata.update({
                            "artist_path": artist_path,
                            "artist_images": artist_images
                        })
                        files_data.append(metadata)
                        logger.info(f"Métadonnées complètes pour: {file_path}")

            except Exception as e:
                logger.error(f"Erreur traitement fichier {file_path}: {str(e)}")
                continue

        logger.info(f"Scan terminé. {len(files_data)} fichiers trouvés")
        return files_data

    except Exception as e:
        logger.error(f"Erreur scan répertoire: {str(e)}")
        return []

def get_tag(audio, tag_name):
    """Récupère une tag de manière sécurisée."""
    try:
        if hasattr(audio.tags, 'get'):
            value = audio.tags.get(tag_name, [""])[0]
            if isinstance(value, bytes):
                return value.decode('utf-8')
            return str(value)
        return ""
    except (AttributeError, KeyError, IndexError, UnicodeDecodeError) as e:
        logger.debug(f"Erreur lecture tag {tag_name}: {str(e)}")
        return ""

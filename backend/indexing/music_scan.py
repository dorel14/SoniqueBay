# -*- coding: utf-8 -*-

from pathlib import Path
from mutagen import File
import mimetypes
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from helpers.logging import logger
import base64


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

def get_cover_art(file_path: str):
    """Récupère la pochette d'album d'un fichier audio."""
    try:
        audio = File(file_path, easy=True)
        if audio is None:
            logger.warning("Impossible de lire le fichier: %s", file_path)
            return None, None
        else:
            filetype = get_file_type(file_path)
            if filetype == "audio/mpeg":
                # Pour les fichiers MP3, utiliser mutagen
                tags = ID3(file_path)
                if tags and tags.get('APIC:'):
                    apic = tags.get('APIC:')
                    mime_type = apic.mime
                    # Création d'une data URL
                    cover_data = f"data:{mime_type};base64,{base64.b64encode(apic.data).decode('utf-8')}"
                    return cover_data, mime_type
            elif filetype in ["audio/flac", "audio/x-flac"]:
                # Pour les fichiers FLAC, utiliser mutagen
                if hasattr(audio, 'pictures') and audio.pictures:
                    picture = audio.pictures[0]
                    mime_type = picture.mime
                    # Création d'une data URL
                    cover_data = f"data:{mime_type};base64,{base64.b64encode(picture.data).decode('utf-8')}"
                    return cover_data, mime_type
            logger.debug("Pas de pochette trouvée pour: %s", file_path)
            return None, None
    except Exception as e:
        logger.error("Erreur lors de la récupération de la pochette pour %s: %s", file_path, str(e))
        return None, None
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

def scan_music_files(directory: str):
    """Scan les fichiers musicaux d'un répertoire."""
    try:
        logger.info("Début du scan dans le répertoire: %s", directory)
        path = Path(directory)

        if not path.exists():
            logger.error("Le répertoire %s n'existe pas", directory)
            return []

        # Liste des extensions supportées
        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
        files_data = []

        for file_path in path.rglob('*'):
            try:
                if file_path.suffix.lower() in music_extensions:
                    logger.info("Traitement du fichier: %s", str(file_path))

                    audio = File(file_path, easy=True)
                    tags = None

                    # Tenter de récupérer les tags ID3 pour la pochette
                    try:
                        tags = ID3(file_path)
                    except (ID3NoHeaderError, OSError) as e:
                        logger.debug("Pas de tags ID3 pour %s: %s", str(file_path), str(e))
                        tags = None

                    if audio is None:
                        logger.warning("Impossible de lire les métadonnées: %s", str(file_path))
                        continue
                    cover_data, mime_type = get_cover_art(file_path) if tags else (None, None)
                    bitrate = get_file_bitrate(file_path)
                    metadata = {
                        "path": str(file_path),
                        "title": get_tag(audio, "title") or file_path.stem,
                        "artist": get_tag(audio, "artist") or "Inconnu",
                        "album": get_tag(audio, "album") or "Inconnu",
                        "genre": get_tag(audio, "genre"),
                        "year": get_tag(audio, "date"),
                        "track_number": get_tag(audio, "tracknumber"),
                        "disc_number": get_tag(audio, "discnumber"),
                        "duration": int(audio.info.length if hasattr(audio.info, 'length') else 0),
                        # MusicBrainz metadata - correction des noms de champs
                        "musicbrainz_id": get_tag(audio, "musicbrainz_trackid"),
                        "musicbrainz_albumid": get_tag(audio, "musicbrainz_albumid"),
                        "musicbrainz_artistid": get_tag(audio, "musicbrainz_artistid"),
                        "musicbrainz_albumartistid": get_tag(audio, "musicbrainz_albumartistid"),
                        "musicbrainz_genre": get_tag(audio, "musicbrainz_genre"),
                        "acoustid_fingerprint": get_tag(audio, "acoustid_fingerprint"),
                        # Cover art
                        "cover_data": cover_data,
                        "cover_mime_type": mime_type,
                        "file_type": get_file_type(file_path),
                        "bitrate": bitrate
                    }

                    metadata.update(extract_audio_features(audio, audio.tags if audio else {}))
                    #print(metadata)
                    files_data.append(metadata)
                    logger.debug("Métadonnées extraites pour: %s", str(file_path))
                    

            except Exception as e:
                logger.error("Erreur lors du traitement de %s: %s", str(file_path), str(e))
                continue

        logger.info("Scan terminé. %d fichiers trouvés", len(files_data))
        return files_data

    except Exception as e:
        logger.error("Erreur lors du scan du répertoire: %s", str(e))
        return []

def extract_metadata(audio, file_path):
    """Extrait les métadonnées d'un fichier audio."""
    try:
        cover_data, mime_type = get_cover_art(str(file_path))
        bitrate = get_file_bitrate(str(file_path))
        audio_features = extract_audio_features(audio, audio.tags if audio else {})

        metadata = {
            "path": str(file_path),
            "title": get_tag(audio, "title") or file_path.stem,
            "artist": get_tag(audio, "artist"),
            "album": get_tag(audio, "album"),
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
        metadata.update(audio_features)

        return metadata
    except Exception as e:
        logger.error("Erreur d'extraction des métadonnées pour %s: %s", file_path, str(e))
        return {"path": str(file_path), "error": str(e)}

def get_tag(audio, tag_name):
    """Récupère une tag de manière sécurisée."""
    try:
        if hasattr(audio.tags, 'get'):
            return audio.tags.get(tag_name, [""])[0]
        return ""
    except (AttributeError, KeyError, IndexError) as e:
        logger.debug("Erreur lecture tag %s: %s", tag_name, str(e))
        return ""

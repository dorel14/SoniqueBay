# -*- coding: utf-8 -*-

from pathlib import Path
from mutagen import File
from mutagen.id3 import ID3, ID3NoHeaderError
from helpers.logging import logger



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
                        # MusicBrainz metadata
                        "musicbrain_id": get_tag(audio, "musicbrainz_trackid"),
                        "musicbrain_albumid": get_tag(audio, "musicbrainz_albumid"),
                        "musicbrain_artistid": get_tag(audio, "musicbrainz_artistid"),
                        "musicbrain_albumartistid": get_tag(audio, "musicbrainz_albumartistid"),
                        "musicbrain_genre": get_tag(audio, "musicbrainz_genre"),
                        "acoustid_fingerprint": get_tag(audio, "acoustid_fingerprint"),
                        # Cover art
                        "cover": tags.get('APIC:').data if tags and tags.get('APIC:') else None
                    }

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
        # Extraction sécurisée des métadonnées
        metadata = {
            "path": str(file_path),
            "title": get_tag(audio, "title") or file_path.stem,
            "artist": get_tag(audio, "artist"),
            "album": get_tag(audio, "album"),
            "duration": int(audio.info.length if hasattr(audio.info, 'length') else 0),
            # ...other metadata...
        }
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

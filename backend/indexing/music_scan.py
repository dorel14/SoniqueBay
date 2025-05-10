# -*- coding: utf-8 -*-
import os
from pathlib import Path
from mutagen import File
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
                    # Utilisation correcte du formatage de log
                    logger.info("Traitement du fichier: %s", str(file_path))

                    audio = File(file_path, easy=True)
                    if audio is None:
                        logger.warning("Impossible de lire les métadonnées: %s", str(file_path))
                        continue

                    metadata = {
                        "path": str(file_path),
                        "title": get_tag(audio, "title") or file_path.stem,
                        "artist": get_tag(audio, "artist"),
                        "album": get_tag(audio, "album"),
                        "genre": get_tag(audio, "genre"),
                        "year": get_tag(audio, "date"),
                        "track_number": get_tag(audio, "tracknumber"),
                        "disc_number": get_tag(audio, "discnumber"),
                        "duration": int(audio.info.length if hasattr(audio.info, 'length') else 0)
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
    except:
        return ""

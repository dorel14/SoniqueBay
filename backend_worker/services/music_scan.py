# -*- coding: utf-8 -*-

from pathlib import Path
from mutagen import File
import mimetypes
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import os
from backend_worker.utils.logging import logger
import base64
from backend_worker.services.settings_service import SettingsService, ALBUM_COVER_FILES, ARTIST_IMAGE_FILES
import json
import aiofiles
import asyncio
from backend_worker.services.audio_features_service import extract_audio_features



settings_service = SettingsService()

def sanitize_path(input_path: str) -> str:
    """
    Sanitise et normalise un chemin d'entrée pour éviter les attaques par traversée de répertoire.

    Args:
        input_path: Chemin à sanitiser

    Returns:
        Chemin normalisé et sécurisé

    Raises:
        ValueError: Si le chemin contient des éléments interdits ou dépasse les limites
    """
    import re
    from pathlib import Path

    if not input_path:
        raise ValueError("Chemin vide fourni")

    # Limiter la longueur totale du chemin
    max_path_length = 260
    if len(input_path) > max_path_length:
        logger.warning(f"Chemin trop long: {len(input_path)} caractères (max: {max_path_length})")
        raise ValueError(f"Le chemin dépasse la longueur maximale autorisée ({max_path_length} caractères)")

    # Normaliser le chemin
    try:
        normalized_path = Path(input_path).resolve()
        normalized_str = str(normalized_path)
    except (OSError, RuntimeError, ValueError) as e:
        logger.warning(f"Impossible de normaliser le chemin {input_path}: {e}")
        if 'null character' in str(e):
            logger.warning(f"Caractère nul détecté dans le chemin: {input_path}")
            raise ValueError(f"Caractère nul détecté dans le chemin: {input_path}")
        raise ValueError(f"Chemin invalide: {input_path}")

    # Regex stricte pour valider le chemin (interdit .., caractères spéciaux dangereux)
    # Permet lettres, chiffres, espaces, tirets, underscores, points, /, \, : (pour Windows)
    forbidden_pattern = re.compile(r'[<>"|?*\x00-\x1f]')  # Caractères de contrôle et spéciaux interdits
    if forbidden_pattern.search(normalized_str):
        logger.warning(f"Caractères interdits détectés dans le chemin: {normalized_str}")
        raise ValueError(f"Le chemin contient des caractères interdits: {normalized_str}")

    # Interdire explicitement les patterns de traversée (avant résolution)
    traversal_patterns = ['../', '..\\', '/..', '\\..']
    for pattern in traversal_patterns:
        if pattern in input_path:
            logger.warning(f"Pattern de traversée détecté: '{pattern}' dans {input_path}")
            raise ValueError(f"Pattern de traversée de répertoire détecté: {input_path}")

    # Interdire les chemins commençant par ..
    if input_path.startswith('..') or (len(input_path) > 1 and input_path[1:3] == '..'):
        logger.warning(f"Chemin commençant par '..' détecté: {input_path}")
        raise ValueError(f"Chemin commençant par '..' interdit: {input_path}")

    # Interdire les caractères nuls
    if '\0' in normalized_str:
        logger.warning(f"Caractère nul détecté dans le chemin: {normalized_str}")
        raise ValueError(f"Caractère nul détecté dans le chemin: {normalized_str}")

    logger.debug(f"Chemin sanitisé avec succès: {input_path} -> {normalized_str}")
    return normalized_str

def validate_filename(filename: str) -> str | None:
    """
    Valide et nettoie un nom de fichier pour éviter les attaques par traversée.

    Args:
        filename: Nom de fichier à valider

    Returns:
        Nom de fichier validé ou None si invalide
    """
    import re

    if not filename:
        return None

    # Limiter la longueur
    max_length = 255
    if len(filename) > max_length:
        logger.warning(f"Nom de fichier trop long: {len(filename)} > {max_length}")
        return None

    # Interdire les caractères interdits
    forbidden_pattern = re.compile(r'[<>"|?*\x00-\x1f]')
    if forbidden_pattern.search(filename):
        logger.warning(f"Caractères interdits dans le nom de fichier: {filename}")
        return None

    # Interdire les patterns de traversée
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Pattern de traversée dans le nom de fichier: {filename}")
        return None

    # Interdire les noms commençant par .
    if filename.startswith('.'):
        logger.warning(f"Nom de fichier commençant par '.': {filename}")
        return None

    # Nettoyer les espaces
    cleaned = filename.strip()
    if not cleaned:
        return None

    return cleaned

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


async def secure_open_file(file_path: Path, mode: str = 'rb', allowed_base_paths: list[Path] | None = None) -> bytes | None:
    """
    Ouvre un fichier de manière sécurisée avec validation complète et renforcée.

    Args:
        file_path: Chemin du fichier à ouvrir
        mode: Mode d'ouverture du fichier (restreint aux modes sécurisés)
        allowed_base_paths: Liste des répertoires de base autorisés (optionnel)

    Returns:
        Contenu du fichier en bytes ou None si erreur ou validation échouée
    """
    try:
        logger.debug(f"[SECURE_OPEN_FILE] Début validation pour: {file_path}, allowed_base_paths: {allowed_base_paths}")

        # ÉTAPE 1: Validation basique du paramètre d'entrée
        if not file_path:
            logger.warning("[SECURE_OPEN_FILE] ALERT: Chemin de fichier vide ou invalide - Tentative suspecte détectée")
            return None

        if not isinstance(file_path, Path):
            logger.warning(f"[SECURE_OPEN_FILE] ALERT: Type de chemin invalide: {type(file_path)} (attendu: Path) - Tentative suspecte détectée")
            return None

        logger.debug("[SECURE_OPEN_FILE] ✓ Validation basique du paramètre réussie")

        # ÉTAPE 2: Vérification que le chemin est absolu
        if not file_path.is_absolute():
            logger.warning(f"[SECURE_OPEN_FILE] Chemin non absolu détecté: {file_path}")
            return None

        logger.debug("[SECURE_OPEN_FILE] ✓ Chemin absolu validé")

        # ÉTAPE 3: Restriction des modes d'ouverture autorisés
        allowed_modes = {'r', 'rb'}  # Modes en lecture seule uniquement
        if mode not in allowed_modes:
            logger.warning(f"[SECURE_OPEN_FILE] Mode d'ouverture non autorisé: '{mode}' (autorisés: {allowed_modes})")
            return None

        logger.debug(f"[SECURE_OPEN_FILE] ✓ Mode d'ouverture validé: {mode}")

        # ÉTAPE 4: Résolution et normalisation du chemin
        try:
            resolved_path = file_path.resolve()
            logger.debug(f"[SECURE_OPEN_FILE] Chemin résolu: {file_path} -> {resolved_path}")
        except (OSError, RuntimeError) as e:
            logger.warning(f"[SECURE_OPEN_FILE] Impossible de résoudre le chemin {file_path}: {e}")
            return None

        # ÉTAPE 4.5: Interdire les liens symboliques pour éviter les contournements de sécurité
        if resolved_path.is_symlink():
            logger.warning(f"[SECURE_OPEN_FILE] Lien symbolique interdit (Path.is_symlink): {resolved_path}")
            return None

        # ÉTAPE 4.6: Vérification supplémentaire des liens symboliques via os.stat (nécessaire sur Windows)
        try:
            stat_result = os.stat(resolved_path)
            # Vérifier si c'est un lien symbolique via st_mode
            if (stat_result.st_mode & 0o170000) == 0o120000:  # S_IFLNK
                logger.warning(f"[SECURE_OPEN_FILE] Lien symbolique interdit (os.stat): {resolved_path}")
                return None
        except (OSError, AttributeError) as e:
            logger.warning(f"[SECURE_OPEN_FILE] Erreur lors de la vérification os.stat pour liens symboliques: {e}")
            # Ne pas échouer ici, continuer avec les autres vérifications

        # ÉTAPE 5: Validation que le chemin est dans le répertoire de travail autorisé
        if allowed_base_paths is None or not allowed_base_paths:
            logger.error(f"[SECURE_OPEN_FILE] allowed_base_paths est None ou vide - Refus d'ouverture pour éviter Path Traversal: {resolved_path}")
            return None

        path_is_allowed = False
        for base_path in allowed_base_paths:
            try:
                if base_path.is_absolute() and resolved_path.is_relative_to(base_path.resolve()):
                    path_is_allowed = True
                    logger.debug(f"[SECURE_OPEN_FILE] Chemin dans répertoire autorisé: {base_path}")
                    break
            except (OSError, ValueError):
                continue

        if not path_is_allowed:
            logger.warning(f"[SECURE_OPEN_FILE] Chemin en dehors des répertoires autorisés: {resolved_path}")
            logger.warning(f"[SECURE_OPEN_FILE] Répertoires autorisés: {[str(p) for p in allowed_base_paths]}")
            return None

        logger.debug("[SECURE_OPEN_FILE] ✓ Validation du répertoire de base réussie")

        # ÉTAPE 6: Vérification de l'existence et du type de fichier
        if not resolved_path.exists():
            logger.warning(f"[SECURE_OPEN_FILE] Fichier non trouvé: {resolved_path}")
            return None

        if not resolved_path.is_file():
            logger.warning(f"[SECURE_OPEN_FILE] Le chemin n'est pas un fichier régulier: {resolved_path}")
            return None

        # DIAGNOSTIC: Vérifier si c'est un lien symbolique (potentielle vulnérabilité)
        if resolved_path.is_symlink():
            logger.warning(f"[SECURE_OPEN_FILE] DIAGNOSTIC: Lien symbolique détecté: {resolved_path} -> {resolved_path.readlink()}")
            # Sur Windows, les liens symboliques peuvent contourner les validations

        logger.debug("[SECURE_OPEN_FILE] ✓ Existence et type de fichier validés")

        # ÉTAPE 7: Validation de la longueur du nom de fichier
        filename = resolved_path.name
        max_filename_length = 255  # Longueur maximale standard pour les noms de fichiers
        if len(filename) > max_filename_length:
            logger.warning(f"[SECURE_OPEN_FILE] Nom de fichier trop long: {len(filename)} caractères (max: {max_filename_length})")
            return None

        if len(filename) == 0:
            logger.warning("[SECURE_OPEN_FILE] Nom de fichier vide détecté")
            return None

        logger.debug(f"[SECURE_OPEN_FILE] ✓ Longueur du nom de fichier validée: {len(filename)} caractères")

        # ÉTAPE 8: Vérification complète des caractères interdits
        path_str = str(resolved_path)

        # Caractères de contrôle et caractères nuls
        if '\0' in path_str:
            logger.warning(f"[SECURE_OPEN_FILE] Caractère nul détecté dans le chemin: {path_str}")
            return None

        # Caractères de contrôle (0-31 sauf tab, newline, carriage return)
        control_chars = set(range(0, 32)) - {9, 10, 13}  # Exclure tab (9), LF (10), CR (13)
        if any(ord(c) in control_chars for c in path_str):
            logger.warning(f"[SECURE_OPEN_FILE] Caractères de contrôle détectés dans le chemin: {path_str}")
            return None

        # Caractères interdits spécifiques (exclure les caractères valides dans les chemins Windows)
        forbidden_chars = {'"', '|', '?', '*'}  # Exclure < > : qui peuvent être valides dans les chemins Windows
        if any(c in path_str for c in forbidden_chars):
            logger.warning(f"[SECURE_OPEN_FILE] Caractères interdits détectés dans le chemin: {path_str}")
            return None

        # Patterns de traversée de répertoire
        suspicious_patterns = ['../', '..\\', '/..', '\\..', './', '.\\']
        for pattern in suspicious_patterns:
            if pattern in path_str:
                logger.warning(f"[SECURE_OPEN_FILE] ALERT: Pattern de traversée détecté: '{pattern}' dans {path_str} - Tentative de Path Traversal suspecte")
                return None

        # Vérifications de début de chemin dangereux
        if path_str.startswith('..') or (len(path_str) > 1 and path_str[1:3] == '..'):
            logger.warning(f"[SECURE_OPEN_FILE] ALERT: Chemin commençant par '..' détecté: {path_str} - Tentative de Path Traversal suspecte")
            return None

        logger.debug("[SECURE_OPEN_FILE] ✓ Validation des caractères interdits réussie")

        # ÉTAPE 9: Vérification des permissions du fichier
        try:
            stat_result = resolved_path.stat()

            # Vérifier que c'est bien un fichier régulier
            if not (stat_result.st_mode & 0o170000 == 0o100000):  # S_IFREG
                logger.warning(f"[SECURE_OPEN_FILE] Le chemin n'est pas un fichier régulier: {resolved_path}")
                return None

            # Vérifier les permissions de lecture
            if not os.access(resolved_path, os.R_OK):
                logger.warning(f"[SECURE_OPEN_FILE] Pas de permission de lecture sur le fichier: {resolved_path}")
                return None

            # Vérifier que le fichier n'est pas trop volumineux (protection DoS)
            max_file_size = 1000 * 1024 * 1024  # 100MB maximum
            if stat_result.st_size > max_file_size:
                logger.warning(f"[SECURE_OPEN_FILE] Fichier trop volumineux: {stat_result.st_size} bytes (max: {max_file_size})")
                return None

            logger.debug(f"[SECURE_OPEN_FILE] ✓ Permissions et taille validées: {stat_result.st_size} bytes")

        except (OSError, AttributeError) as e:
            logger.warning(f"[SECURE_OPEN_FILE] Erreur lors de la vérification des permissions du fichier {resolved_path}: {e}")
            return None

        # ÉTAPE 10.5: Double validation - résoudre à nouveau et vérifier la cohérence
        try:
            final_resolved_path = resolved_path.resolve()
            if final_resolved_path != resolved_path:
                logger.warning(f"[SECURE_OPEN_FILE] Incohérence de résolution détectée: {resolved_path} -> {final_resolved_path}")
                return None
        except (OSError, RuntimeError) as e:
            logger.warning(f"[SECURE_OPEN_FILE] Erreur lors de la double validation: {e}")
            return None

        # ÉTAPE 11: Ouverture sécurisée du fichier
        logger.info(f"[SECURE_OPEN_FILE] Ouverture sécurisée du fichier: {final_resolved_path} (mode: {mode})")
        # DIAGNOSTIC: Logger le chemin résolu pour détecter les traversées potentielles
        logger.debug(f"[SECURE_OPEN_FILE] DIAGNOSTIC: Chemin résolu avant ouverture: {final_resolved_path}")
        # LOG DEBUG: Diagnostic pour Path Traversal (niveau debug pour éviter le bruit)
        logger.debug(f"[PATH_TRAVERSAL_DIAG] Ouverture de fichier - Chemin final: {str(final_resolved_path)}, allowed_base_paths: {[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
        try:
            async with aiofiles.open(final_resolved_path, mode=mode) as f:
                content = await f.read()
                logger.debug(f"[SECURE_OPEN_FILE] Fichier lu avec succès: {len(content)} bytes")
                return content
        except Exception as e:
            logger.error(f"[SECURE_OPEN_FILE] Erreur lors de la lecture du fichier {final_resolved_path}: {e}")
            return None

    except Exception as e:
        logger.error(f"[SECURE_OPEN_FILE] Erreur inattendue lors du traitement de {file_path}: {e}")
        return None


async def get_cover_art(file_path_str: str, audio, allowed_base_paths: list[Path] | None = None):
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
                if isinstance(cover_files_json, list):
                    cover_files = cover_files_json
                else:
                    cover_files = json.loads(cover_files_json)

                # SECURITY: Valider les noms de fichiers de cover
                validated_cover_files = []
                for cover_file in cover_files:
                    if isinstance(cover_file, str):
                        validated = validate_filename(cover_file)
                        if validated:
                            validated_cover_files.append(validated)
                        else:
                            logger.warning(f"Nom de fichier cover invalide ignoré: {cover_file}")
                    else:
                        logger.warning(f"Type de nom de fichier cover invalide: {type(cover_file)}")
                        continue

                if not validated_cover_files:
                    logger.warning("Aucun nom de fichier cover valide trouvé, utilisation d'une liste par défaut")
                    validated_cover_files = ["cover.jpg", "folder.jpg", "front.jpg"]

                cover_files = validated_cover_files

                for cover_file in cover_files:
                    cover_path = dir_path / cover_file
                    logger.debug(f"Attempting to open cover file: {cover_path}")
                    # SECURITY: Validate path to prevent directory traversal
                    try:
                        resolved_path = cover_path.resolve()
                        dir_resolved = dir_path.resolve()

                        # Vérification anti-traversée de répertoire renforcée
                        if not resolved_path.is_relative_to(dir_resolved):
                            logger.warning(f"Path traversal attempt detected for cover file: {cover_path}")
                            continue

                        # Vérification supplémentaire: le chemin ne doit pas contenir de composants suspects
                        cover_path_str = str(cover_path)
                        # Vérification intelligente: seulement les vraies tentatives de path traversal
                        if cover_path_str.startswith('\\') or '/../' in cover_path_str or cover_path_str.endswith('/..') or cover_path_str == '..':
                            logger.warning(f"Chemin de cover potentiellement dangereux: {cover_path_str}")
                            continue

                        # Vérifier que le fichier cover existe et est un fichier régulier
                        if not cover_path.exists() or not cover_path.is_file():
                            logger.debug(f"Fichier cover non trouvé ou invalide: {cover_path}")
                            continue

                    except Exception as e:
                        logger.error(f"Error resolving path for cover file {cover_path}: {e}")
                        continue

                    # SECURITY: Utiliser la fonction sécurisée pour ouvrir le fichier
                    if cover_path.exists():
                        if allowed_base_paths is None:
                            logger.error("allowed_base_paths est None dans get_cover_art - Refus d'ouverture pour éviter Path Traversal")
                            return None, None
                        mime_type = mimetypes.guess_type(str(cover_path))[0] or 'image/jpeg'
                        # LOG DEBUG: Diagnostic pour Path Traversal dans get_cover_art
                        logger.debug(f"[PATH_TRAVERSAL_DIAG] get_cover_art - Ouverture cover: chemin original={str(cover_path)}, résolu={str(resolved_path)}, allowed_base_paths={[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
                        # DIAGNOSTIC: Log before secure_open_file in get_cover_art
                        logger.warning(f"[PATH_TRAVERSAL_DIAG] get_cover_art - Avant ouverture sécurisée: resolved_path={str(resolved_path)}, allowed_base_paths={[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
                        cover_bytes = await secure_open_file(resolved_path, 'rb', allowed_base_paths=allowed_base_paths)
                        if cover_bytes:
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
        # SECURITY: Validation du chemin avant traitement
        path_obj = Path(file_path)

        # Vérifier que le chemin ne contient pas de caractères suspects
        # Vérification intelligente: seulement les vraies tentatives de path traversal
        if file_path.startswith('\\') or '/../' in file_path or file_path.endswith('/..') or file_path == '..':
            logger.warning(f"Chemin de fichier potentiellement dangereux pour bitrate: {file_path}")
            return 0

        # Vérifier que le fichier existe et est accessible
        if not path_obj.exists() or not path_obj.is_file():
            logger.warning(f"Fichier non trouvé ou invalide pour bitrate: {file_path}")
            return 0

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


async def extract_metadata(audio, file_path_str: str, allowed_base_paths: list[Path] | None = None):
    """Extrait les métadonnées d'un objet audio Mutagen."""
    try:
        # L'objet 'audio' est déjà chargé, on l'utilise directement
        cover_data, mime_type = await get_cover_art(file_path_str, audio=audio, allowed_base_paths=allowed_base_paths)
        
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

async def get_artist_images(artist_path: str, allowed_base_paths: list[Path] | None = None) -> list[tuple[str, str]]:
    """Récupère les images d'artiste dans le dossier artiste."""
    try:
        artist_images = []
        dir_path = Path(artist_path)

        if not dir_path.exists():
            logger.debug(f"Dossier artiste non trouvé: {artist_path}")
            return []

        # Récupérer la liste des noms de fichiers d'artiste depuis les paramètres
        artist_files_json = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        if isinstance(artist_files_json, list):
            artist_files = artist_files_json
        else:
            artist_files = json.loads(artist_files_json)

        # SECURITY: Valider les noms de fichiers d'artiste
        validated_artist_files = []
        for artist_file in artist_files:
            if isinstance(artist_file, str):
                validated = validate_filename(artist_file)
                if validated:
                    validated_artist_files.append(validated)
                else:
                    logger.warning(f"Nom de fichier artiste invalide ignoré: {artist_file}")
            else:
                logger.warning(f"Type de nom de fichier artiste invalide: {type(artist_file)}")
                continue

        if not validated_artist_files:
            logger.warning("Aucun nom de fichier artiste valide trouvé, utilisation d'une liste par défaut")
            validated_artist_files = ["artist.jpg", "artist.png", "folder.jpg"]

        artist_files = validated_artist_files

        for image_file in artist_files:
            image_path = dir_path / image_file
            logger.debug(f"Attempting to open artist image file: {image_path}")
            # SECURITY: Validate path to prevent directory traversal
            try:
                resolved_path = image_path.resolve()
                dir_resolved = dir_path.resolve()

                # Vérification anti-traversée de répertoire renforcée
                if not resolved_path.is_relative_to(dir_resolved):
                    logger.warning(f"Path traversal attempt detected for artist image file: {image_path}")
                    continue

                # Vérification supplémentaire: le chemin ne doit pas contenir de composants suspects
                image_path_str = str(image_path)
                # Vérification intelligente: seulement les vraies tentatives de path traversal
                if image_path_str.startswith('\\') or '/../' in image_path_str or image_path_str.endswith('/..') or image_path_str == '..':
                    logger.warning(f"Chemin d'image d'artiste potentiellement dangereux: {image_path_str}")
                    continue

                # Vérifier que le fichier image existe et est un fichier régulier
                if not image_path.exists() or not image_path.is_file():
                    logger.debug(f"Fichier image d'artiste non trouvé ou invalide: {image_path}")
                    continue

            except Exception as e:
                logger.error(f"Error resolving path for artist image file {image_path}: {e}")
                continue

            # SECURITY: Utiliser la fonction sécurisée pour ouvrir le fichier
            if image_path.exists():
                if allowed_base_paths is None:
                    logger.error("allowed_base_paths est None dans get_artist_images - Refus d'ouverture pour éviter Path Traversal")
                    return []
                try:
                    mime_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'
                    # LOG DEBUG: Diagnostic pour Path Traversal dans get_artist_images
                    logger.debug(f"[PATH_TRAVERSAL_DIAG] get_artist_images - Ouverture image artiste: chemin original={str(image_path)}, résolu={str(resolved_path)}, allowed_base_paths={[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
                    # DIAGNOSTIC: Log before secure_open_file in get_artist_images
                    logger.warning(f"[PATH_TRAVERSAL_DIAG] get_artist_images - Avant ouverture sécurisée: resolved_path={str(resolved_path)}, allowed_base_paths={[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
                    image_bytes = await secure_open_file(resolved_path, 'rb', allowed_base_paths=allowed_base_paths)
                    if image_bytes:
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
    # Corriger les apostrophes mal encodées dans les noms de fichiers
    path_obj = Path(file_path_str)
    if '?' in path_obj.name:
        corrected_name = path_obj.name.replace('?', "'")
        file_path_str = str(path_obj.parent / corrected_name)

    # SECURITY: Sanitiser le chemin avant traitement
    try:
        file_path_str = sanitize_path(file_path_str)
    except ValueError as e:
        logger.warning(f"Chemin rejeté par sanitisation: {file_path_str} - {e}")
        return None

    file_path = Path(file_path_str)

    try:
        # SECURITY: Validate path is within allowed directory boundary
        if not scan_config.get("base_directory"):
            logger.error("Pas de répertoire de base configuré pour la validation de sécurité")
            return None

        base_dir = Path(scan_config["base_directory"]).resolve()
        allowed_base_paths = [base_dir]
        resolved_path = file_path.resolve()

        # Vérifier que le fichier est dans les limites du répertoire de base
        try:
            if not resolved_path.is_relative_to(base_dir):
                logger.warning(f"Tentative de traversée de répertoire détectée: {file_path_str}")
                logger.warning(f"Chemin résolu: {resolved_path}, Répertoire de base: {base_dir}")
                logger.warning(f"Vérification de sécurité: {resolved_path} n'est PAS dans {base_dir}")
                return None
        except (OSError, ValueError) as e:
            logger.warning(f"Erreur de résolution de chemin lors de la validation: {file_path_str} - {e}")
            return None

        # Vérification supplémentaire: le chemin ne doit pas contenir de caractères suspects
        # Vérification intelligente: seulement les vraies tentatives de path traversal
        if file_path_str.startswith('\\') or '/../' in file_path_str or file_path_str.endswith('/..') or file_path_str == '..':
            logger.warning(f"Chemin de fichier potentiellement dangereux: {file_path_str}")
            return None

        # Vérifier que le fichier existe et est un fichier régulier
        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Fichier non trouvé ou invalide: {file_path_str}")
            return None

        logger.debug(f"Chemin validé avec succès: {file_path_str} dans les limites de {base_dir}")

        if file_path.suffix.lower().encode('utf-8') not in scan_config["music_extensions"]:
            logger.debug(f"Extension non musicale ignorée: {file_path_str}")
            return None

        loop = asyncio.get_running_loop()
        try:
            # SECURITY: Use the validated resolved path instead of original bytes
            file_path_str = file_path_bytes.decode('utf-8', 'surrogateescape')
            # Re-validate the path to ensure it's still safe
            if not scan_config.get("base_directory"):
                logger.error("Pas de répertoire de base configuré pour la validation de sécurité")
                return None

            base_dir = Path(scan_config["base_directory"]).resolve()
            current_path = Path(file_path_str).resolve()

            if not current_path.is_relative_to(base_dir):
                logger.warning(f"Tentative de traversée de répertoire détectée: {file_path_str}")
                return None

            # DIAGNOSTIC: Log path before secure_open_file in process_file
            logger.debug(f"[PATH_TRAVERSAL_DIAG] process_file - Avant ouverture sécurisée: current_path={str(current_path)}, allowed_base_paths={[str(p) for p in allowed_base_paths] if allowed_base_paths else 'None'}")
            # SECURITY: Utiliser la fonction sécurisée pour ouvrir le fichier
            file_content = await secure_open_file(current_path, 'rb', allowed_base_paths=allowed_base_paths)
            if file_content is None:
                logger.error(f"Impossible d'ouvrir le fichier de manière sécurisée: {file_path_str}")
                return None

            # Utiliser le contenu du fichier avec mutagen via un flux mémoire
            from io import BytesIO
            file_buffer = BytesIO(file_content)
            audio = await loop.run_in_executor(None, lambda: File(file_buffer, easy=False))
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
        artist_path = Path(*parts[:artist_depth]) if artist_depth > 0 and len(parts) > artist_depth else file_path.parent
        artist_path_str = str(artist_path)

        artist_images = []
        if artist_path_str in artist_images_cache:
            artist_images = artist_images_cache[artist_path_str]
        elif artist_path.exists():
            # Note: get_artist_images appelle toujours settings_service. On pourrait optimiser davantage.
            artist_images = await get_artist_images(artist_path_str, allowed_base_paths=allowed_base_paths)
            artist_images_cache[artist_path_str] = artist_images

        metadata = await extract_metadata(audio, file_path_str, allowed_base_paths=allowed_base_paths)
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
    resolved_base = path.resolve()

    for dirpath, dirnames, filenames in await loop.run_in_executor(None, os.walk, path):
        # SECURITY: Validate current directory is within base path
        current_dir = Path(dirpath).resolve()
        try:
            if not current_dir.is_relative_to(resolved_base):
                logger.warning(f"Répertoire en dehors des limites détecté, ignoré: {dirpath}")
                logger.warning(f"Répertoire actuel: {current_dir}, Base: {resolved_base}")
                continue

            # Vérification supplémentaire: le répertoire ne doit pas contenir de caractères suspects
            dirpath_str = str(dirpath)
            # Vérification intelligente: seulement les vraies tentatives de path traversal
            # Exclure les noms d'artistes légitimes qui contiennent ".." comme "Fred again.."
            if dirpath_str.startswith('\\') or '/../' in dirpath_str or dirpath_str.endswith('/..') or dirpath_str == '..':
                logger.warning(f"Chemin de répertoire potentiellement dangereux: {dirpath_str}")
                continue

        except (OSError, ValueError) as e:
            logger.warning(f"Erreur de résolution de répertoire: {dirpath} - {e}")
            continue

        logger.debug(f"Répertoire validé: {dirpath} dans les limites de {resolved_base}")

        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            if not filename.startswith('.'):
                file_path = os.path.join(dirpath, filename)
                yield file_path.encode('utf-8', 'surrogateescape')

async def scan_music_files(directory: str, scan_config: dict):
    """Générateur asynchrone ultra-optimisé qui scanne les fichiers musicaux."""
    path = Path(directory)
    artist_images_cache = {}
    cover_cache = {}

    # Augmenter la parallélisation pour l'extraction de base
    semaphore = asyncio.Semaphore(100)  # Augmenté de 20 à 100

    async def process_and_yield(file_path_bytes):
        async with semaphore:
            return await process_file(
                file_path_bytes, scan_config, artist_images_cache, cover_cache
            )

    # Optimiser le batching pour réduire la surcharge asyncio
    tasks = []
    batch_size = 200  # Augmenté pour moins de yields

    async for file_path_bytes in async_walk(path):
        file_suffix = Path(file_path_bytes.decode('utf-8', 'surrogateescape')).suffix.lower().encode('utf-8')
        if file_suffix in scan_config["music_extensions"]:
            tasks.append(process_and_yield(file_path_bytes))
            if len(tasks) >= batch_size:
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        yield res
                tasks = []

    # Traiter les tâches restantes
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
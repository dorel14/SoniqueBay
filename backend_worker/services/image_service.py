import json
import base64
import mimetypes
import aiofiles

from typing import Tuple, Optional, List
from backend_worker.utils.logging import logger
from backend_worker.services.path_service import find_local_images
from backend_worker.services.settings_service import SettingsService, ALBUM_COVER_FILES, ARTIST_IMAGE_FILES
from pathlib import Path

settings_service = SettingsService()

async def read_image_file(file_path: str) -> bytes:
    """Lit un fichier image et retourne ses données binaires."""
    try:
        # SECURITY: Validation complète du chemin d'entrée
        if not file_path or not file_path.strip():
            logger.warning("Chemin de fichier image vide ou invalide")
            return None

        path = Path(file_path)

        # Normaliser et résoudre le chemin pour gérer les composants relatifs et les liens symboliques
        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Impossible de résoudre le chemin {file_path}: {e}")
            return None

        # Vérifier que le chemin résolu existe et est un fichier régulier
        if not resolved_path.exists():
            logger.warning(f"Fichier image non trouvé: {resolved_path}")
            return None

        if not resolved_path.is_file():
            logger.warning(f"Le chemin n'est pas un fichier: {resolved_path}")
            return None

        # SECURITY: Vérification anti-traversée de répertoire
        path_str = str(resolved_path)

        # Vérifier les caractères suspects dans le chemin
        suspicious_patterns = ['../', '..\\', '/..', '\\..']
        for pattern in suspicious_patterns:
            if pattern in path_str:
                logger.warning(f"Tentative de traversée de répertoire détectée: {pattern} dans {path_str}")
                return None

        # Vérifier que le chemin ne commence pas par des caractères de traversée
        if path_str.startswith('..') or path_str.startswith('/') or path_str.startswith('\\'):
            logger.warning(f"Chemin potentiellement dangereux détecté: {path_str}")
            return None

        # Vérifier que le chemin ne contient pas de caractères de contrôle ou nuls
        if '\0' in path_str or any(ord(c) < 32 for c in path_str):
            logger.warning(f"Caractères invalides détectés dans le chemin: {path_str}")
            return None

        # SECURITY: Validation finale - s'assurer que c'est bien un fichier régulier
        try:
            stat_result = resolved_path.stat()
            if not stat_result.st_mode or not (stat_result.st_mode & 0o170000 == 0o100000):  # S_IFREG
                logger.warning(f"Le chemin n'est pas un fichier régulier: {resolved_path}")
                return None
        except (OSError, AttributeError) as e:
            logger.warning(f"Erreur lors de la vérification du statut du fichier {resolved_path}: {e}")
            return None

        # SECURITY: Utilisation exclusive du chemin validé et sécurisé
        return resolved_path.read_bytes()

    except Exception as e:
        logger.error(f"Erreur lecture image {file_path}: {str(e)}")
        return None

async def process_image_data(image_bytes: bytes) -> tuple[str, str]:
    """Convertit les données binaires en base64 et détermine le type MIME."""
    try:
        if not image_bytes:
            return None, None
        
        mime_type = 'image/jpeg'  # Type par défaut
        cover_data = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        return cover_data, mime_type
    except Exception as e:
        logger.error(f"Erreur traitement image: {str(e)}")
        return None, None

async def find_cover_in_directory(directory: str, cover_filenames: list[str]) -> str:
    """Recherche une image de cover dans un dossier."""
    try:
        # SECURITY: Validation complète du chemin du répertoire
        if not directory or not directory.strip():
            logger.warning("Chemin de répertoire vide ou invalide")
            return None

        dir_path = Path(directory)

        # Normaliser et résoudre le chemin pour gérer les composants relatifs et les liens symboliques
        try:
            resolved_path = dir_path.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Impossible de résoudre le chemin {directory}: {e}")
            return None

        # Vérifier que le chemin résolu existe et est un répertoire
        if not resolved_path.exists():
            logger.warning(f"Dossier non trouvé: {resolved_path}")
            return None

        if not resolved_path.is_dir():
            logger.warning(f"Le chemin n'est pas un répertoire: {resolved_path}")
            return None

        # SECURITY: Vérification anti-traversée de répertoire
        path_str = str(resolved_path)

        # Vérifier les caractères suspects dans le chemin
        suspicious_patterns = ['../', '..\\', '/..', '\\..']
        for pattern in suspicious_patterns:
            if pattern in path_str:
                logger.warning(f"Tentative de traversée de répertoire détectée: {pattern} dans {path_str}")
                return None

        # Vérifier que le chemin ne commence pas par des caractères de traversée
        if path_str.startswith('..') or path_str.startswith('/') or path_str.startswith('\\'):
            logger.warning(f"Chemin potentiellement dangereux détecté: {path_str}")
            return None

        # Vérifier que le chemin ne contient pas de caractères de contrôle ou nuls
        if '\0' in path_str or any(ord(c) < 32 for c in path_str):
            logger.warning(f"Caractères invalides détectés dans le chemin: {path_str}")
            return None

        # SECURITY: Valider les noms de fichiers de cover
        validated_filenames = []
        for filename in cover_filenames:
            if isinstance(filename, str):
                # Vérifier que le nom de fichier ne contient pas de caractères de traversée
                if '..' in filename or '/' in filename or '\\' in filename:
                    logger.warning(f"Nom de fichier cover potentiellement dangereux ignoré: {filename}")
                    continue
                # Vérifier que c'est un nom de fichier valide
                if filename.strip() and not filename.startswith('.'):
                    validated_filenames.append(filename.strip())
            else:
                logger.warning(f"Type de nom de fichier cover invalide: {type(filename)}")
                continue

        # Parcourir les fichiers de cover potentiels validés
        for filename in validated_filenames:
            cover_path = resolved_path / filename

            # SECURITY: Validation finale du chemin du fichier cover
            try:
                cover_resolved = cover_path.resolve()
                # Vérifier que le fichier cover est dans le répertoire spécifié
                if not cover_resolved.is_relative_to(resolved_path):
                    logger.warning(f"Chemin de cover en dehors du répertoire: {cover_path}")
                    continue

                # Vérifications supplémentaires de sécurité
                cover_path_str = str(cover_path)
                if '..' in cover_path_str or cover_path_str.startswith('/') or cover_path_str.startswith('\\'):
                    logger.warning(f"Chemin de cover potentiellement dangereux: {cover_path_str}")
                    continue

                if cover_resolved.exists() and cover_resolved.is_file():
                    logger.info(f"Cover trouvée: {cover_resolved}")
                    return cover_resolved.as_posix()

            except (OSError, ValueError) as e:
                logger.warning(f"Erreur de résolution du chemin de cover {cover_path}: {e}")
                continue

        return None
    except Exception as e:
        logger.error(f"Erreur recherche cover dans {directory}: {str(e)}")
        return None

async def process_cover_image(image_path: str, album_path: Optional[str] = None) -> Tuple[str, str]:
    """Traite l'image de cover avec fallback sur les fichiers locaux."""
    try:
        # Si image_data fournie et valide, la traiter
        if image_path and isinstance(image_path, str):
            if image_path.startswith('data:image/'):
                mime_type = image_path.split(';')[0].replace('data:', '')
                return image_path, mime_type
            else:
                # Essayer de lire directement le fichier image
                image_bytes = await read_image_file(image_path)
                if image_bytes:
                    return await process_image_data(image_bytes)
                else:
                    logger.error(f"Erreur traitement cover: Impossible de lire le fichier {image_path}")

        # Chercher dans le dossier local si un chemin album est fourni
        if album_path:
            album_cover_files = await settings_service.get_setting(ALBUM_COVER_FILES)
            cover_path = await find_local_images(album_path, json.loads(album_cover_files))
            if cover_path:
                image_bytes = await read_image_file(cover_path)
                if image_bytes:
                    return await process_image_data(image_bytes)

        return None, None

    except Exception as e:
        logger.error(f"Erreur traitement cover: {str(e)}")
        return None, None

async def process_artist_image(artist_path: str) -> Tuple[str, str]:
    """Traite l'image d'artiste avec recherche dans le dossier de l'artiste."""
    try:
        logger.info(f"Début traitement image artiste pour: {artist_path}")
        
        if not artist_path:
            logger.warning("Chemin artiste non fourni")
            return None, None
            
        # Récupérer la liste des noms de fichiers d'artiste
        artist_image_files = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        logger.info(f"Fichiers images artiste à chercher: {artist_image_files}")
        
        # Rechercher les images
        image_path = await find_local_images(artist_path, json.loads(artist_image_files))
        if not image_path:
            logger.warning(f"Aucune image trouvée dans: {artist_path}")
            return None, None
            
        logger.info(f"Image artiste trouvée: {image_path}")
        
        # Lire l'image
        image_bytes = await read_image_file(image_path)
        if not image_bytes:
            logger.error(f"Impossible de lire l'image: {image_path}")
            return None, None
            
        # Convertir en base64
        logger.info("Conversion de l'image en base64...")
        result = await process_image_data(image_bytes)
        
        if result[0]:
            logger.info("Image artiste traitée avec succès")
        else:
            logger.error("Échec du traitement de l'image artiste")
            
        return result
        
    except Exception as e:
        logger.error(f"Erreur traitement image artiste pour {artist_path}: {str(e)}")
        return None, None

async def convert_to_base64(image_bytes: bytes, mime_type: str) -> Tuple[str, str]:
    """Convertit les octets d'image en une chaîne base64."""
    try:
        if not image_bytes:
            return None, None

        # Déterminer le type MIME si non fourni
        if not mime_type:
            mime_type = 'image/jpeg'

        # Conversion en base64
        image_data = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        return image_data, mime_type
    except Exception as e:
        logger.error(f"Erreur conversion image en base64: {str(e)}")
        return None, None

def convert_to_base64_sync(image_bytes: bytes, mime_type: str) -> Tuple[str, str]:
    """Version synchrone de convert_to_base64 pour les contextes non-async."""
    try:
        if not image_bytes:
            return None, None

        # Déterminer le type MIME si non fourni
        if not mime_type:
            mime_type = 'image/jpeg'

        # Conversion en base64
        image_data = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        return image_data, mime_type
    except Exception as e:
        logger.error(f"Erreur conversion image en base64 (synchrone): {str(e)}")
        return None, None

async def get_artist_images(artist_path: str) -> List[Tuple[str, str]]:
    """Récupère les images d'artiste dans le dossier artiste."""
    try:
        logger.info(f"Recherche d'images dans: {artist_path}")
        artist_images = []

        # SECURITY: Validation complète du chemin d'entrée
        if not artist_path or not artist_path.strip():
            logger.warning("Chemin artiste vide ou invalide")
            return []

        dir_path = Path(artist_path)

        # Normaliser et résoudre le chemin pour gérer les composants relatifs et les liens symboliques
        try:
            resolved_path = dir_path.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Impossible de résoudre le chemin {artist_path}: {e}")
            return []

        # Vérifier que le chemin résolu existe et est un répertoire
        if not resolved_path.exists():
            logger.warning(f"Dossier artiste non trouvé: {resolved_path}")
            return []

        if not resolved_path.is_dir():
            logger.warning(f"Le chemin n'est pas un répertoire: {resolved_path}")
            return []

        # SECURITY: Vérification anti-traversée de répertoire
        path_str = str(resolved_path)

        # Vérifier les caractères suspects dans le chemin
        suspicious_patterns = ['../', '..\\', '/..', '\\..']
        for pattern in suspicious_patterns:
            if pattern in path_str:
                logger.warning(f"Tentative de traversée de répertoire détectée: {pattern} dans {path_str}")
                return []

        # Vérifier que le chemin ne commence pas par des caractères de traversée
        if path_str.startswith('..') or path_str.startswith('/') or path_str.startswith('\\'):
            logger.warning(f"Chemin potentiellement dangereux détecté: {path_str}")
            return []

        # Vérifier que le chemin ne contient pas de caractères de contrôle ou nuls
        if '\0' in path_str or any(ord(c) < 32 for c in path_str):
            logger.warning(f"Caractères invalides détectés dans le chemin: {path_str}")
            return []

        # Liste des fichiers image possibles
        image_files = ["artist.jpg", "folder.jpg", "cover.jpg", "fanart.jpg", "artist.png", "folder.png", "cover.png", "fanart.png", "artist.jpeg", "folder.jpeg", "cover.jpeg", "fanart.jpeg"]
        logger.info(f"Recherche des fichiers: {image_files}")

        for image_file in image_files:
            # SECURITY: Valider le nom du fichier image
            if not image_file or '..' in image_file or '/' in image_file or '\\' in image_file:
                logger.warning(f"Nom de fichier image potentiellement dangereux ignoré: {image_file}")
                continue

            image_path = resolved_path / image_file
            if image_path.exists() and image_path.is_file():
                try:
                    logger.info(f"Image trouvée: {image_path}")

                    # SECURITY: Validation finale du chemin de l'image
                    try:
                        image_resolved = image_path.resolve()
                        # Vérifier que l'image est dans le répertoire de l'artiste
                        if not image_resolved.is_relative_to(resolved_path):
                            logger.warning(f"Chemin d'image en dehors du répertoire artiste: {image_path}")
                            continue

                        # Vérifications supplémentaires de sécurité
                        image_path_str = str(image_path)
                        if '..' in image_path_str or image_path_str.startswith('/') or image_path_str.startswith('\\'):
                            logger.warning(f"Chemin d'image potentiellement dangereux: {image_path_str}")
                            continue

                    except (OSError, ValueError) as e:
                        logger.warning(f"Erreur de résolution du chemin d'image {image_path}: {e}")
                        continue

                    mime_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'

                    # SECURITY: Utilisation exclusive du chemin validé et sécurisé
                    async with aiofiles.open(image_resolved, mode='rb') as f:
                        image_bytes = await f.read()
                        image_data, converted_mime_type = await convert_to_base64(image_bytes, mime_type)
                        if image_data:
                            artist_images.append((image_data, converted_mime_type))
                            logger.info(f"Image traitée avec succès: {image_path}")
                except Exception as e:
                    logger.error(f"Erreur traitement image {image_path}: {str(e)}")

        logger.info(f"Total images trouvées: {len(artist_images)}")
        return artist_images

    except Exception as e:
        logger.error(f"Erreur recherche images dans {artist_path}: {str(e)}")
        return []

import json
import base64
import mimetypes
import aiofiles

from typing import Tuple, Optional, List
from helpers.logging import logger
from .path_service import find_local_images
from .settings_service import SettingsService, ALBUM_COVER_FILES, ARTIST_IMAGE_FILES
from pathlib import Path

settings_service = SettingsService()

async def read_image_file(file_path: str) -> bytes:
    """Lit un fichier image et retourne ses données binaires."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Image non trouvée: {file_path}")
            return None
        return path.read_bytes()
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
        dir_path = Path(directory)
        if not dir_path.exists():
            return None

        # Parcourir les fichiers de cover potentiels
        for filename in cover_filenames:
            cover_path = dir_path / filename
            if cover_path.exists():
                logger.info(f"Cover trouvée: {cover_path}")
                return str(cover_path)
        
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

async def get_artist_images(artist_path: str) -> List[Tuple[str, str]]:
    """Récupère les images d'artiste dans le dossier artiste."""
    try:
        logger.info(f"Recherche d'images dans: {artist_path}")
        artist_images = []
        dir_path = Path(artist_path)
        
        if not dir_path.exists():
            logger.warning(f"Dossier artiste non trouvé: {artist_path}")
            return []

        # Liste des fichiers image possibles
        image_files = ["artist.jpg", "folder.jpg", "cover.jpg", "fanart.jpg"]
        logger.info(f"Recherche des fichiers: {image_files}")

        for image_file in image_files:
            image_path = dir_path / image_file
            if image_path.exists():
                try:
                    logger.info(f"Image trouvée: {image_path}")
                    mime_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'
                    async with aiofiles.open(image_path, mode='rb') as f:
                        image_bytes = await f.read()
                        image_data = await convert_to_base64(image_bytes, mime_type)
                        if image_data:
                            artist_images.append((image_data, mime_type))
                            logger.info(f"Image traitée avec succès: {image_path}")
                except Exception as e:
                    logger.error(f"Erreur traitement image {image_path}: {str(e)}")

        logger.info(f"Total images trouvées: {len(artist_images)}")
        return artist_images

    except Exception as e:
        logger.error(f"Erreur recherche images dans {artist_path}: {str(e)}")
        return []

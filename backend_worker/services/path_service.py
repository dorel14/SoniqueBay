import os
import httpx
import json
from typing import Optional,  List
from backend_worker.utils.logging import logger
from backend_worker.services.settings_service import SettingsService, ARTIST_IMAGE_FILES, ALBUM_COVER_FILES
from pathlib import Path

settings_service = SettingsService()

# Fonctions globales pour la compatibilité
async def find_local_images(directory: str, image_type: str = "album") -> Optional[str]:
    """Version globale de find_local_images pour compatibilité."""
    path_service = PathService()
    return await path_service.find_local_images(directory, image_type)

async def get_artist_path(artist_name: str, full_path: str) -> Optional[str]:
    """Version globale de get_artist_path pour compatibilité."""
    path_service = PathService()
    return await path_service.get_artist_path(artist_name, full_path)

class PathService:
    def __init__(self, api_url: str = os.getenv('API_URL', 'http://localhost:8001')):
        self.api_url = api_url
        self.settings_service = SettingsService(api_url)

    async def get_template(self) -> Optional[str]:
        """Récupère le template de chemin depuis l'API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/api/settings/music_path_template")
            if response.status_code == 200:
                return (await response.json()).get("value")
            return None

    async def get_artist_path(self, artist_name: str, full_path: str) -> Optional[str]:
        """Extrait le chemin de l'artiste à partir du chemin complet."""
        try:
            template = await self.get_template()
            if not template:
                return None

            template_parts = template.split('/')
            path_parts = [p for p in full_path.split('/') if p]  # Filter out empty parts
            artist_depth = template_parts.index("{album_artist}")
            return '/' + '/'.join(path_parts[:artist_depth + 1])  # Use / consistently
        except (ValueError, IndexError) as e:
            logger.error(f"Erreur extraction chemin artiste: {e}")
            return None

    async def find_local_images(self, directory: str, image_type: str = "album") -> Optional[str]:
        """Cherche les images dans un dossier."""
        try:
            if not os.path.exists(directory):
                logger.debug(f"Dossier non trouvé: {directory}")
                return None

            # Si image_type est une liste, l'utiliser directement
            if isinstance(image_type, list):
                image_files = image_type
            else:
                # Sinon, charger depuis les settings
                setting_key = ALBUM_COVER_FILES if image_type == "album" else ARTIST_IMAGE_FILES
                image_files = json.loads(await self.settings_service.get_setting(setting_key))

            for image_name in image_files:
                image_path = (Path(directory) / image_name).as_posix()  # Use POSIX style paths
                if os.path.isfile(image_path):
                    logger.debug(f"Image trouvée: {image_path}")
                    return image_path

            logger.debug(f"Aucune image trouvée dans {directory}")
            return None

        except Exception as e:
            logger.error(f"Erreur recherche image dans {directory}: {e}")
            return None

    @classmethod
    async def find_cover_in_directory(cls, directory: str, cover_filenames: List[str]) -> Optional[str]:
        """Recherche une image de cover dans un dossier."""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.debug(f"Dossier non trouvé: {directory}")
                return None

            # Parcourir les fichiers de cover potentiels
            for filename in cover_filenames:
                cover_path = dir_path / filename
                if cover_path.exists():
                    logger.info(f"Cover trouvée: {cover_path}")
                    return str(cover_path.absolute())

            logger.debug(f"Aucune cover trouvée dans: {directory}")
            return None

        except Exception as e:
            logger.error(f"Erreur recherche cover dans {directory}: {str(e)}")
            return None

# Ajouter au niveau global pour la compatibilité
async def find_cover_in_directory(directory: str, cover_filenames: List[str]) -> Optional[str]:
    """Version globale de find_cover_in_directory pour compatibilité."""
    return await PathService.find_cover_in_directory(directory, cover_filenames)

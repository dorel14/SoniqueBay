import json
import os

from typing import Optional,  List
from backend.api.utils.logging import logger
from backend.services.settings_service import SettingsService, ARTIST_IMAGE_FILES, ALBUM_COVER_FILES
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession


settings_service = SettingsService()

# Fonctions globales pour la compatibilité
async def find_local_images(directory: str, image_type: str | List[str] = "album", db: AsyncSession = None) -> Optional[str]:
    """Version globale de find_local_images pour compatibilité."""
    path_service = PathService(db)
    return await path_service.find_local_images(directory, image_type)  # type: ignore

async def get_artist_path(artist_name: str, full_path: str, db: AsyncSession = None) -> Optional[str]:
    """Version globale de get_artist_path pour compatibilité."""
    path_service = PathService(db)
    return await path_service.get_artist_path(artist_name, full_path)

class PathService:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.settings_service = SettingsService()

    async def get_template(self) -> Optional[str]:
        """Récupère le template de chemin depuis la DB."""
        if self.db:
            return await self.settings_service.get_setting("music_path_template", self.db)
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

    async def find_local_images(self, directory: str, image_type: str | List[str] = "album") -> Optional[str]:
        """Cherche les images dans un dossier."""
        try:
            if not os.path.exists(directory):
                logger.warning(f"[PATH_SERVICE] Dossier non trouvé: {directory}")
                return None

            # Si image_type est une liste, l'utiliser directement
            if isinstance(image_type, list):
                image_files = image_type
            else:
                # Sinon, charger depuis les settings
                setting_key = ALBUM_COVER_FILES if image_type == "album" else ARTIST_IMAGE_FILES
                setting_value = await self.settings_service.get_setting(setting_key, self.db)
                image_files = json.loads(setting_value) if setting_value else []

            logger.info(f"[PATH_SERVICE] Recherche images {image_type} dans {directory}: {image_files}")
            
            for image_name in image_files:
                image_path = (Path(directory) / image_name).as_posix()  # Use POSIX style paths
                if os.path.isfile(image_path):
                    logger.info(f"[PATH_SERVICE] Image trouvée: {image_path}")
                    return image_path

            logger.warning(f"[PATH_SERVICE] Aucune image trouvée dans {directory}")
            return None

        except Exception as e:
            logger.error(f"[PATH_SERVICE] Erreur recherche image dans {directory}: {e}")
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

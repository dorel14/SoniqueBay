import json
import httpx
from typing import Any
import os

# Clés des paramètres système
MUSIC_PATH_TEMPLATE = "music_path_template"
ARTIST_IMAGE_FILES = "artist_image_files"
ALBUM_COVER_FILES = "album_cover_files"

# Valeurs par défaut
DEFAULT_SETTINGS = {
    MUSIC_PATH_TEMPLATE: "{album_artist}/{album_title}/{track}",
    ARTIST_IMAGE_FILES: json.dumps(["folder.jpg", "fanart.jpg"]),
    ALBUM_COVER_FILES: json.dumps(["cover.jpg", "folder.jpg"])
}

class SettingsService:
    def __init__(self, api_url: str = os.getenv('API_URL', 'http://localhost:8001')):
        self.api_url = f"{api_url}/api/settings"

    async def get_setting(self, key: str) -> Any:
        """Récupère un paramètre avec fallback sur la valeur par défaut."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{key}")
            if response.status_code == 200:
                data = response.json()
                if data["value"] is None:
                    # Créer avec la valeur par défaut
                    await self.update_setting(key, DEFAULT_SETTINGS.get(key))
                    return DEFAULT_SETTINGS.get(key)
                return data["value"]
            return DEFAULT_SETTINGS.get(key)

    async def update_setting(self, key: str, value: str) -> bool:
        """Met à jour un paramètre."""
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{self.api_url}/{key}", params={"value": value})
            return response.status_code == 200

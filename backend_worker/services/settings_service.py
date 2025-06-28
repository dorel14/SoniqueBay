import httpx
import os
from typing import Any
# Définition locale des clés de settings
ALBUM_COVER_FILES = "album_cover_files"
ARTIST_IMAGE_FILES = "artist_image_files"
MUSIC_PATH_TEMPLATE = "music_path_template"
class SettingsService:
    def __init__(self, api_url: str = os.getenv('API_URL', 'http://localhost:8001')):
        self.api_url = f"{api_url}/api/settings"

    async def get_setting(self, key: str) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{key}")
            if response.status_code == 200:
                data = response.json()
                return data.get("value")
            return None

    async def update_setting(self, key: str, value: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{self.api_url}/{key}", params={"value": value})
            return response.status_code == 200

    async def get_path_variables(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/path_variables")
            if response.status_code == 200:
                return response.json()
            return {}
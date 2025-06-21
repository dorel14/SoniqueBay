import httpx
from typing import Optional, Tuple
from helpers.logging import logger
import base64
import os

async def get_coverart_image(client: httpx.AsyncClient, mb_release_id: str) -> Optional[Tuple[str, str]]:
    """Récupère l'image de cover depuis Cover Art Archive."""
    try:
        if not mb_release_id:
            return None

        url = f"https://coverartarchive.org/release/{mb_release_id}/front"
        response = await client.get(url)

        if response.status_code == 200:
            image_data = response.content
            mime_type = response.headers.get('content-type', 'image/jpeg')
            logger.info(f"Cover trouvée sur Cover Art Archive pour {mb_release_id}")

            # Convertir en base64
            image_data = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
            return image_data, mime_type

        return None

    except Exception as e:
        logger.error(f"Erreur récupération cover depuis Cover Art Archive: {str(e)}")
        return None

async def get_cover_schema(api_url: str = os.environ.get("API_URL")) -> dict:
    """Récupère dynamiquement le schéma JSON de CoverCreate depuis l'API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/covers/schema")
        response.raise_for_status()
        return response.json()
async def get_cover_types(api_url: str = os.environ.get("API_URL")) -> list:
    """Récupère dynamiquement les types de couverture depuis l'API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/covers/types")
        response.raise_for_status()
        return response.json()

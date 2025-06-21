import httpx
import base64
from typing import Optional, Tuple
from helpers.logging import logger
from .settings_service import SettingsService

settings_service = SettingsService()

async def get_lastfm_artist_image(client: httpx.AsyncClient, artist_name: str) -> Optional[Tuple[str, str]]:
    """Récupère l'image d'artiste depuis Last.fm et la convertit en base64."""
    try:
        api_key = await settings_service.get_setting("lastfm_api_key")
        if not api_key:
            logger.warning("Clé API Last.fm non configurée")
            return None

        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            'method': 'artist.getinfo',
            'artist': artist_name,
            'api_key': api_key,
            'format': 'json',
        }

        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            images = data.get('artist', {}).get('image', [])
            
            # Chercher la plus grande image
            for img in reversed(images):
                image_url = img.get("#text")
                if image_url:
                    logger.info(f"Image Last.fm trouvée pour {artist_name}")
                    # Télécharger l'image
                    img_response = await client.get(image_url)
                    if img_response.status_code == 200:
                        # Convertir en base64
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
                        mime_type = img_response.headers.get('content-type', 'image/jpeg')
                        return f"data:{mime_type};base64,{image_data}", mime_type

        logger.warning(f"Aucune image Last.fm trouvée pour {artist_name}")
        return None

    except Exception as e:
        logger.error(f"Erreur récupération image Last.fm pour {artist_name}: {str(e)}")
        return None

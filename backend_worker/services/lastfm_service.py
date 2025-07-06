import httpx
import base64
from typing import Optional, Tuple
from helpers.logging import logger
from .settings_service import SettingsService

settings_service = SettingsService()
_lastfm_artist_image_cache = {}

async def get_lastfm_artist_image(client: httpx.AsyncClient, artist_name: str) -> Optional[Tuple[str, str]]:
    """Récupère l'image d'artiste depuis Last.fm et la convertit en base64."""
    try:
        # --- Début optimisation 1 ---
        if artist_name in _lastfm_artist_image_cache:
            return _lastfm_artist_image_cache[artist_name]
        # --- Fin optimisation 1 ---
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

        response = await client.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            images = data.get('artist', {}).get('image', [])
            
            # --- Début optimisation 2 ---
            # Chercher une image de taille intermédiaire d'abord
            preferred_sizes = ["extralarge", "large", "mega", "medium", "small"]
            for size in preferred_sizes:
                for img in images:
                    if img.get("size") == size and img.get("#text"):
                        image_url = img.get("#text")
                        logger.info(f"Image Last.fm trouvée pour {artist_name} (taille {size})")
                        try:
                            img_response = await client.get(image_url, timeout=10)
                        except httpx.RequestError as e:
                            logger.error(f"Timeout image Last.fm: {e}")
                            continue
                        if img_response.status_code == 200:
                            image_data = base64.b64encode(img_response.content).decode('utf-8')
                            mime_type = img_response.headers.get('content-type', 'image/jpeg')
                            result = (f"data:{mime_type};base64,{image_data}", mime_type)
                            # --- Début optimisation 1 (suite) ---
                            _lastfm_artist_image_cache[artist_name] = result
                            # --- Fin optimisation 1 (suite) ---
                            return result
            # --- Fin optimisation 2 ---
        logger.warning(f"Aucune image Last.fm trouvée pour {artist_name}")
        return None

    except Exception as e:
        logger.error(f"Erreur récupération image Last.fm pour {artist_name}: {str(e)}")
        return None

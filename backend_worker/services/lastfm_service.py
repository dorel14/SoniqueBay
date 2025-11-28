import httpx
import base64
from typing import Optional, Tuple
from backend_worker.utils.logging import logger
from backend_worker.services.settings_service import SettingsService
from backend_worker.services.cache_service import cache_service

settings_service = SettingsService()
# Le cache est maintenant géré par CacheService

async def _fetch_lastfm_image(client: httpx.AsyncClient, artist_name: str) -> Optional[Tuple[str, str]]:
    """Fonction interne pour récupérer l'image Last.fm (utilisée par le cache)."""
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
                        return result

    logger.warning(f"Aucune image Last.fm trouvée pour {artist_name}")
    return None


async def get_lastfm_artist_image(client: httpx.AsyncClient, artist_name: str) -> Optional[Tuple[str, str]]:
    """
    Récupère l'image d'artiste depuis Last.fm avec cache et circuit breaker.

    Args:
        client: Client HTTP asynchrone
        artist_name: Nom de l'artiste

    Returns:
        Tuple (données_base64, type_mime) ou None
    """
    try:
        # Utiliser le CacheService avec circuit breaker
        return await cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            artist_name.lower(),
            _fetch_lastfm_image,
            client,
            artist_name
        )

    except Exception as e:
        logger.error(f"Erreur récupération image Last.fm pour {artist_name}: {str(e)}")
        return None

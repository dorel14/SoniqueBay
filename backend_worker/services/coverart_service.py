import httpx
from typing import Optional, Tuple
from backend_worker.utils.logging import logger
import base64
import os

async def get_coverart_image(client: httpx.AsyncClient, mb_release_id: str) -> Optional[Tuple[str, str]]:
    """Récupère l'image de cover depuis Cover Art Archive."""
    try:
        if not mb_release_id:
            logger.warning(f"[COVERART] MBID vide fourni")
            return None

        url = f"https://coverartarchive.org/release/{mb_release_id}/front"
        logger.info(f"[COVERART] Requête vers {url}")

        # Suivre manuellement les redirections si nécessaire
        max_redirects = 5
        current_url = url

        for _ in range(max_redirects):
            response = await client.get(current_url, timeout=10, follow_redirects=False)
            logger.info(f"[COVERART] Réponse: status={response.status_code}, url={current_url}")

            if response.status_code in (301, 302, 307, 308):
                # Redirection
                location = response.headers.get('location')
                logger.info(f"[COVERART] Headers de redirection: {dict(response.headers)}")
                if location:
                    if location.startswith('http'):
                        current_url = location
                    else:
                        # URL relative
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, location)
                    logger.info(f"[COVERART] Redirection vers {current_url}")
                    continue
                else:
                    logger.warning(f"[COVERART] Redirection sans location header")
                    return None
            elif response.status_code == 200:
                image_data = response.content
                mime_type = response.headers.get('content-type', 'image/jpeg')
                logger.info(f"Cover trouvée sur Cover Art Archive pour {mb_release_id} (taille: {len(image_data)} bytes)")

                # Convertir en base64
                image_data = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
                return image_data, mime_type
            else:
                logger.warning(f"[COVERART] Cover non trouvée pour {mb_release_id}: status {response.status_code}")
                return None

        logger.warning(f"[COVERART] Trop de redirections pour {mb_release_id}")
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

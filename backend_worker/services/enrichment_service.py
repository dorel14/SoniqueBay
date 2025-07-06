import httpx
import os
from typing import Optional
from helpers.logging import logger
from backend_worker.services.lastfm_service import get_lastfm_artist_image
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.entity_manager import create_or_update_cover

api_url = os.getenv("API_URL", "http://backend:8001")

async def enrich_artist(artist_id: int):
    """
    Tente d'enrichir un artiste avec une image de Last.fm si aucune n'existe.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Vérifier si une cover existe déjà
            response = await client.get(f"{api_url}/api/covers/artist/{artist_id}")
            if response.status_code == 200 and response.json():
                logger.info(f"L'artiste {artist_id} a déjà une cover. Enrichissement annulé.")
                return

            # 2. Récupérer les informations de l'artiste
            response = await client.get(f"{api_url}/api/artists/{artist_id}")
            if response.status_code != 200:
                logger.error(f"Impossible de récupérer l'artiste {artist_id} pour l'enrichissement.")
                return
            
            artist_data = response.json()
            artist_name = artist_data.get("name")

            if not artist_name:
                logger.error(f"Nom d'artiste manquant pour l'ID {artist_id}.")
                return

            # 3. Tenter de récupérer l'image sur Last.fm
            logger.info(f"Recherche d'une image Last.fm pour l'artiste '{artist_name}' (ID: {artist_id})")
            lastfm_cover = await get_lastfm_artist_image(client, artist_name)

            if lastfm_cover:
                cover_data, mime_type = lastfm_cover
                await create_or_update_cover(
                    client, "artist", artist_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"lastfm://{artist_name}"
                )
                logger.info(f"Image Last.fm ajoutée avec succès pour l'artiste {artist_id}.")

        except Exception as e:
            logger.error(f"Erreur lors de l'enrichissement de l'artiste {artist_id}: {e}", exc_info=True)

async def enrich_album(album_id: int):
    """
    Tente d'enrichir un album avec une pochette de Cover Art Archive si aucune n'existe.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Vérifier si une cover existe déjà
            response = await client.get(f"{api_url}/api/covers/album/{album_id}")
            if response.status_code == 200 and response.json():
                logger.info(f"L'album {album_id} a déjà une cover. Enrichissement annulé.")
                return

            # 2. Récupérer les informations de l'album
            response = await client.get(f"{api_url}/api/albums/{album_id}")
            if response.status_code != 200:
                logger.error(f"Impossible de récupérer l'album {album_id} pour l'enrichissement.")
                return
            
            album_data = response.json()
            mb_release_id = album_data.get("musicbrainz_albumid")

            if not mb_release_id:
                logger.warning(f"Aucun MusicBrainz Release ID pour l'album {album_id}. Impossible de chercher sur Cover Art Archive.")
                return

            # 3. Tenter de récupérer la pochette sur Cover Art Archive
            logger.info(f"Recherche d'une pochette sur Cover Art Archive pour l'album {album_id} (MBID: {mb_release_id})")
            coverart_cover = await get_coverart_image(client, mb_release_id)

            if coverart_cover:
                cover_data, mime_type = coverart_cover
                await create_or_update_cover(
                    client, "album", album_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"coverart://{mb_release_id}"
                )
                logger.info(f"Pochette de Cover Art Archive ajoutée avec succès pour l'album {album_id}.")

        except Exception as e:
            logger.error(f"Erreur lors de l'enrichissement de l'album {album_id}: {e}", exc_info=True)
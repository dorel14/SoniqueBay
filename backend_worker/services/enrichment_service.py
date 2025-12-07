import httpx
import os
from backend_worker.utils.logging import logger
from backend_worker.services.lastfm_service import lastfm_service
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.workers.lastfm.lastfm_worker import fetch_artist_lastfm_info
from backend_worker.services.entity_manager import create_or_update_cover
from backend_worker.workers.lastfm.lastfm_worker import fetch_similar_artists

api_url = os.getenv("API_URL", "http://api:8001")

async def enrich_artist(artist_id: int):
    """
    Tente d'enrichir un artiste avec des données complètes de Last.fm.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Récupérer les informations de l'artiste
            response = await client.get(f"{api_url}/api/artists/{artist_id}")
            if response.status_code != 200:
                logger.error(f"Impossible de récupérer l'artiste {artist_id} pour l'enrichissement.")
                return

            artist_data = response.json()
            artist_name = artist_data.get("name")
            mb_artist_id = artist_data.get("musicbrainz_artistid")

            if not artist_name:
                logger.error(f"Nom d'artiste manquant pour l'ID {artist_id}.")
                return

            # 2. Récupérer les informations complètes depuis Last.fm
            logger.info(f"Recherche d'informations Last.fm pour l'artiste '{artist_name}' (ID: {artist_id})")

            # Récupérer les infos de base avec MBID si disponible
            artist_info = await lastfm_service.get_artist_info(artist_name, mb_artist_id)
            if not artist_info:
                logger.warning(f"Aucune information Last.fm trouvée pour l'artiste {artist_name} (MBID: {mb_artist_id or 'N/A'})")
                return

            # 3. Mettre à jour les informations Last.fm dans la base de données
            await fetch_artist_lastfm_info(artist_id)

            # 4. Récupérer et stocker les artistes similaires
            similar_artists = await lastfm_service.get_similar_artists(artist_name)
            if similar_artists:
                await fetch_similar_artists(artist_id)

            # 5. Récupérer l'image de l'artiste
            lastfm_cover = await lastfm_service.get_artist_image(artist_name)
            if lastfm_cover:
                cover_data, mime_type = lastfm_cover
                await create_or_update_cover(
                    client, "artist", artist_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"lastfm://{artist_name}"
                )

            logger.info(f"Enrichissement Last.fm complet pour l'artiste {artist_id}.")

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
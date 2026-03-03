import httpx
import os
from backend_worker.utils.logging import logger
from backend_worker.services.lastfm_service import lastfm_service
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.entity_manager import create_or_update_cover

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

            # 3. Mettre à jour les informations Last.fm dans la base de données via API
            update_response = await client.post(f"{api_url}/api/artists/{artist_id}/lastfm-info")
            if update_response.status_code != 200:
                logger.warning(f"Échec de la mise à jour Last.fm pour l'artiste {artist_id}: {update_response.text}")
            else:
                logger.info(f"Informations Last.fm mises à jour pour l'artiste {artist_id}")

            # 4. Récupérer et stocker les artistes similaires via API
            similar_response = await client.post(f"{api_url}/api/artists/{artist_id}/fetch-similar?limit=10")
            if similar_response.status_code != 200:
                logger.warning(f"Échec de la récupération des artistes similaires pour {artist_id}: {similar_response.text}")
            else:
                logger.info(f"Artistes similaires récupérés pour l'artiste {artist_id}")

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
            logger.info(f"[ENRICH_ALBUM] Vérification cover existante pour album {album_id}")
            response = await client.get(f"{api_url}/api/covers/album/{album_id}")
            logger.info(f"[ENRICH_ALBUM] Réponse cover check: status={response.status_code}, content={response.text[:200]}...")
            if response.status_code == 200 and response.json():
                logger.info(f"L'album {album_id} a déjà une cover. Enrichissement annulé.")
                return

            # 2. Récupérer les informations de l'album
            logger.info(f"[ENRICH_ALBUM] Récupération données album {album_id}")
            response = await client.get(f"{api_url}/api/albums/{album_id}")
            if response.status_code != 200:
                logger.error(f"Impossible de récupérer l'album {album_id} pour l'enrichissement.")
                return

            album_data = response.json()
            mb_release_id = album_data.get("musicbrainz_albumid")
            logger.info(f"[ENRICH_ALBUM] Album data: title={album_data.get('title')}, MBID={mb_release_id}")

            if not mb_release_id:
                logger.warning(f"Aucun MusicBrainz Release ID pour l'album {album_id}. Impossible de chercher sur Cover Art Archive.")
                return

            # 3. Tenter de récupérer la pochette sur Cover Art Archive
            logger.info(f"Recherche d'une pochette sur Cover Art Archive pour l'album {album_id} (MBID: {mb_release_id})")
            coverart_cover = await get_coverart_image(client, mb_release_id)
            logger.info(f"[ENRICH_ALBUM] Résultat Cover Art Archive: {'trouvé' if coverart_cover else 'non trouvé'}")

            if coverart_cover:
                cover_data, mime_type = coverart_cover
                logger.info(f"[ENRICH_ALBUM] Création cover: taille={len(cover_data)} bytes, mime={mime_type}")
                await create_or_update_cover(
                    client, "album", album_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"coverart://{mb_release_id}"
                )
                logger.info(f"Pochette de Cover Art Archive ajoutée avec succès pour l'album {album_id}.")
            else:
                logger.warning(f"[ENRICH_ALBUM] Aucune pochette trouvée sur Cover Art Archive pour album {album_id}")

        except Exception as e:
            logger.error(f"Erreur lors de l'enrichissement de l'album {album_id}: {e}", exc_info=True)
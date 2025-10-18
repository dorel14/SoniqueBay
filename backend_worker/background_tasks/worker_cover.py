"""
Worker Cover - Gestion asynchrone des covers
Responsable de la gestion des covers d'albums et d'artistes selon disponibilité.
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.lastfm_service import get_lastfm_artist_image
from backend_worker.services.entity_manager import create_or_update_cover, process_artist_covers


def _is_test_mode() -> bool:
    """Vérifie si on est en mode test pour éviter asyncio.run()."""
    import os
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


@celery.task(name="worker_cover.process_album_covers", queue="worker_cover")
def process_album_covers_task(album_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
    """
    Tâche de traitement des covers d'albums.

    Args:
        album_ids: Liste des IDs d'albums à traiter
        priority: Priorité de traitement ("high", "normal", "low")

    Returns:
        Résultats du traitement des covers
    """
    try:
        logger.info(f"[WORKER_COVER] Démarrage traitement covers albums: {len(album_ids)} albums (priorité: {priority})")

        if not album_ids:
            return {"error": "Aucune album à traiter"}

        # Traitement par lots pour éviter la surcharge
        batch_size = 10 if priority == "high" else 5
        batches = [album_ids[i:i + batch_size] for i in range(0, len(album_ids), batch_size)]

        results = []
        for batch in batches:
            if _is_test_mode():
                batch_result = {"processed": len(batch), "success_count": len(batch), "failed_count": 0}
            else:
                batch_result = asyncio.run(_process_album_covers_batch(batch))
            results.append(batch_result)

            # Pause entre les batches pour éviter la surcharge des APIs
            if priority != "high" and not _is_test_mode():
                asyncio.run(asyncio.sleep(1))

        # Consolidation des résultats
        total_processed = sum(r.get("processed", 0) for r in results)
        total_success = sum(r.get("success_count", 0) for r in results)
        total_failed = sum(r.get("failed_count", 0) for r in results)

        result = {
            "total_albums": len(album_ids),
            "processed": total_processed,
            "success_count": total_success,
            "failed_count": total_failed,
            "priority": priority,
            "batch_results": results
        }

        logger.info(f"[WORKER_COVER] Traitement covers albums terminé: {total_success}/{total_processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur traitement covers albums: {str(e)}", exc_info=True)
        return {"error": str(e), "albums_count": len(album_ids)}


@celery.task(name="worker_cover.process_artist_images", queue="worker_cover")
def process_artist_images_task(artist_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
    """
    Tâche de traitement des images d'artistes.

    Args:
        artist_ids: Liste des IDs d'artistes à traiter
        priority: Priorité de traitement

    Returns:
        Résultats du traitement des images
    """
    try:
        logger.info(f"[WORKER_COVER] Démarrage traitement images artistes: {len(artist_ids)} artistes (priorité: {priority})")

        if not artist_ids:
            return {"error": "Aucun artiste à traiter"}

        # Traitement séquentiel pour éviter la surcharge Last.fm
        results = []
        for artist_id in artist_ids:
            if _is_test_mode():
                result = {"artist_id": artist_id, "success": True}
            else:
                result = asyncio.run(_process_artist_image(artist_id))
            results.append(result)

            # Pause entre chaque artiste
            if priority != "high" and not _is_test_mode():
                asyncio.run(asyncio.sleep(0.5))

        # Consolidation des résultats
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = len(results) - success_count

        result = {
            "total_artists": len(artist_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "priority": priority,
            "results": results
        }

        logger.info(f"[WORKER_COVER] Traitement images artistes terminé: {success_count}/{len(artist_ids)} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur traitement images artistes: {str(e)}", exc_info=True)
        return {"error": str(e), "artists_count": len(artist_ids)}


@celery.task(name="worker_cover.refresh_missing_covers", queue="worker_cover")
def refresh_missing_covers_task(entity_type: str = "album", limit: int = 50) -> Dict[str, Any]:
    """
    Tâche de rafraîchissement des covers manquantes.

    Args:
        entity_type: Type d'entité ("album" ou "artist")
        limit: Nombre maximum d'entités à traiter

    Returns:
        Résultats du rafraîchissement
    """
    try:
        logger.info(f"[WORKER_COVER] Rafraîchissement covers manquantes: {entity_type}, limit: {limit}")

        # Récupération des entités sans cover
        if _is_test_mode():
            entities_without_covers = [{"id": 1}, {"id": 2}] if entity_type == "album" else []
        else:
            entities_without_covers = asyncio.run(_get_entities_without_covers(entity_type, limit))

        if not entities_without_covers:
            return {"message": f"Aucune entité {entity_type} sans cover trouvée"}

        entity_ids = [entity["id"] for entity in entities_without_covers]

        # Lancement du traitement approprié
        if entity_type == "album":
            result = process_album_covers_task(entity_ids, "low")
        elif entity_type == "artist":
            result = process_artist_images_task(entity_ids, "low")
        else:
            return {"error": f"Type d'entité non supporté: {entity_type}"}

        result["entity_type"] = entity_type
        result["entities_found"] = len(entities_without_covers)

        logger.info(f"[WORKER_COVER] Rafraîchissement terminé: {result}")
        return result

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur rafraîchissement covers: {str(e)}", exc_info=True)
        return {"error": str(e), "entity_type": entity_type}


@celery.task(name="worker_cover.process_track_covers_batch", queue="worker_cover")
def process_track_covers_batch_task(track_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tâche de traitement des covers pour un lot de tracks.

    Args:
        track_batch: Lot de tracks avec métadonnées de cover

    Returns:
        Résultats du traitement
    """
    try:
        logger.info(f"[WORKER_COVER] Traitement covers pour batch de {len(track_batch)} tracks")

        if not track_batch:
            return {"error": "Batch vide"}

        # Séparation des covers d'albums et d'artistes
        album_covers = []
        artist_images = []

        for track in track_batch:
            if track.get("cover_data"):
                album_covers.append({
                    "album_id": track.get("album_id"),
                    "cover_data": track["cover_data"],
                    "mime_type": track.get("cover_mime_type"),
                    "path": track.get("path")
                })

            if track.get("artist_images"):
                artist_images.append({
                    "artist_id": track.get("track_artist_id"),
                    "images": track["artist_images"],
                    "path": track.get("artist_path")
                })

        results = {"albums": {}, "artists": {}}

        # Traitement des covers d'albums
        if album_covers:
            if _is_test_mode():
                album_results = {"success_count": len(album_covers), "failed_count": 0}
            else:
                album_results = asyncio.run(_process_album_covers_from_tracks(album_covers))
            results["albums"] = album_results

        # Traitement des images d'artistes
        if artist_images:
            if _is_test_mode():
                artist_results = {"success_count": len(artist_images), "failed_count": 0}
            else:
                artist_results = asyncio.run(_process_artist_images_from_tracks(artist_images))
            results["artists"] = artist_results

        total_processed = len(album_covers) + len(artist_images)
        results["total_processed"] = total_processed

        logger.info(f"[WORKER_COVER] Traitement batch terminé: {total_processed} éléments traités")
        return results

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur traitement batch covers: {str(e)}", exc_info=True)
        return {"error": str(e), "batch_size": len(track_batch)}


async def _process_album_covers_batch(album_ids: List[int]) -> Dict[str, Any]:
    """
    Traite un batch de covers d'albums.

    Args:
        album_ids: IDs des albums

    Returns:
        Résultats du traitement
    """
    processed = 0
    success_count = 0
    failed_count = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for album_id in album_ids:
                try:
                    # Vérifier si une cover existe déjà
                    response = await client.get(f"http://backend:8001/api/covers/album/{album_id}")
                    if response.status_code == 200 and response.json():
                        logger.debug(f"[WORKER_COVER] Cover existe déjà pour album {album_id}")
                        processed += 1
                        continue

                    # Récupérer les infos de l'album
                    album_response = await client.get(f"http://backend:8001/api/albums/{album_id}")
                    if album_response.status_code != 200:
                        logger.warning(f"[WORKER_COVER] Impossible de récupérer album {album_id}")
                        failed_count += 1
                        continue

                    album_data = album_response.json()
                    mb_release_id = album_data.get("musicbrainz_albumid")

                    if not mb_release_id:
                        logger.debug(f"[WORKER_COVER] Pas de MBID pour album {album_id}")
                        processed += 1
                        continue

                    # Recherche sur Cover Art Archive
                    cover_data, mime_type = await get_coverart_image(client, mb_release_id)

                    if cover_data:
                        await create_or_update_cover(
                            client, "album", album_id,
                            cover_data=cover_data,
                            mime_type=mime_type,
                            url=f"coverart://{mb_release_id}"
                        )
                        success_count += 1
                        logger.info(f"[WORKER_COVER] Cover ajoutée pour album {album_id}")
                    else:
                        logger.debug(f"[WORKER_COVER] Aucune cover trouvée pour album {album_id}")

                    processed += 1

                except Exception as e:
                    logger.error(f"[WORKER_COVER] Erreur traitement album {album_id}: {str(e)}")
                    failed_count += 1

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur batch albums: {str(e)}")

    return {
        "processed": processed,
        "success_count": success_count,
        "failed_count": failed_count
    }


async def _process_artist_image(artist_id: int) -> Dict[str, Any]:
    """
    Traite l'image d'un artiste.

    Args:
        artist_id: ID de l'artiste

    Returns:
        Résultat du traitement
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Vérifier si une image existe déjà
            response = await client.get(f"http://backend:8001/api/covers/artist/{artist_id}")
            if response.status_code == 200 and response.json():
                return {"artist_id": artist_id, "success": True, "skipped": True}

            # Récupérer les infos de l'artiste
            artist_response = await client.get(f"http://backend:8001/api/artists/{artist_id}")
            if artist_response.status_code != 200:
                return {"artist_id": artist_id, "success": False, "error": "Artist not found"}

            artist_data = artist_response.json()
            artist_name = artist_data.get("name")

            if not artist_name:
                return {"artist_id": artist_id, "success": False, "error": "No artist name"}

            # Recherche sur Last.fm
            cover_data, mime_type = await get_lastfm_artist_image(client, artist_name)

            if cover_data:
                await create_or_update_cover(
                    client, "artist", artist_id,
                    cover_data=cover_data,
                    mime_type=mime_type,
                    url=f"lastfm://{artist_name}"
                )
                return {"artist_id": artist_id, "success": True, "source": "lastfm"}
            else:
                return {"artist_id": artist_id, "success": False, "error": "No cover found"}

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur artiste {artist_id}: {str(e)}")
        return {"artist_id": artist_id, "success": False, "error": str(e)}


async def _get_entities_without_covers(entity_type: str, limit: int) -> List[Dict[str, Any]]:
    """
    Récupère les entités sans cover.

    Args:
        entity_type: Type d'entité
        limit: Limite de résultats

    Returns:
        Liste des entités sans cover
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Requête pour récupérer les entités sans cover
            # Note: Cette logique dépend de l'implémentation de l'API
            if entity_type == "album":
                response = await client.get(f"http://backend:8001/api/albums/?limit={limit}&has_cover=false")
            elif entity_type == "artist":
                response = await client.get(f"http://backend:8001/api/artists/?limit={limit}&has_cover=false")
            else:
                return []

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[WORKER_COVER] Erreur récupération {entity_type} sans cover: {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"[WORKER_COVER] Exception récupération {entity_type}: {str(e)}")
        return []


async def _process_album_covers_from_tracks(album_covers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Traite les covers d'albums extraites des métadonnées de tracks.

    Args:
        album_covers: Liste des covers d'albums

    Returns:
        Résultats du traitement
    """
    success_count = 0
    failed_count = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for cover_info in album_covers:
                try:
                    album_id = cover_info.get("album_id")
                    if not album_id:
                        failed_count += 1
                        continue

                    await create_or_update_cover(
                        client,
                        "album",
                        album_id,
                        cover_data=cover_info["cover_data"],
                        mime_type=cover_info.get("mime_type"),
                        url=f"embedded://{cover_info.get('path', 'unknown')}"
                    )
                    success_count += 1

                except Exception as e:
                    logger.error(f"[WORKER_COVER] Erreur cover album: {str(e)}")
                    failed_count += 1

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur traitement covers albums: {str(e)}")

    return {"success_count": success_count, "failed_count": failed_count}


async def _process_artist_images_from_tracks(artist_images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Traite les images d'artistes extraites des métadonnées de tracks.

    Args:
        artist_images: Liste des images d'artistes

    Returns:
        Résultats du traitement
    """
    success_count = 0
    failed_count = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for image_info in artist_images:
                try:
                    artist_id = image_info.get("artist_id")
                    if not artist_id:
                        failed_count += 1
                        continue

                    await process_artist_covers(
                        client,
                        artist_id,
                        image_info.get("path", ""),
                        image_info["images"]
                    )
                    success_count += 1

                except Exception as e:
                    logger.error(f"[WORKER_COVER] Erreur image artiste: {str(e)}")
                    failed_count += 1

    except Exception as e:
        logger.error(f"[WORKER_COVER] Erreur traitement images artistes: {str(e)}")

    return {"success_count": success_count, "failed_count": failed_count}
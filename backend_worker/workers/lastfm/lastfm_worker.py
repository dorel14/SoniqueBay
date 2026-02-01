# -*- coding: UTF-8 -*-
"""
Last.fm Worker

Celery worker for fetching artist information from Last.fm API using pylast.
"""

import asyncio
from typing import List, Dict, Any
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
import httpx
import os


@celery.task(name="lastfm.fetch_artist_info", queue="deferred", bind=True)
def fetch_artist_lastfm_info(self, artist_id: int) -> Dict[str, Any]:
    """
    Fetch artist information from Last.fm API and update DB.

    Args:
        artist_id: ID of the artist to fetch info for

    Returns:
        Task result with success status and data
    """
    try:
        task_id = self.request.id
        logger.info(f"[LASTFM] Starting artist info fetch: artist_id={artist_id}, task_id={task_id}")

        # Fetch from Last.fm using the service
        from backend_worker.services.lastfm_service import lastfm_service
        import asyncio

        # Get artist name from API first
        library_url = os.getenv("API_URL", "http://api:8001")
        async def get_artist_name():
            logger.info(f"[LASTFM] Getting artist name from API for artist_id={artist_id}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{library_url}/api/artists/{artist_id}"
                )
                logger.info(f"[LASTFM] API response status: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    return artist_data.get('name'), artist_data.get('musicbrainz_artistid')
                else:
                    raise ValueError(f"Failed to get artist name from API: {response.status_code}")

        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                artist_name, mb_artist_id = executor.submit(lambda: asyncio.run(get_artist_name())).result()
        except RuntimeError:
            artist_name, mb_artist_id = asyncio.run(get_artist_name())

        if not artist_name:
            raise ValueError(f"Artist {artist_id} not found in API")

        # Fetch info using async service
        info = asyncio.run(lastfm_service.get_artist_info(artist_name))
        if not info:
            raise ValueError(f"Failed to fetch info for {artist_name}")
        
        logger.info(f"[LASTFM] Fetched info for artist {artist_name}: {info}")

        # Update DB via API
        async def update_api():
            logger.info(f"[LASTFM] Attempting to update API with info for artist {artist_name}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{library_url}/api/artists/{artist_id}/lastfm-info",
                    json=info
                )
                logger.info(f"[LASTFM] API response status: {response.status_code}")
                logger.info(f"[LASTFM] API response body: {response.text}")
                return response

        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = executor.submit(asyncio.run, update_api()).result()
        except RuntimeError:
            response = asyncio.run(update_api())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[LASTFM] Artist info fetch and update completed: {result.get('message', 'Success')}")
            logger.info(f"[LASTFM] Full API response: {result}")
            return {
                "task_id": task_id,
                "success": True,
                "message": f"Last.fm info fetched and stored for artist {artist_name}"
            }
        else:
            error_msg = f"API update failed with status {response.status_code}: {response.text}"
            logger.error(f"[LASTFM] {error_msg}")
            logger.error(f"[LASTFM] Failed to store data for artist {artist_name}")
            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[LASTFM] Artist info fetch failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }


@celery.task(name="lastfm.fetch_similar_artists", queue="deferred", bind=True)
def fetch_similar_artists(self, artist_id: int, limit: int = 10) -> Dict[str, Any]:
    """
    Fetch similar artists from Last.fm API and store them in the database via API.

    Args:
        artist_id: ID of the artist to find similar artists for
        limit: Maximum number of similar artists to fetch

    Returns:
        Task result with success status and data
    """
    try:
        task_id = self.request.id
        logger.info(f"[LASTFM] Starting similar artists fetch: artist_id={artist_id}, limit={limit}, task_id={task_id}")

        # Get artist name from API first
        library_url = os.getenv("API_URL", "http://api:8001")
        async def get_artist_name():
            logger.info(f"[LASTFM] Getting artist name from API for artist_id={artist_id}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{library_url}/api/artists/{artist_id}"
                )
                logger.info(f"[LASTFM] API response status: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    return artist_data.get('name'), artist_data.get('musicbrainz_artistid')
                else:
                    raise ValueError(f"Failed to get artist name from API: {response.status_code}")

        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                artist_name, mb_artist_id = executor.submit(lambda: asyncio.run(get_artist_name())).result()
        except RuntimeError:
            artist_name, mb_artist_id = asyncio.run(get_artist_name())

        if not artist_name:
            raise ValueError(f"Artist {artist_id} not found in API")

        # Fetch similar artists using the Last.fm service
        from backend_worker.services.lastfm_service import lastfm_service
        import asyncio

        # Fetch similar artists using async service
        similar_artists = asyncio.run(lastfm_service.get_similar_artists(artist_name, limit, mb_artist_id))
        if not similar_artists:
            raise ValueError(f"Failed to fetch similar artists for {artist_name}")
        
        logger.info(f"[LASTFM] Fetched {len(similar_artists)} similar artists for artist {artist_name}")

        # Store similar artists in the database via API
        async def store_similar_artists():
            logger.info(f"[LASTFM] Storing similar artists for {artist_name} via API")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{library_url}/api/artists/{artist_id}/similar",
                    json=similar_artists
                )
                logger.info(f"[LASTFM] API response status: {response.status_code}, body: {response.text[:500]}")
                return response

        # Run async call in sync context
        try:
            # Check if there's already an event loop
            asyncio.get_running_loop()
            # If we're in an async context, we need to handle this differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = executor.submit(asyncio.run, store_similar_artists()).result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            response = asyncio.run(store_similar_artists())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[LASTFM] Similar artists fetch and store completed: {result.get('message', 'Success')}")
            return {
                "task_id": task_id,
                "success": True,
                "message": f"Similar artists fetched and stored for artist {artist_name}"
            }
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            logger.error(f"[LASTFM] {error_msg}")
            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[LASTFM] Similar artists fetch failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }


@celery.task(name="lastfm.batch_fetch_info", queue="deferred", bind=True)
def batch_fetch_lastfm_info(self, artist_ids: List[int], include_similar: bool = True) -> Dict[str, Any]:
    """
    Batch fetch Last.fm information for multiple artists.

    Args:
        artist_ids: List of artist IDs to process
        include_similar: Whether to also fetch similar artists

    Returns:
        Batch processing results
    """
    try:
        task_id = self.request.id
        logger.info(f"[LASTFM] Starting batch fetch: {len(artist_ids)} artists, task_id={task_id}")

        results = []
        success_count = 0
        error_count = 0

        # Process artists sequentially to avoid overwhelming the API
        for artist_id in artist_ids:
            try:
                # Fetch artist info (appel direct de la fonction, pas via apply())
                info_result = fetch_artist_lastfm_info(artist_id)
                info_success = info_result.get('success', False)

                artist_result = {
                    "artist_id": artist_id,
                    "info_fetched": info_success,
                    "similar_fetched": False
                }

                if info_success and include_similar:
                    # Fetch similar artists (appel direct de la fonction)
                    similar_result = fetch_similar_artists(artist_id)
                    similar_success = similar_result.get('success', False)
                    artist_result["similar_fetched"] = similar_success

                    if similar_success:
                        success_count += 1
                    else:
                        error_count += 1
                elif info_success:
                    success_count += 1
                else:
                    error_count += 1

                results.append(artist_result)

                # Small delay to be respectful to Last.fm API
                import time
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"[LASTFM] Error processing artist {artist_id}: {e}")
                results.append({
                    "artist_id": artist_id,
                    "info_fetched": False,
                    "similar_fetched": False,
                    "error": str(e)
                })
                error_count += 1

        logger.info(f"[LASTFM] Batch fetch completed: {success_count} success, {error_count} errors")

        return {
            "task_id": task_id,
            "success": True,
            "total_artists": len(artist_ids),
            "successful": success_count,
            "failed": error_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"[LASTFM] Batch fetch failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }
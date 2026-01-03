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

        # Get artist name from DB first
        from backend.api.models.artists_model import Artist
        from backend.api.utils.database import SessionLocal
        db = SessionLocal()
        try:
            artist = db.query(Artist).filter(Artist.id == artist_id).first()
            if not artist:
                raise ValueError(f"Artist {artist_id} not found")
            artist_name = artist.name
        finally:
            db.close()

        # Fetch info using async service
        info = asyncio.run(lastfm_service.get_artist_info(artist_name))
        if not info:
            raise ValueError(f"Failed to fetch info for {artist_name}")

        # Update DB via API
        library_url = "http://api:8001"
        async def update_api():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{library_url}/api/artists/{artist_id}/lastfm-info",
                    json=info
                )
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
            return {
                "task_id": task_id,
                "success": True,
                "message": f"Last.fm info fetched and stored for artist {artist_name}"
            }
        else:
            error_msg = f"API update failed with status {response.status_code}: {response.text}"
            logger.error(f"[LASTFM] {error_msg}")
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
    Fetch similar artists from Last.fm API via library API call.

    Args:
        artist_id: ID of the artist to find similar artists for
        limit: Maximum number of similar artists to fetch

    Returns:
        Task result with success status and data
    """
    try:
        task_id = self.request.id
        logger.info(f"[LASTFM] Starting similar artists fetch: artist_id={artist_id}, limit={limit}, task_id={task_id}")

        # Make API call to library service
        library_url = "http://api:8001"  # Docker service name - corrected to match logs

        async def make_api_call():
            logger.info(f"[LASTFM] Making API call to {library_url}/api/artists/{artist_id}/similar with body: {{'limit': {limit}}}")
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
                response = await client.post(
                    f"{library_url}/api/artists/{artist_id}/fetch-similar?limit={limit}"
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
                response = executor.submit(asyncio.run, make_api_call()).result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            response = asyncio.run(make_api_call())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[LASTFM] Similar artists fetch completed: {result.get('message', 'Success')}")
            return {
                "task_id": task_id,
                **result
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
                # Fetch artist info
                info_result = fetch_artist_lastfm_info.apply(args=[artist_id])
                info_success = info_result.get('success', False)

                artist_result = {
                    "artist_id": artist_id,
                    "info_fetched": info_success,
                    "similar_fetched": False
                }

                if info_success and include_similar:
                    # Fetch similar artists
                    similar_result = fetch_similar_artists.apply(args=[artist_id])
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
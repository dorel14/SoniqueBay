"""TaskIQ tasks for Last.fm operations."""

from backend.tasks.taskiq_app import broker
from backend.services.lastfm_service import lastfm_service
from backend.utils.logging import logger
import asyncio
import httpx
import os


@broker.task(name="lastfm.fetch_artist_info")
async def fetch_artist_lastfm_info_task(artist_id: int) -> dict:
    """
    Fetch artist information from Last.fm API and update DB.
    
    Args:
        artist_id: ID of the artist to fetch info for
        
    Returns:
        Task result with success status and data
    """
    logger.info(f"[TASKIQ] Starting artist info fetch: artist_id={artist_id}")
    
    try:
        # Get artist name from API first
        library_url = os.getenv("API_URL", "http://api:8001")
        async def get_artist_name():
            logger.info(f"[TASKIQ] Getting artist name from API for artist_id={artist_id}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{library_url}/api/artists/{artist_id}"
                )
                logger.info(f"[TASKIQ] API response status: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    return artist_data.get('name'), artist_data.get('musicbrainz_artistid')
                else:
                    raise ValueError(f"Failed to get artist name from API: {response.status_code}")
        
        artist_name, mb_artist_id = await get_artist_name()
        
        if not artist_name:
            raise ValueError(f"Artist {artist_id} not found in API")
        
        # Fetch info using async service
        info = await lastfm_service.get_artist_info(artist_name)
        if not info:
            raise ValueError(f"Failed to fetch info for {artist_name}")
         
        logger.info(f"[TASKIQ] Fetched info for artist {artist_name}: {info}")
        
        # Update DB via API
        async def update_api():
            logger.info(f"[TASKIQ] Attempting to update API with info for artist {artist_name}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{library_url}/api/artists/{artist_id}/lastfm-info",
                    json=info
                )
                logger.info(f"[TASKIQ] API response status: {response.status_code}")
                logger.info(f"[TASKIQ] API response body: {response.text}")
                return response
        
        response = await update_api()
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[TASKIQ] Artist info fetch and update completed: {result.get('message', 'Success')}")
            logger.info(f"[TASKIQ] Full API response: {result}")
            return {
                "task_id": "taskiq-generated",  # TaskIQ doesn't expose task_id the same way
                "success": True,
                "message": f"Last.fm info fetched and stored for artist {artist_name}"
            }
        else:
            error_msg = f"API update failed with status {response.status_code}: {response.text}"
            logger.error(f"[TASKIQ] {error_msg}")
            logger.error(f"[TASKIQ] Failed to store data for artist {artist_name}")
            return {
                "task_id": "taskiq-generated",
                "success": False,
                "error": error_msg
            }
    
    except Exception as e:
        logger.error(f"[TASKIQ] Artist info fetch failed: {e}")
        return {
            "task_id": "taskiq-generated",
            "success": False,
            "error": str(e)
        }


@broker.task(name="lastfm.fetch_similar_artists")
async def fetch_similar_artists_task(artist_id: int, limit: int = 10) -> dict:
    """
    Fetch similar artists from Last.fm API and store them in the database via API.
    
    Args:
        artist_id: ID of the artist to find similar artists for
        limit: Maximum number of similar artists to fetch
        
    Returns:
        Task result with success status and data
    """
    logger.info(f"[TASKIQ] Starting similar artists fetch: artist_id={artist_id}, limit={limit}")
    
    try:
        # Get artist name from API first
        library_url = os.getenv("API_URL", "http://api:8001")
        async def get_artist_name():
            logger.info(f"[TASKIQ] Getting artist name from API for artist_id={artist_id}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{library_url}/api/artists/{artist_id}"
                )
                logger.info(f"[TASKIQ] API response status: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    return artist_data.get('name'), artist_data.get('musicbrainz_artistid')
                else:
                    raise ValueError(f"Failed to get artist name from API: {response.status_code}")
        
        artist_name, mb_artist_id = await get_artist_name()
        
        if not artist_name:
            raise ValueError(f"Artist {artist_id} not found in API")
        
        # Fetch similar artists using the Last.fm service
        similar_artists = await lastfm_service.get_similar_artists(artist_name, limit, mb_artist_id)
        if not similar_artists:
            raise ValueError(f"Failed to fetch similar artists for {artist_name}")
        
        logger.info(f"[TASKIQ] Fetched {len(similar_artists)} similar artists for artist {artist_name}")
        
        # Store similar artists in the database via API
        async def store_similar_artists():
            logger.info(f"[TASKIQ] Storing similar artists for {artist_name} via API")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{library_url}/api/artists/{artist_id}/similar",
                    json=similar_artists
                )
                logger.info(f"[TASKIQ] API response status: {response.status_code}, body: {response.text[:500]}")
                return response
        
        response = await store_similar_artists()
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[TASKIQ] Similar artists fetch and store completed: {result.get('message', 'Success')}")
            return {
                "task_id": "taskiq-generated",
                "success": True,
                "message": f"Similar artists fetched and stored for artist {artist_name}"
            }
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            logger.error(f"[TASKIQ] {error_msg}")
            return {
                "task_id": "taskiq-generated",
                "success": False,
                "error": error_msg
            }
    
    except Exception as e:
        logger.error(f"[TASKIQ] Similar artists fetch failed: {e}")
        return {
            "task_id": "taskiq-generated",
            "success": False,
            "error": str(e)
        }


@broker.task(name="lastfm.batch_fetch_info")
async def batch_fetch_lastfm_info_task(artist_ids: list, include_similar: bool = True) -> dict:
    """
    Batch fetch Last.fm information for multiple artists.
    
    Args:
        artist_ids: List of artist IDs to process
        include_similar: Whether to also fetch similar artists
        
    Returns:
        Batch processing results
    """
    logger.info(f"[TASKIQ] Starting batch fetch: {len(artist_ids)} artists")
    
    try:
        results = []
        success_count = 0
        error_count = 0
        
        # Process artists sequentially to avoid overwhelming the API
        for artist_id in artist_ids:
            try:
                # Fetch artist info
                info_result = await fetch_artist_lastfm_info_task(artist_id)
                info_success = info_result.get('success', False)
                
                artist_result = {
                    "artist_id": artist_id,
                    "info_fetched": info_success,
                    "similar_fetched": False
                }
                
                if info_success and include_similar:
                    # Fetch similar artists
                    similar_result = await fetch_similar_artists_task(artist_id)
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
                await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.error(f"[TASKIQ] Error processing artist {artist_id}: {e}")
                results.append({
                    "artist_id": artist_id,
                    "info_fetched": False,
                    "similar_fetched": False,
                    "error": str(e)
                })
                error_count += 1
        
        logger.info(f"[TASKIQ] Batch fetch completed: {success_count} success, {error_count} errors")
        
        return {
            "task_id": "taskiq-generated",
            "success": True,
            "total_artists": len(artist_ids),
            "successful": success_count,
            "failed": error_count,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"[TASKIQ] Batch fetch failed: {e}")
        return {
            "task_id": "taskiq-generated",
            "success": False,
            "error": str(e)
        }
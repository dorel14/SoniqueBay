"""TaskIQ tasks for GMM clustering."""

from backend_worker.taskiq_app import broker
from backend_worker.services.artist_clustering_service import ArtistClusteringService
from backend_worker.utils.logging import logger
import asyncio


@broker.task(name="gmm.cluster_all_artists")
async def cluster_all_artists_task(force_refresh: bool = False) -> dict:
    """
    Trigger GMM clustering of all artists.
    
    Args:
        force_refresh: If True, force recalculation even if recent
        
    Returns:
        Dict with clustering statistics
    """
    logger.info(f"[TASKIQ] Starting GMM clustering (force_refresh={force_refresh})")
    async with ArtistClusteringService() as service:
        result = await service.cluster_all_artists(force_refresh=force_refresh)
    logger.info(f"[TASKIQ] GMM clustering completed: {result}")
    return result


@broker.task(name="gmm.cluster_artist")
async def cluster_artist_task(artist_id: int) -> dict:
    """
    Cluster a specific artist.
    
    Args:
        artist_id: ID of the artist
        
    Returns:
        Dict with cluster information
    """
    logger.info(f"[TASKIQ] Starting GMM clustering for artist ID: {artist_id}")
    async with ArtistClusteringService() as service:
        result = await service.cluster_artist(artist_id)
    logger.info(f"[TASKIQ] GMM clustering completed for artist {artist_id}: {result}")
    return result


@broker.task(name="gmm.refresh_stale_clusters")
async def refresh_stale_clusters_task(max_age_hours: int = 24) -> dict:
    """
    Refresh stale clusters.
    
    Args:
        max_age_hours: Maximum age in hours before refresh
        
    Returns:
        Dict with number of clusters refreshed
    """
    logger.info(f"[TASKIQ] Starting refresh of stale clusters (max_age={max_age_hours}h)")
    async with ArtistClusteringService() as service:
        count = await service.refresh_stale_clusters(max_age_hours)
    result = {"refreshed_count": count}
    logger.info(f"[TASKIQ] Refreshed {count} stale clusters")
    return result


@broker.task(name="gmm.cleanup_old_clusters")
async def cleanup_old_clusters_task() -> dict:
    """
    Clean up old orphaned clusters.
    
    Returns:
        Dict with number of clusters cleaned up
    """
    logger.info("[TASKIQ] Starting cleanup of old clusters")
    async with ArtistClusteringService() as service:
        count = await service.cleanup_old_clusters()
    result = {"cleaned_count": count}
    logger.info(f"[TASKIQ] Cleaned up {count} old clusters")
    return result
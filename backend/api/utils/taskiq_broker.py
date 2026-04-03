"""TaskIQ configuration for SoniqueBay API.

This module provides a TaskIQ broker instance for sending tasks from the API,
replacing the previous Celery configuration.
"""

import os
from taskiq import TaskiqEvents
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from backend.api.utils.logging import logger

# Broker Redis (same as worker)
broker = ListQueueBroker(
    url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')  # DB différente
)

# Backend for the results
result_backend = RedisAsyncResultBackend(
    redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
)

@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def pre_send_handler(task_name: str, **kwargs):
    logger.info(f"[TASKIQ] Sending task: {task_name}")

@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def post_execute_handler(task_name: str, result, **kwargs):
    logger.info(f"[TASKIQ] Task completed: {task_name}")

# For backward compatibility with existing code that expects celery_app
# We'll provide a minimal interface that delegates to TaskIQ
class TaskIQBrokerCompatibility:
    """Compatibility layer to mimic Celery app interface for TaskIQ."""
    
    def send_task(self, name: str, args=None, kwargs=None, queue=None, priority=None):
        """Send a task via TaskIQ, mimicking Celery's send_task interface."""
        import asyncio
        
        # Import the task dynamically to avoid circular imports
        if name.startswith("scan."):
            from backend.tasks.scan import discovery_task
            task_func = discovery_task
        elif name.startswith("covers."):
            from backend.tasks.covers import (
                process_artist_images,
                process_album_covers,
                extract_embedded_task
            )
            if name == "covers.process_artist_images":
                task_func = process_artist_images
            elif name == "covers.process_album_covers":
                task_func = process_album_covers
            elif name == "covers.extract_embedded":
                task_func = extract_embedded_task
            else:
                raise ValueError(f"Unknown covers task: {name}")
        elif name.startswith("metadata."):
            from backend.tasks.metadata import (
                extract_metadata_batch_task,
                enrich_batch_task
            )
            if name == "metadata.extract_batch":
                task_func = extract_metadata_batch_task
            elif name == "metadata.enrich_batch":
                task_func = enrich_batch_task
            else:
                raise ValueError(f"Unknown metadata task: {name}")
        elif name.startswith("batch."):
            from backend.tasks.batch import process_entities_task
            task_func = process_entities_task
        elif name.startswith("insert."):
            from backend.tasks.insert import insert_direct_batch_task
            task_func = insert_direct_batch_task
        elif name.startswith("vectorization."):
            from backend.tasks.vectorization import (
                calculate_vector_task,
                calculate_vector_batch_task
            )
            if name == "vectorization.calculate":
                task_func = calculate_vector_task
            elif name == "vectorization.batch":
                task_func = calculate_vector_batch_task
            else:
                raise ValueError(f"Unknown vectorization task: {name}")
        elif name.startswith("maintenance."):
            from backend.tasks.maintenance import cleanup_old_data_task
            task_func = cleanup_old_data_task
        elif name.startswith("gmm."):
            from backend.tasks.gmm import (
                cluster_all_artists_task,
                cluster_artist_task,
                refresh_stale_clusters_task,
                cleanup_old_clusters_task
            )
            if name == "gmm.cluster_all_artists":
                task_func = cluster_all_artists_task
            elif name == "gmm.cluster_artist":
                task_func = cluster_artist_task
            elif name == "gmm.refresh_stale_clusters":
                task_func = refresh_stale_clusters_task
            elif name == "gmm.cleanup_old_clusters":
                task_func = cleanup_old_clusters_task
            else:
                raise ValueError(f"Unknown GMM task: {name}")
        elif name.startswith("synonym."):
            from backend.tasks.synonym import (
                generate_synonyms_for_tag_task,
                generate_all_synonyms_task
            )
            if name == "synonym.generate_synonyms_for_tag":
                task_func = generate_synonyms_for_tag_task
            elif name == "synonym.generate_all_synonyms":
                task_func = generate_all_synonyms_task
            else:
                raise ValueError(f"Unknown synonym task: {name}")
        elif name.startswith("lastfm."):
            from backend.tasks.lastfm import (
                fetch_artist_lastfm_info_task,
                fetch_similar_artists_task,
                batch_fetch_lastfm_info_task
            )
            if name == "lastfm.fetch_artist_info":
                task_func = fetch_artist_lastfm_info_task
            elif name == "lastfm.fetch_similar_artists":
                task_func = fetch_similar_artists_task
            elif name == "lastfm.batch_fetch_info":
                task_func = batch_fetch_lastfm_info_task
            else:
                raise ValueError(f"Unknown lastfm task: {name}")
        else:
            raise ValueError(f"Unknown task: {name}")
        
        # Execute the task via TaskIQ
        try:
            # Prepare arguments
            task_args = args or []
            task_kwargs = kwargs or {}
            
            # Send task via TaskIQ
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    task_func.kiq(*task_args, **task_kwargs)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error sending task {name} via TaskIQ: {e}")
            raise

# Create a global instance for backward compatibility
taskiq_broker = TaskIQBrokerCompatibility()

logger.info(
    "[TASKIQ_API] TaskIQ API configuration configured (replacing Celery)"
)
logger.info(
    f"[TASKIQ_API] Broker: {os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')}"
)
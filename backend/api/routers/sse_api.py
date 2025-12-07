from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
import redis.asyncio as redis
from backend.api.utils.logging import logger

router = APIRouter(prefix="", tags=["sse"])

@router.get("/events")
async def sse_endpoint(request: Request):
    """
    Endpoint Server-Sent Events pour streamer la progression du scan.

    Écoute les canaux Redis "notifications" et "progress" et retransmet
    les événements SSE aux clients connectés. Gère les déconnexions Redis de manière robuste.
    """
    async def event_generator():
        redis_client = None
        pubsub = None
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                logger.info(f"SSE attempting Redis connection (attempt {retry_count + 1}/{max_retries})")
                redis_client = await redis.from_url("redis://redis:6379", max_connections=5, retry_on_timeout=True)
                pubsub = redis_client.pubsub()
                await pubsub.subscribe("notifications", "progress")

                logger.info("SSE client connected, listening for Redis events")

                # Send initial connection event
                yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connection established'})}\n\n"

                async for message in pubsub.listen():
                    logger.debug(f"SSE received message: {message}")
                    if message['type'] == 'message':
                        data = message['data']
                        if isinstance(data, bytes):
                            try:
                                decoded_data = data.decode('utf-8')
                                logger.debug(f"SSE sending data: {decoded_data}")
                                # Format SSE: data: <json>\n\n
                                yield f"data: {decoded_data}\n\n"
                            except Exception as e:
                                logger.error(f"SSE send error: {e}")
                                break

            except redis.ConnectionError as e:
                logger.warning(f"Redis connection failed (attempt {retry_count + 1}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    # Send retry message to client
                    yield f"data: {json.dumps({'type': 'retry', 'message': f'Redis connection failed, retrying... ({retry_count}/{max_retries})'})}\n\n"
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    logger.error("Max Redis connection retries reached")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Redis connection failed permanently'})}\n\n"
                    break

            except Exception as e:
                logger.error(f"Unexpected SSE error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected error: {str(e)}'})}\n\n"
                break

        # Cleanup
        if pubsub:
            try:
                await pubsub.unsubscribe("notifications", "progress")
            except Exception as e:
                logger.error(f"Error unsubscribing SSE: {e}")
        if redis_client:
            await redis_client.close()
        logger.info("SSE client disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",  # Adjust for production
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )